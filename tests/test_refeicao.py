"""/r sem Postgres: tratamento do texto, cálculo, respostas, silêncio e erros de banco."""

from datetime import date, datetime, time, timezone
from decimal import Decimal
from types import SimpleNamespace

import asyncpg
import pytest
from telegram import Message, Update
from telegram.error import NetworkError
from telegram.ext import MessageHandler

from app import handlers
from app.gemini import FalhaGemini, ItemEstimado, RespostaGemini
from app.handlers import (
    LIMITE_DESCRICAO,
    TEXTO_BANCO_FORA_DO_AR,
    TEXTO_ERRO_INESPERADO,
    TEXTO_FALHA_GEMINI,
    TEXTO_R_MUITO_LONGO,
    TEXTO_R_NENHUM_ALIMENTO,
    TEXTO_R_SEM_DESCRICAO,
    alimentos_para_salvar,
    calcular_itens,
    eh_erro_de_banco,
    extrair_descricao,
    formatar_gramas,
    formatar_kcal,
    limpar_descricao,
    resposta_refeicao,
)
from tests.conftest import CHAT_AUTORIZADO, CHAT_NAO_AUTORIZADO, JOAO


def criar_item(nome="arroz", gramas=150, kcal_100g=130, **campos) -> ItemEstimado:
    valores = {
        "nome": nome,
        "texto": f"{gramas} g de {nome}",
        "gramas": gramas,
        "kcal_100g": kcal_100g,
        "proteina_100g": 2.5,
        "carbo_100g": 28,
        "gordura_100g": 0.3,
        "porcao_g": 45,
        "porcao_nome": "1 colher de servir",
        "alcoolico": False,
    }
    return ItemEstimado(**(valores | campos))


def linha_base(id=1, kcal="130", proteina="2.5", carbo="28", gordura="0.3") -> dict:
    return {
        "id": id,
        "kcal_100g": Decimal(kcal),
        "proteina_100g": Decimal(proteina),
        "carbo_100g": Decimal(carbo),
        "gordura_100g": Decimal(gordura),
    }


# --- extrair_descricao ---

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("/r arroz", "arroz"),
        ("/r@KallyBot arroz e feijão", "arroz e feijão"),
        ("/R arroz", "arroz"),
        ("/r", ""),
        ("/r   ", ""),
        ("/r\narroz\nfeijão", "arroz\nfeijão"),
        ("/r arroz\n\n  feijão   e  ovo", "arroz\n\n  feijão   e  ovo"),
    ],
)
def test_extrair_descricao(texto, esperado):
    assert extrair_descricao(texto) == esperado


# --- limpar_descricao (D8) ---

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("arroz", "arroz"),
        ("arroz   e    feijão", "arroz e feijão"),
        ("  arroz  ", "arroz"),
        ("arroz\nfeijão", "arroz\nfeijão"),
        ("arroz\n\n\n  feijão  \n", "arroz\nfeijão"),
        ("arroz\r\nfeijão", "arroz\nfeijão"),
        ("arroz\t\tfeijão", "arroz feijão"),
        ("", ""),
        ("   \n  \n ", ""),
    ],
)
def test_limpar_descricao(texto, esperado):
    assert limpar_descricao(texto) == esperado


# --- cálculo (P2, P4) ---

def test_alimentos_para_salvar_normaliza_o_nome():
    linha = alimentos_para_salvar([criar_item(nome=" Feijão ", kcal_100g=130.1, porcao_nome=" 1 concha ")])[0]
    assert linha["nome"] == "feijao"
    assert linha["kcal_100g"] == Decimal("130.1")
    assert linha["porcao_nome"] == "1 concha"


def test_calcular_item():
    item = calcular_itens([criar_item(gramas=150)], {"arroz": linha_base(id=7)})[0]
    assert item["alimento_id"] == 7
    assert item["gramas"] == Decimal("150")
    assert item["kcal"] == Decimal("195")
    assert item["proteina_g"] == Decimal("3.8")  # 3,75
    assert item["carbo_g"] == Decimal("42.0")
    assert item["gordura_g"] == Decimal("0.5")  # 0,45


