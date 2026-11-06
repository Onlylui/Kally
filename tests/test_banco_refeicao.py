"""Testes com Postgres real, no banco kally_teste (nunca no POSTGRES_DB)."""

import os
from datetime import date, datetime, time, timezone
from decimal import Decimal
from types import SimpleNamespace

import asyncpg
import pytest

from app import db, gemini, handlers
from app.gemini import FalhaGemini, ItemEstimado, RespostaGemini
from app.handlers import (
    TEXTO_BANCO_FORA_DO_AR,
    TEXTO_ERRO_INESPERADO,
    TEXTO_FALHA_GEMINI,
    TEXTO_R_NENHUM_ALIMENTO,
)
from tests.conftest import BANCO_DE_TESTE, CHAT_AUTORIZADO, JOAO, MARIA, recusar_banco_real

DIA = date(2026, 11, 1)


def alimento(nome="arroz", kcal="130", porcao_nome="1 colher de servir") -> dict:
    return {
        "nome": nome,
        "kcal_100g": Decimal(kcal),
        "proteina_100g": Decimal("2.5"),
        "carbo_100g": Decimal("28"),
        "gordura_100g": Decimal("0.3"),
        "porcao_g": Decimal("45"),
        "porcao_nome": porcao_nome,
    }


def item_gravar(alimento_id: int, gramas="150", kcal="195", texto="150 g de arroz") -> dict:
    return {
        "alimento_id": alimento_id,
        "texto": texto,
        "gramas": Decimal(gramas),
        "kcal": Decimal(kcal),
        "proteina_g": Decimal("3.8"),
        "carbo_g": Decimal("42"),
        "gordura_g": Decimal("0.5"),
    }


async def registrar(pool, itens, kcal=195, data=DIA, telegram_id=JOAO, hora=time(12, 0)) -> int:
    return await db.registrar_refeicao(
        pool,
        telegram_id,
        CHAT_AUTORIZADO,
        "150 g de arroz",
        kcal,
        Decimal("3.8"),
        Decimal("42"),
        Decimal("0.5"),
        data,
        hora,
        itens,
    )


async def contar(pool, tabela: str) -> int:
    assert tabela in {"alimentos", "refeicoes", "refeicao_itens", "usuarios"}
    return await pool.fetchval(f"SELECT count(*) FROM {tabela}")


# --- salvaguardas do banco de teste ---

@pytest.mark.asyncio
async def test_a_fixture_esta_no_banco_de_teste(pool_teste):
    assert await pool_teste.fetchval("SELECT current_database()") == BANCO_DE_TESTE
    assert os.environ["POSTGRES_DB"] != BANCO_DE_TESTE


@pytest.mark.asyncio
async def test_a_fixture_aplica_as_migracoes_reais_num_banco_vazio(pool_teste):
    assert await pool_teste.fetchval("SELECT count(*) FROM schema_versao") >= 1
    for tabela in ["alimentos", "refeicoes", "refeicao_itens", "usuarios"]:
        assert await contar(pool_teste, tabela) == 0


def test_recusa_rodar_se_o_banco_real_tiver_o_nome_do_de_teste():
    with pytest.raises(pytest.fail.Exception):
        recusar_banco_real(BANCO_DE_TESTE)
    recusar_banco_real("kally")


# --- salvar_alimentos (P2) ---

@pytest.mark.asyncio
async def test_alimento_novo_e_gravado(pool_teste):
    base = await db.salvar_alimentos(pool_teste, [alimento("arroz"), alimento("feijao", "76")])

    assert set(base) == {"arroz", "feijao"}
    linha = await pool_teste.fetchrow("SELECT * FROM alimentos WHERE nome = 'feijao'")
    assert linha["id"] == base["feijao"]["id"]
    assert linha["kcal_100g"] == Decimal("76")
    assert linha["porcao_g"] == Decimal("45")
    assert linha["porcao_nome"] == "1 colher de servir"
    assert linha["origem"] == "ia"


