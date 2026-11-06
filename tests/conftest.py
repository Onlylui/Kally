"""Fixtures compartilhadas: banco de teste (kally_teste) e bot sem rede."""

import json
import os
from datetime import datetime, timezone
from types import SimpleNamespace

import asyncpg
import pytest
import pytest_asyncio
from telegram import Update
from telegram.ext import Application
from telegram.request import BaseRequest

from app import db, handlers
from app.main import registrar_handlers

# Nome fixo: nunca vem do ambiente, para o DROP DATABASE abaixo não atingir o banco real.
BANCO_DE_TESTE = "kally_teste"
BANCO_DE_MANUTENCAO = "postgres"

CHAT_AUTORIZADO = -100123
CHAT_NAO_AUTORIZADO = -999
JOAO = 111
MARIA = 222


# --- Banco de teste ---

def recusar_banco_real(nome_do_banco_real: str | None) -> None:
    """Se o banco do bot se chamasse kally_teste, recriá-lo apagaria os dados reais."""
    if nome_do_banco_real == BANCO_DE_TESTE:
        pytest.fail(f"POSTGRES_DB não pode ser {BANCO_DE_TESTE}: os testes apagam esse banco.")


def _dados_de_conexao() -> dict:
    return {
        "host": os.environ["POSTGRES_HOST"],
        "port": int(os.environ["POSTGRES_PORT"]),
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }


async def _recriar_banco(criar: bool) -> None:
    """Sempre pelo banco de manutenção, nunca pelo POSTGRES_DB."""
    conexao = await asyncpg.connect(database=BANCO_DE_MANUTENCAO, **_dados_de_conexao())
    try:
        # DROP e CREATE em execute separados: nenhum dos dois roda dentro de transação.
        await conexao.execute(f'DROP DATABASE IF EXISTS "{BANCO_DE_TESTE}" WITH (FORCE)')
        if criar:
            await conexao.execute(f'CREATE DATABASE "{BANCO_DE_TESTE}"')
    finally:
        await conexao.close()


@pytest_asyncio.fixture
async def pool_teste():
    """Pool de um kally_teste recém-criado, com as migrações reais, apagado ao final.

    Banco inacessível faz o teste falhar: nada aqui captura o erro nem pula o teste.
    """
    recusar_banco_real(os.environ.get("POSTGRES_DB"))
    await _recriar_banco(criar=True)
    try:
        # Direto no asyncpg: db.criar_pool() usa o POSTGRES_DB, que é o banco real.
        pool = await asyncpg.create_pool(
            database=BANCO_DE_TESTE,
            min_size=1,
            max_size=3,
            **_dados_de_conexao(),
        )
        try:
            atual = await pool.fetchval("SELECT current_database()")
            if atual != BANCO_DE_TESTE:
                pytest.fail(f"Conectado ao banco errado: {atual}")
            await db.aplicar_migracoes(pool)
            yield pool
        finally:
            await pool.close()
    finally:
        await _recriar_banco(criar=False)


# --- Bot real do PTB, com requisições falsas ---

class RequisicaoFalsa(BaseRequest):
    """Responde como a API do Telegram, sem rede, e guarda os textos que o bot enviou."""

    def __init__(self) -> None:
        self.enviadas: list[str] = []

    @property
    def read_timeout(self) -> None:
        return None

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def do_request(self, url, method, request_data=None, **_):
        metodo = url.rsplit("/", maxsplit=1)[-1]
        if metodo == "getMe":
            resultado = {"id": 1, "is_bot": True, "first_name": "KALLY", "username": "KallyBot"}
        elif metodo == "sendMessage":
            parametros = request_data.parameters
            self.enviadas.append(parametros["text"])
            resultado = {
                "message_id": 1,
                "date": 0,
                "chat": {"id": parametros["chat_id"], "type": "group"},
                "text": parametros["text"],
            }
        else:
            resultado = True
        return 200, json.dumps({"ok": True, "result": resultado}).encode()


@pytest_asyncio.fixture
async def bot_teste():
    """Application real com os handlers de produção. `enviar` entrega um update ao bot."""
    requisicao = RequisicaoFalsa()
    app = (
        Application.builder()
        .token("123:abc")
        .request(requisicao)
        .get_updates_request(RequisicaoFalsa())
        .build()
    )
    registrar_handlers(app)
    app.bot_data.update(
        allowed_chat_ids={CHAT_AUTORIZADO},
        gemini=object(),
        gemini_modelo="modelo-falso",
        pool=object(),
    )
    await app.initialize()
    contador = {"update_id": 0}

    async def enviar(
        texto: str,
        chat_id: int = CHAT_AUTORIZADO,
        usuario: tuple[int, str] = (JOAO, "João"),
        momento: datetime = datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc),
    ) -> list[str]:
        """Processa a mensagem e devolve só o que o bot respondeu a ela."""
        contador["update_id"] += 1
        comando = texto.split(maxsplit=1)[0] if texto.startswith("/") else None
        entidades = [{"type": "bot_command", "offset": 0, "length": len(comando)}] if comando else []
        update = Update.de_json(
            {
                "update_id": contador["update_id"],
                "message": {
                    "message_id": contador["update_id"],
                    "date": int(momento.timestamp()),
                    "chat": {"id": chat_id, "type": "group"},
                    "from": {"id": usuario[0], "is_bot": False, "first_name": usuario[1]},
                    "text": texto,
                    "entities": entidades,
                },
            },
            app.bot,
        )
        ja_enviadas = len(requisicao.enviadas)
        await app.process_update(update)
        return requisicao.enviadas[ja_enviadas:]

    yield SimpleNamespace(app=app, enviar=enviar)
    await app.shutdown()


@pytest.fixture
def gemini_falso(monkeypatch):
    """Troca o gemini.estimar: `resposta` define o retorno e `chamadas` guarda os textos."""
    falso = SimpleNamespace(chamadas=[], resposta=None, erro=None)

    async def estimar(cliente, modelo, texto):
        falso.chamadas.append(texto)
        if falso.erro:
            raise falso.erro
        return falso.resposta

    monkeypatch.setattr(handlers.gemini, "estimar", estimar)
    return falso