@pytest.mark.parametrize(
    "gramas, kcal_100g, esperado",
    [
        (100, "100.5", 101),  # ROUND_HALF_UP, não arredondamento bancário
        (100, "101.5", 102),
        (100, "100.4", 100),
        (50, "1", 1),  # 0,5
        (1, "1", 0),
    ],
)
def test_kcal_arredonda_para_inteiro(gramas, kcal_100g, esperado):
    item = calcular_itens([criar_item(gramas=gramas)], {"arroz": linha_base(kcal=kcal_100g)})[0]
    assert item["kcal"] == esperado


def test_calculo_usa_os_valores_da_base_e_os_gramas_do_gemini():
    # A base diz 100 kcal; o Gemini disse 130 agora. A base vence (P2).
    item = calcular_itens([criar_item(gramas=200, kcal_100g=130)], {"arroz": linha_base(kcal="100")})[0]
    assert item["kcal"] == 200


def test_calculo_acha_a_base_pelo_nome_normalizado():
    item = calcular_itens([criar_item(nome="Feijão")], {"feijao": linha_base(id=3)})[0]
    assert item["alimento_id"] == 3
    assert item["nome"] == "Feijão"  # P10: a resposta usa o nome como veio


# --- formatação ---

@pytest.mark.parametrize("kcal, esperado", [(0, "0"), (90, "90"), (999, "999"), (1420, "1.420"), (1234567, "1.234.567")])
def test_formatar_kcal(kcal, esperado):
    assert formatar_kcal(kcal) == esperado


@pytest.mark.parametrize(
    "gramas, esperado",
    [("150", "150"), ("150.0", "150"), ("62.5", "62,5"), ("33.333", "33,3"), ("100.04", "100")],
)
def test_formatar_gramas(gramas, esperado):
    assert formatar_gramas(Decimal(gramas)) == esperado


ITENS = [
    {"nome": "arroz", "gramas": Decimal("200"), "kcal": Decimal("260")},
    {"nome": "feijão", "gramas": Decimal("100"), "kcal": Decimal("75")},
]
HOJE = date(2026, 11, 1)


def test_resposta_hoje():
    assert resposta_refeicao("João", ITENS, 1420, HOJE, HOJE, []) == (
        "João: +335 kcal · total hoje: 1.420 kcal\n"
        "arroz 200 g · 260 kcal · feijão 100 g · 75 kcal"
    )


def test_resposta_de_ontem_enviada_depois_da_meia_noite():
    assert resposta_refeicao("João", ITENS, 2130, date(2026, 10, 31), HOJE, []) == (
        "João: +335 kcal · total de 31/10: 2.130 kcal\n"
        "arroz 200 g · 260 kcal · feijão 100 g · 75 kcal"
    )


def test_resposta_com_ignorados():
    assert resposta_refeicao("João", ITENS[:1], 260, HOJE, HOJE, ["kkkk", " ", "asdf"]) == (
        "João: +260 kcal · total hoje: 260 kcal\n"
        "arroz 200 g · 260 kcal\n"
        "Ignorei: kkkk, asdf"
    )


def test_resposta_sem_botoes_e_sem_unidades():
    texto = resposta_refeicao("João", ITENS, 335, HOJE, HOJE, [])
    assert "un.)" not in texto
    assert "Corrigir" not in texto


def test_textos_do_r():
    assert TEXTO_R_SEM_DESCRICAO == "Descreva o que comeu, ex.: /r 150 g de arroz e 1 filé de frango"
    assert TEXTO_R_MUITO_LONGO == "Descrição muito longa. Use até 500 caracteres."
    assert TEXTO_R_NENHUM_ALIMENTO == (
        "Não identifiquei nenhum alimento. Descreva o que comeu, ex.: /r 150 g de arroz e 1 filé de frango"
    )
    assert TEXTO_FALHA_GEMINI == "Não consegui estimar agora. Nada foi registrado, tente de novo em instantes."
    assert TEXTO_BANCO_FORA_DO_AR == "Não consegui confirmar o registro agora. Tente de novo em instantes."
    assert TEXTO_ERRO_INESPERADO == "Algo deu errado. Tente de novo em instantes."


# --- handlers registrados ---