@pytest.mark.asyncio
async def test_alimento_existente_nunca_e_sobrescrito(pool_teste):
    await db.salvar_alimentos(pool_teste, [alimento("arroz", "130", "1 colher de servir")])
    base = await db.salvar_alimentos(pool_teste, [alimento("arroz", "800", "outra porção")])

    assert base["arroz"]["kcal_100g"] == Decimal("130")
    linha = await pool_teste.fetchrow("SELECT * FROM alimentos WHERE nome = 'arroz'")
    assert linha["kcal_100g"] == Decimal("130")
    assert linha["porcao_nome"] == "1 colher de servir"
    assert await contar(pool_teste, "alimentos") == 1


@pytest.mark.asyncio
async def test_mesmo_alimento_duas_vezes_no_mesmo_registro(pool_teste):
    base = await db.salvar_alimentos(pool_teste, [alimento("arroz", "130"), alimento("arroz", "200")])
    assert base["arroz"]["kcal_100g"] == Decimal("130")
    assert await contar(pool_teste, "alimentos") == 1


# --- registrar_refeicao ---

@pytest.mark.asyncio
async def test_grava_refeicao_itens_e_devolve_o_total(pool_teste):
    await db.salvar_usuario(pool_teste, JOAO, "João")
    base = await db.salvar_alimentos(pool_teste, [alimento("arroz"), alimento("ovo")])
    itens = [
        item_gravar(base["arroz"]["id"]),
        item_gravar(base["ovo"]["id"], "100", "140", "2 ovos"),
    ]

    assert await registrar(pool_teste, itens, kcal=335) == 335

    refeicao = await pool_teste.fetchrow("SELECT * FROM refeicoes")
    assert refeicao["kcal"] == 335
    assert refeicao["data"] == DIA
    assert refeicao["hora"] == time(12, 0)
    assert refeicao["message_id"] is None
    assert refeicao["retroativo"] is False
    assert refeicao["kcal_manual"] is False

    linhas = await pool_teste.fetch("SELECT * FROM refeicao_itens ORDER BY ordem")
    assert [linha["ordem"] for linha in linhas] == [1, 2]
    assert [linha["texto"] for linha in linhas] == ["150 g de arroz", "2 ovos"]
    assert all(linha["refeicao_id"] == refeicao["id"] for linha in linhas)


@pytest.mark.asyncio
async def test_total_soma_so_a_pessoa_e_o_dia(pool_teste):
    await db.salvar_usuario(pool_teste, JOAO, "João")
    await db.salvar_usuario(pool_teste, MARIA, "Maria")
    base = await db.salvar_alimentos(pool_teste, [alimento()])
    itens = [item_gravar(base["arroz"]["id"])]

    assert await registrar(pool_teste, itens, kcal=100) == 100
    assert await registrar(pool_teste, itens, kcal=200) == 300
    assert await registrar(pool_teste, itens, kcal=50, telegram_id=MARIA) == 50
    assert await registrar(pool_teste, itens, kcal=70, data=date(2026, 11, 2)) == 70


@pytest.mark.asyncio
async def test_item_que_falha_desfaz_a_refeicao_inteira(pool_teste):
    await db.salvar_usuario(pool_teste, JOAO, "João")
    base = await db.salvar_alimentos(pool_teste, [alimento()])
    itens = [
        item_gravar(base["arroz"]["id"]),
        item_gravar(base["arroz"]["id"], gramas="0"),  # viola CHECK (gramas > 0)
    ]

    with pytest.raises(asyncpg.CheckViolationError):
        await registrar(pool_teste, itens)

    assert await contar(pool_teste, "refeicoes") == 0
    assert await contar(pool_teste, "refeicao_itens") == 0


@pytest.mark.asyncio
async def test_alimento_inexistente_desfaz_a_refeicao_inteira(pool_teste):
    await db.salvar_usuario(pool_teste, JOAO, "João")

    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await registrar(pool_teste, [item_gravar(alimento_id=999)])

    assert await contar(pool_teste, "refeicoes") == 0


# --- fluxo completo: bot real, Postgres real e Gemini falso ---

