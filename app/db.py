"""Conexão com o Postgres, migrações e consultas."""

import logging
import os
import re
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

PASTA_MIGRACOES = Path(__file__).resolve().parent.parent / "migrations"

# Nome de arquivo de migração: número, sublinhado, descrição. Ex.: 001_inicial.sql
_NOME_MIGRACAO = re.compile(r"^(\d+)_.+\.sql$")


# --- Conexão ---

async def criar_pool() -> asyncpg.Pool:
    """Cria o pool de conexões com as variáveis POSTGRES_* do ambiente."""
    nomes = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
    faltando = [nome for nome in nomes if not os.getenv(nome)]
    if faltando:
        # Só os nomes das variáveis vão para a mensagem, nunca os valores.
        raise RuntimeError(f"variáveis do banco não definidas: {', '.join(faltando)}")

    return await asyncpg.create_pool(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        database=os.environ["POSTGRES_DB"],
        min_size=1,
        max_size=5,
    )


# --- Migrações ---

def ordenar_migracoes(nomes: list[str]) -> list[tuple[int, str]]:
    """Devolve (número, nome) de cada arquivo .sql, em ordem pelo número do nome.

    Ordena pelo número, não pelo texto: 010 vem depois de 002.
    Lança ValueError se um .sql não seguir o padrão 001_nome.sql ou se um número se repetir.
    """
    migracoes = []
    for nome in nomes:
        if not nome.endswith(".sql"):
            continue
        achado = _NOME_MIGRACAO.match(nome)
        if not achado:
            raise ValueError(f"nome de migração fora do padrão 001_nome.sql: {nome}")
        migracoes.append((int(achado.group(1)), nome))

    migracoes.sort()
    numeros = [numero for numero, _ in migracoes]
    if len(numeros) != len(set(numeros)):
        raise ValueError("há duas migrações com o mesmo número")
    return migracoes


async def aplicar_migracoes(pool: asyncpg.Pool, pasta: Path = PASTA_MIGRACOES) -> None:
    """Aplica, em ordem, as migrações de `pasta` que ainda não estão na schema_versao."""
    async with pool.acquire() as conexao:
        await conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_versao (
                versao      integer PRIMARY KEY,
                aplicada_em timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        aplicadas = {linha["versao"] for linha in await conexao.fetch("SELECT versao FROM schema_versao")}

        nomes = [arquivo.name for arquivo in pasta.iterdir() if arquivo.is_file()]
        for numero, nome in ordenar_migracoes(nomes):
            if numero in aplicadas:
                continue
            sql = (pasta / nome).read_text(encoding="utf-8")
            # Migração e registro na mesma transação: se falhar, nada fica pela metade.
            async with conexao.transaction():
                await conexao.execute(sql)
                await conexao.execute("INSERT INTO schema_versao (versao) VALUES ($1)", numero)
            logger.info("Migração aplicada: %s", nome)


# --- Usuários ---

async def salvar_usuario(pool: asyncpg.Pool, telegram_id: int, nome: str) -> None:
    """Cria o usuário no primeiro comando e atualiza o nome nos seguintes."""
    await pool.execute(
        """
        INSERT INTO usuarios (telegram_id, nome) VALUES ($1, $2)
        ON CONFLICT (telegram_id) DO UPDATE SET nome = EXCLUDED.nome
        """,
        telegram_id,
        nome,
    )


# --- Pesos (RN-012) ---

async def registrar_peso(
    pool: asyncpg.Pool,
    telegram_id: int,
    chat_id: int,
    peso_kg: Decimal,
    data: date,
    hora: time,
) -> tuple[Decimal, date] | None:
    """Grava a pesagem e devolve a anterior (peso, data), ou None se for a primeira.

    A anterior é a mais recente antes desta, de qualquer data, por data, hora e id.
    message_id fica nulo até a etapa dos botões.
    """
    async with pool.acquire() as conexao:
        async with conexao.transaction():
            novo_id = await conexao.fetchval(
                """
                INSERT INTO pesos (telegram_id, chat_id, peso_kg, data, hora)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                telegram_id,
                chat_id,
                peso_kg,
                data,
                hora,
            )
            anterior = await conexao.fetchrow(
                """
                SELECT peso_kg, data FROM pesos
                WHERE telegram_id = $1
                  AND (data, hora, id) < ($2::date, $3::time, $4::bigint)
                ORDER BY data DESC, hora DESC, id DESC
                LIMIT 1
                """,
                telegram_id,
                data,
                hora,
                novo_id,
            )
    if anterior is None:
        return None
    return anterior["peso_kg"], anterior["data"]


async def ultimo_peso(pool: asyncpg.Pool, telegram_id: int) -> tuple[Decimal, date] | None:
    """A pesagem mais recente (peso, data), ou None se a pessoa nunca se pesou."""
    linha = await pool.fetchrow(
        """
        SELECT peso_kg, data FROM pesos
        WHERE telegram_id = $1
        ORDER BY data DESC, hora DESC, id DESC
        LIMIT 1
        """,
        telegram_id,
    )
    if linha is None:
        return None
    return linha["peso_kg"], linha["data"]