def todos_os_handlers(app) -> list:
    return [handler for grupo in app.handlers.values() for handler in grupo]


@pytest.mark.asyncio
async def test_nao_ha_handler_de_mensagem_sem_comando(bot_teste):
    assert not any(isinstance(handler, MessageHandler) for handler in todos_os_handlers(bot_teste.app))


def test_papagaio_nao_existe_mais():
    assert not hasattr(handlers, "ecoar")


# --- comando_r com banco falso ---

@pytest.fixture
def banco_falso(monkeypatch):
    chamadas = SimpleNamespace(usuarios=[], alimentos=[], refeicoes=[])

    async def salvar_usuario(pool, telegram_id, nome):
        chamadas.usuarios.append((telegram_id, nome))

    async def salvar_alimentos(pool, alimentos):
        chamadas.alimentos.append(alimentos)
        return {a["nome"]: linha_base(id=i, kcal=str(a["kcal_100g"])) for i, a in enumerate(alimentos, 1)}

    async def registrar_refeicao(pool, *argumentos):
        chamadas.refeicoes.append(argumentos)
        return 1420

    monkeypatch.setattr(handlers.db, "salvar_usuario", salvar_usuario)
    monkeypatch.setattr(handlers.db, "salvar_alimentos", salvar_alimentos)
    monkeypatch.setattr(handlers.db, "registrar_refeicao", registrar_refeicao)
    return chamadas


@pytest.mark.asyncio
async def test_r_registra_e_responde(bot_teste, gemini_falso, banco_falso):
    gemini_falso.resposta = RespostaGemini(itens=[criar_item(gramas=200)], ignorados=[])

    # 02:30 UTC de segunda ainda é domingo em São Paulo (RN-001, RN-007).
    momento = datetime(2026, 11, 2, 2, 30, tzinfo=timezone.utc)
    respostas = await bot_teste.enviar("/r 200 g de arroz", momento=momento)

    assert gemini_falso.chamadas == ["200 g de arroz"]
    assert banco_falso.usuarios == [(JOAO, "João")]
    telegram_id, chat_id, descricao, kcal, _, _, _, data, hora, itens = banco_falso.refeicoes[0]
    assert (telegram_id, chat_id, descricao, kcal) == (JOAO, CHAT_AUTORIZADO, "200 g de arroz", 260)
    assert (data, hora) == (date(2026, 11, 1), time(23, 30))
    assert len(itens) == 1
    assert len(respostas) == 1
    assert respostas[0].startswith("João: +260 kcal · total de 01/11: 1.420 kcal\narroz 200 g · 260 kcal")


@pytest.mark.asyncio
async def test_r_limpa_o_texto_para_o_gemini_e_guarda_o_original(bot_teste, gemini_falso, banco_falso):
    gemini_falso.resposta = RespostaGemini(itens=[criar_item()], ignorados=[])
    await bot_teste.enviar("/r  arroz   e  feijão\n\n  2  ovos  ")

    assert gemini_falso.chamadas == ["arroz e feijão\n2 ovos"]
    assert banco_falso.refeicoes[0][2] == "arroz   e  feijão\n\n  2  ovos  "


@pytest.mark.asyncio
async def test_r_com_ignorados_registra_e_avisa(bot_teste, gemini_falso, banco_falso):
    gemini_falso.resposta = RespostaGemini(itens=[criar_item()], ignorados=["kkkk"])
    respostas = await bot_teste.enviar("/r arroz kkkk")
    assert len(banco_falso.refeicoes) == 1
    assert respostas[0].endswith("\nIgnorei: kkkk")


@pytest.mark.asyncio
@pytest.mark.parametrize("texto", ["/r", "/r    ", "/r\n\n  \n", "/r@KallyBot"])
async def test_r_vazio_nao_chama_o_gemini(bot_teste, gemini_falso, banco_falso, texto):
    assert await bot_teste.enviar(texto) == [TEXTO_R_SEM_DESCRICAO]
    assert gemini_falso.chamadas == []
    assert banco_falso.alimentos == banco_falso.refeicoes == []