def criar_item(nome="arroz", gramas=150.0, **campos) -> ItemEstimado:
    valores = {
        "nome": nome,
        "texto": f"{gramas:g} g de {nome}",
        "gramas": gramas,
        "kcal_100g": 130,
        "proteina_100g": 2.5,
        "carbo_100g": 28,
        "gordura_100g": 0.3,
        "porcao_g": 45,
        "porcao_nome": "1 colher de servir",
        "alcoolico": False,
    }
    return ItemEstimado(**(valores | campos))


@pytest.fixture
def bot(bot_teste, pool_teste):
    bot_teste.app.bot_data["pool"] = pool_teste
    return bot_teste


@pytest.mark.asyncio
async def test_r_de_ponta_a_ponta(bot, pool_teste, gemini_falso):
    gemini_falso.resposta = RespostaGemini(
        itens=[criar_item("Feijão", 100, kcal_100g=76, carbo_100g=14, proteina_100g=4.8, gordura_100g=0.5), criar_item()],
        ignorados=["kkkk"],
    )
    texto = "100 g de feijão,   150 g de arroz\n\n  kkkk"

    respostas = await bot.enviar(f"/r {texto}")

    assert len(gemini_falso.chamadas) == 1
    assert gemini_falso.chamadas[0] == "100 g de feijão, 150 g de arroz\nkkkk"
    assert respostas[0].split("·")[0] == "João: +271 kcal "
    assert "\nFeijão 100 g · 76 kcal · arroz 150 g · 195 kcal\nIgnorei: kkkk" in respostas[0]

    refeicao = await pool_teste.fetchrow("SELECT * FROM refeicoes")
    assert refeicao["descricao"] == texto
    assert refeicao["kcal"] == 271
    assert refeicao["telegram_id"] == JOAO
    assert refeicao["chat_id"] == CHAT_AUTORIZADO
    assert refeicao["message_id"] is None
    assert refeicao["proteina_g"] == Decimal("8.6")  # 4,8 + 3,8
    assert refeicao["carbo_g"] == Decimal("56.0")
    assert refeicao["gordura_g"] == Decimal("1.0")

    assert await pool_teste.fetchval("SELECT count(*) FROM alimentos WHERE nome IN ('feijao', 'arroz')") == 2
    itens = await pool_teste.fetch("SELECT * FROM refeicao_itens ORDER BY ordem")
    assert [item["texto"] for item in itens] == ["100 g de Feijão", "150 g de arroz"]
    assert sum(item["kcal"] for item in itens) == refeicao["kcal"]


@pytest.mark.asyncio
async def test_a_base_vence_no_registro(bot, pool_teste, gemini_falso):
    await db.salvar_alimentos(pool_teste, [alimento("arroz", "100")])
    gemini_falso.resposta = RespostaGemini(itens=[criar_item(gramas=200.0, kcal_100g=130)], ignorados=[])

    respostas = await bot.enviar("/r 200 g de arroz")

    assert "arroz 200 g · 200 kcal" in respostas[0]
    assert await pool_teste.fetchval("SELECT kcal_100g FROM alimentos") == Decimal("100")
    assert await pool_teste.fetchval("SELECT kcal FROM refeicoes") == 200


@pytest.mark.asyncio
async def test_2359_e_0001_caem_em_dias_diferentes(bot, pool_teste, gemini_falso):
    # Datas passadas: a data vem de message.date, nunca do relógio. 2020 também evita que
    # o "hoje" do relógio coincida com a data do teste na resposta.
    gemini_falso.resposta = RespostaGemini(itens=[criar_item(gramas=100.0)], ignorados=[])
    sexta_2359 = datetime(2020, 3, 7, 2, 59, tzinfo=timezone.utc)
    sabado_0001 = datetime(2020, 3, 7, 3, 1, tzinfo=timezone.utc)

    primeira = await bot.enviar("/r 100 g de arroz", momento=sexta_2359)
    segunda = await bot.enviar("/r 100 g de arroz", momento=sabado_0001)
    terceira = await bot.enviar("/r 100 g de arroz", momento=sabado_0001)

    linhas = await pool_teste.fetch("SELECT data, hora FROM refeicoes ORDER BY id")
    assert (linhas[0]["data"], linhas[0]["hora"]) == (date(2020, 3, 6), time(23, 59))
    assert (linhas[1]["data"], linhas[1]["hora"]) == (date(2020, 3, 7), time(0, 1))

    # Cada dia tem o próprio total.
    assert "total de 06/03: 130 kcal" in primeira[0]
    assert "total de 07/03: 130 kcal" in segunda[0]
    assert "total de 07/03: 260 kcal" in terceira[0]