@pytest.mark.asyncio
async def test_r_longo_demais_nao_chama_o_gemini(bot_teste, gemini_falso, banco_falso):
    assert await bot_teste.enviar("/r " + "a" * (LIMITE_DESCRICAO + 1)) == [TEXTO_R_MUITO_LONGO]
    assert gemini_falso.chamadas == []
    assert banco_falso.alimentos == banco_falso.refeicoes == []


@pytest.mark.asyncio
async def test_limite_vale_para_o_texto_limpo(bot_teste, gemini_falso, banco_falso):
    gemini_falso.resposta = RespostaGemini(itens=[criar_item()], ignorados=[])
    # 500 caracteres depois da limpeza, bem mais antes dela.
    texto = "a" * 250 + " " * 300 + "b" * 249
    await bot_teste.enviar("/r " + texto)
    assert len(gemini_falso.chamadas) == 1
    assert len(gemini_falso.chamadas[0]) == LIMITE_DESCRICAO


@pytest.mark.asyncio
async def test_r_sem_alimento_nao_grava(bot_teste, gemini_falso, banco_falso):
    gemini_falso.resposta = RespostaGemini(itens=[], ignorados=["kkkkk"])
    assert await bot_teste.enviar("/r kkkkk") == [TEXTO_R_NENHUM_ALIMENTO]
    assert len(gemini_falso.chamadas) == 1
    assert banco_falso.alimentos == banco_falso.refeicoes == []


@pytest.mark.asyncio
async def test_falha_do_gemini_nao_grava(bot_teste, gemini_falso, banco_falso):
    gemini_falso.erro = FalhaGemini()
    assert await bot_teste.enviar("/r arroz") == [TEXTO_FALHA_GEMINI]
    assert len(gemini_falso.chamadas) == 1
    assert banco_falso.alimentos == banco_falso.refeicoes == []


# --- filtro e silêncio ---

@pytest.mark.asyncio
async def test_r_em_chat_nao_autorizado_nao_chama_o_gemini(bot_teste, gemini_falso, banco_falso):
    assert await bot_teste.enviar("/r arroz", chat_id=CHAT_NAO_AUTORIZADO) == []
    assert gemini_falso.chamadas == []
    assert banco_falso.usuarios == []


@pytest.mark.asyncio
async def test_mensagem_sem_comando_recebe_silencio(bot_teste, gemini_falso, banco_falso):
    assert await bot_teste.enviar("almocei arroz, feijão e bife") == []
    assert gemini_falso.chamadas == []
    assert banco_falso.usuarios == []


@pytest.mark.asyncio
async def test_id_continua_funcionando(bot_teste):
    assert await bot_teste.enviar("/id") == [f"ID deste chat: {CHAT_AUTORIZADO}"]
    assert await bot_teste.enviar("/id", chat_id=CHAT_NAO_AUTORIZADO) == [f"ID deste chat: {CHAT_NAO_AUTORIZADO}"]


# --- banco fora do ar ---

@pytest.mark.parametrize(
    "erro",
    [
        OSError("conexão recusada"),
        ConnectionRefusedError(),
        TimeoutError(),
        asyncpg.PostgresConnectionError("caiu"),
        asyncpg.InterfaceError("pool fechado"),
        asyncpg.CheckViolationError("check"),
    ],
)
def test_eh_erro_de_banco(erro):
    assert eh_erro_de_banco(erro)


@pytest.mark.parametrize("erro", [ValueError("x"), KeyError("x"), RuntimeError("x"), None])
def test_nao_eh_erro_de_banco(erro):
    assert not eh_erro_de_banco(erro)


@pytest.mark.asyncio
@pytest.mark.parametrize("funcao", ["salvar_usuario", "salvar_alimentos", "registrar_refeicao"])
async def test_banco_fora_do_ar_no_r(bot_teste, gemini_falso, banco_falso, monkeypatch, funcao):
    gemini_falso.resposta = RespostaGemini(itens=[criar_item()], ignorados=[])

    async def falhar(*_):
        raise ConnectionRefusedError("conexão recusada")

    monkeypatch.setattr(handlers.db, funcao, falhar)
    assert await bot_teste.enviar("/r arroz") == [TEXTO_BANCO_FORA_DO_AR]