@pytest.mark.asyncio
async def test_total_hoje_quando_a_mensagem_e_de_hoje(bot, gemini_falso, monkeypatch):
    gemini_falso.resposta = RespostaGemini(itens=[criar_item(gramas=100.0)], ignorados=[])

    class RelogioFalso(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2020, 3, 7, 10, 0, tzinfo=tz)

    monkeypatch.setattr(handlers, "datetime", RelogioFalso)
    momento = datetime(2020, 3, 7, 3, 1, tzinfo=timezone.utc)
    respostas = await bot.enviar("/r 100 g de arroz", momento=momento)
    assert "total hoje: 130 kcal" in respostas[0]


@pytest.mark.asyncio
async def test_pessoas_nao_se_misturam(bot, gemini_falso):
    gemini_falso.resposta = RespostaGemini(itens=[criar_item(gramas=100.0)], ignorados=[])
    await bot.enviar("/r arroz")
    respostas = await bot.enviar("/r arroz", usuario=(MARIA, "Maria"))
    assert respostas[0].startswith("Maria: +130 kcal")
    assert "130 kcal\narroz" in respostas[0]


@pytest.mark.asyncio
async def test_falha_do_gemini_nao_grava_nada(bot, pool_teste, gemini_falso):
    gemini_falso.erro = FalhaGemini()
    assert await bot.enviar("/r arroz") == [TEXTO_FALHA_GEMINI]
    assert await contar(pool_teste, "alimentos") == 0
    assert await contar(pool_teste, "refeicoes") == 0


@pytest.mark.asyncio
async def test_nenhum_alimento_nao_grava_nada(bot, pool_teste, gemini_falso):
    gemini_falso.resposta = RespostaGemini(itens=[], ignorados=["kkkkk"])
    assert await bot.enviar("/r kkkkk") == [TEXTO_R_NENHUM_ALIMENTO]
    assert await contar(pool_teste, "alimentos") == 0
    assert await contar(pool_teste, "refeicoes") == 0


def cliente_que_responde(resposta: RespostaGemini) -> SimpleNamespace:
    """Vale o gemini.estimar de verdade, com a validação; só a chamada é falsa."""

    async def generate_content(**_):
        return SimpleNamespace(parsed=resposta)

    modelos = SimpleNamespace(generate_content=generate_content)
    return SimpleNamespace(aio=SimpleNamespace(models=modelos))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "campos",
    [
        {"gramas": 10000.5},
        {"porcao_g": 10001},
        {"proteina_100g": 100.1, "kcal_100g": 400},
        {"gordura_100g": 101, "alcoolico": True},
        {"texto": "ar\x00roz"},
    ],
)
async def test_valor_fora_do_teto_nao_grava_nada(bot, pool_teste, campos):
    bot.app.bot_data["gemini"] = cliente_que_responde(
        RespostaGemini(itens=[criar_item(), criar_item("ovo", **campos)], ignorados=[])
    )

    assert await bot.enviar("/r arroz e ovo") == [TEXTO_FALHA_GEMINI]
    assert await contar(pool_teste, "alimentos") == 0
    assert await contar(pool_teste, "refeicoes") == 0
    assert await contar(pool_teste, "refeicao_itens") == 0


@pytest.mark.asyncio
async def test_gramas_no_limite_exato_registra(bot, pool_teste):
    bot.app.bot_data["gemini"] = cliente_que_responde(
        RespostaGemini(itens=[criar_item(gramas=10000.0, porcao_g=10000)], ignorados=[])
    )

    respostas = await bot.enviar("/r 10 kg de arroz")

    assert "arroz 10000 g · 13.000 kcal" in respostas[0]
    assert await pool_teste.fetchval("SELECT kcal FROM refeicoes") == 13000


@pytest.mark.asyncio
async def test_erro_inesperado_no_r_responde_o_texto_novo(bot, pool_teste, gemini_falso, monkeypatch):
    gemini_falso.resposta = RespostaGemini(itens=[criar_item()], ignorados=[])

    def falhar(itens, base):
        raise ValueError("defeito no código")

    monkeypatch.setattr(handlers, "calcular_itens", falhar)

    assert await bot.enviar("/r arroz") == [TEXTO_ERRO_INESPERADO]
    assert await contar(pool_teste, "refeicoes") == 0


@pytest.mark.asyncio
async def test_erro_inesperado_no_peso_responde_o_texto_novo(bot, pool_teste, monkeypatch):
    def falhar(texto):
        raise ValueError("defeito no código")

    monkeypatch.setattr(handlers, "ler_peso", falhar)

    assert await bot.enviar("/peso 82,4") == [TEXTO_ERRO_INESPERADO]
    assert await pool_teste.fetchval("SELECT count(*) FROM pesos") == 0


@pytest.mark.asyncio
async def test_item_invalido_entre_validos_nao_grava_nada(bot, pool_teste):
    bot.app.bot_data["gemini"] = cliente_que_responde(
        RespostaGemini(itens=[criar_item(), criar_item("ovo", kcal_100g=1000)], ignorados=[])
    )

    assert await bot.enviar("/r arroz e ovo") == [TEXTO_FALHA_GEMINI]
    assert await contar(pool_teste, "alimentos") == 0
    assert await contar(pool_teste, "refeicoes") == 0


@pytest.mark.asyncio
async def test_falha_ao_gravar_o_item_desfaz_e_responde_o_texto_do_banco(bot, pool_teste, gemini_falso, monkeypatch):
    # Gramas válidos para o Gemini, mas um alimento_id quebrado faz o segundo INSERT falhar.
    gemini_falso.resposta = RespostaGemini(itens=[criar_item()], ignorados=[])
    calcular = handlers.calcular_itens

    def calcular_com_id_invalido(itens, base):
        calculados = calcular(itens, base)
        calculados[0]["alimento_id"] = 999_999
        return calculados

    monkeypatch.setattr(handlers, "calcular_itens", calcular_com_id_invalido)

    assert await bot.enviar("/r arroz") == [TEXTO_BANCO_FORA_DO_AR]
    assert await contar(pool_teste, "refeicoes") == 0
    assert await contar(pool_teste, "refeicao_itens") == 0
    # O alimento fica na base: é gravado antes, em transação própria, e isso é inofensivo.
    assert await contar(pool_teste, "alimentos") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("texto", ["/r arroz", "/peso 82,4", "/peso"])
async def test_conexao_perdida_de_verdade(bot, gemini_falso, texto):
    # Um pool real fechado: o erro é o do asyncpg, sem nada falso no caminho.
    pool = await asyncpg.create_pool(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        database=BANCO_DE_TESTE,
        min_size=1,
        max_size=1,
    )
    await pool.close()
    bot.app.bot_data["pool"] = pool

    assert await bot.enviar(texto) == [TEXTO_BANCO_FORA_DO_AR]
    assert gemini_falso.chamadas == []


# --- /peso continua funcionando ---

@pytest.mark.asyncio
async def test_peso_no_banco_real(bot):
    assert await bot.enviar("/peso") == ["João: nenhuma pesagem registrada ainda. Ex.: /peso 82,4"]
    assert await bot.enviar("/peso 82,4") == ["João: 82,4 kg registrado (primeira pesagem)"]
    resposta = await bot.enviar("/peso 81.9")
    assert resposta[0].startswith("João: 81,9 kg registrado (anterior: 82,4 kg em ")