@pytest.mark.asyncio
async def test_banco_fora_do_ar_antes_do_gemini_nao_gasta_a_chamada(bot_teste, gemini_falso, monkeypatch):
    async def falhar(*_):
        raise OSError("conexão recusada")

    monkeypatch.setattr(handlers.db, "salvar_usuario", falhar)
    await bot_teste.enviar("/r arroz")
    assert gemini_falso.chamadas == []


@pytest.mark.asyncio
@pytest.mark.parametrize("texto", ["/peso", "/peso 82,4"])
async def test_banco_fora_do_ar_no_peso(bot_teste, monkeypatch, texto):
    async def falhar(*_):
        raise asyncpg.PostgresConnectionError("caiu")

    monkeypatch.setattr(handlers.db, "salvar_usuario", falhar)
    assert await bot_teste.enviar(texto) == [TEXTO_BANCO_FORA_DO_AR]


@pytest.mark.asyncio
async def test_erro_que_nao_e_de_banco_nao_responde_o_texto_do_banco(bot_teste, monkeypatch):
    async def falhar(*_):
        raise ValueError("defeito no código")

    monkeypatch.setattr(handlers.db, "salvar_usuario", falhar)
    respostas = await bot_teste.enviar("/peso")
    assert respostas == [TEXTO_ERRO_INESPERADO]
    assert TEXTO_BANCO_FORA_DO_AR not in respostas


@pytest.mark.asyncio
async def test_erro_inesperado_no_peso_ao_registrar(bot_teste, banco_falso, monkeypatch):
    async def falhar(*_):
        raise KeyError("defeito no código")

    monkeypatch.setattr(handlers.db, "registrar_peso", falhar)
    assert await bot_teste.enviar("/peso 82,4") == [TEXTO_ERRO_INESPERADO]


@pytest.mark.asyncio
@pytest.mark.parametrize("funcao", ["salvar_usuario", "salvar_alimentos", "registrar_refeicao"])
async def test_erro_inesperado_no_r(bot_teste, gemini_falso, banco_falso, monkeypatch, funcao):
    gemini_falso.resposta = RespostaGemini(itens=[criar_item()], ignorados=[])

    async def falhar(*_):
        raise ValueError("defeito no código")

    monkeypatch.setattr(handlers.db, funcao, falhar)
    assert await bot_teste.enviar("/r arroz") == [TEXTO_ERRO_INESPERADO]


@pytest.mark.asyncio
async def test_erro_inesperado_vai_para_o_log(bot_teste, monkeypatch, caplog):
    async def falhar(*_):
        raise ValueError("defeito no código")

    monkeypatch.setattr(handlers.db, "salvar_usuario", falhar)
    await bot_teste.enviar("/peso")
    assert "Erro ao processar um update" in caplog.text
    assert "defeito no código" in caplog.text


@pytest.mark.asyncio
async def test_resposta_de_erro_que_falha_nao_gera_novo_erro(bot_teste, monkeypatch, caplog):
    async def falhar(*_):
        raise ValueError("defeito no código")

    async def telegram_fora(*_, **__):
        raise NetworkError("telegram fora do ar")

    monkeypatch.setattr(handlers.db, "salvar_usuario", falhar)
    monkeypatch.setattr(Message, "reply_text", telegram_fora)

    assert await bot_teste.enviar("/peso") == []
    assert "Não consegui avisar a pessoa sobre o erro" in caplog.text

    # O bot segue vivo: a mensagem seguinte é processada normalmente.
    monkeypatch.undo()
    assert await bot_teste.enviar("/id") == [f"ID deste chat: {CHAT_AUTORIZADO}"]


@pytest.mark.asyncio
@pytest.mark.parametrize("erro", [ValueError("x"), OSError("x")])
async def test_erro_sem_mensagem_para_responder_nao_quebra(bot_teste, erro):
    # Update sem mensagem: erro fora de um comando.
    await handlers.tratar_erro(Update(update_id=1), SimpleNamespace(error=erro))
    await handlers.tratar_erro(None, SimpleNamespace(error=erro))


@pytest.mark.asyncio
async def test_tratar_erro_sem_update_nao_quebra():
    context = SimpleNamespace(error=OSError("rede"))
    await handlers.tratar_erro(None, context)
