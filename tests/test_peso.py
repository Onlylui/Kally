from datetime import date, datetime, time, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import handlers
from app.handlers import (
    TEXTO_PESO_FORA_DA_FAIXA,
    TEXTO_PESO_NAO_ENTENDI,
    comando_peso,
    data_hora_sao_paulo,
    formatar_data,
    formatar_dia_semana,
    formatar_peso,
    ler_peso,
    peso_na_faixa,
    resposta_peso_registrado,
    resposta_ultimo_peso,
)


# --- ler_peso ---

@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("82,4", Decimal("82.4")),
        ("82.4", Decimal("82.4")),
        ("82", Decimal("82")),
        ("82,4kg", Decimal("82.4")),
        ("82,4 kg", Decimal("82.4")),
        ("82,4 KG", Decimal("82.4")),
        ("82kg", Decimal("82")),
        ("82,45", Decimal("82.45")),
        ("  82,4  ", Decimal("82.4")),
        ("824", Decimal("824")),  # é um número; a faixa é conferida à parte
    ],
)
def test_ler_peso_valido(texto, esperado):
    assert ler_peso(texto) == esperado


@pytest.mark.parametrize(
    "texto",
    ["82,456", "-82,4", "", "   ", "abc", "82,", ",5", "82,4 kilos", "kg", "82 4", "oitenta", "82,4kg extra"],
)
def test_ler_peso_invalido(texto):
    assert ler_peso(texto) is None


# --- faixa de 30 a 300 kg ---

@pytest.mark.parametrize("peso", ["30", "300", "82.4", "30.00", "300.00"])
def test_peso_dentro_da_faixa(peso):
    assert peso_na_faixa(Decimal(peso))


@pytest.mark.parametrize("peso", ["29.99", "300.01", "0", "824"])
def test_peso_fora_da_faixa(peso):
    assert not peso_na_faixa(Decimal(peso))


# --- formatação ---

@pytest.mark.parametrize(
    "peso, esperado",
    [
        ("82.40", "82,4"),
        ("82.00", "82"),
        ("82.4", "82,4"),
        ("82.45", "82,45"),
        ("82", "82"),
        ("100.00", "100"),
        ("30.05", "30,05"),
    ],
)
def test_formatar_peso(peso, esperado):
    assert formatar_peso(Decimal(peso)) == esperado


def test_formatar_data():
    assert formatar_data(date(2026, 10, 28)) == "28/10"
    assert formatar_data(date(2026, 1, 5)) == "05/01"


@pytest.mark.parametrize(
    "dia, esperado",
    [
        (date(2026, 10, 26), "seg 26/10"),
        (date(2026, 10, 27), "ter 27/10"),
        (date(2026, 10, 28), "qua 28/10"),
        (date(2026, 10, 29), "qui 29/10"),
        (date(2026, 10, 30), "sex 30/10"),
        (date(2026, 10, 31), "sáb 31/10"),
        (date(2026, 11, 1), "dom 01/11"),
    ],
)
def test_formatar_dia_semana(dia, esperado):
    assert formatar_dia_semana(dia) == esperado


# --- fuso (RN-001, RN-007) ---

def test_segunda_0230_utc_conta_como_domingo_em_sao_paulo():
    enviada = datetime(2026, 11, 2, 2, 30, tzinfo=timezone.utc)  # segunda, 02:30 UTC
    data, hora = data_hora_sao_paulo(enviada)
    assert data == date(2026, 11, 1)
    assert formatar_dia_semana(data) == "dom 01/11"
    assert hora == time(23, 30)


def test_horario_do_meio_do_dia():
    enviada = datetime(2026, 11, 1, 10, 15, 42, tzinfo=timezone.utc)
    assert data_hora_sao_paulo(enviada) == (date(2026, 11, 1), time(7, 15, 42))


# --- respostas (tabela 5.9) ---

def test_resposta_registrado_com_anterior():
    texto = resposta_peso_registrado("João", Decimal("82.4"), (Decimal("83.10"), date(2026, 10, 28)))
    assert texto == "João: 82,4 kg registrado (anterior: 83,1 kg em 28/10)"


def test_resposta_primeira_pesagem():
    texto = resposta_peso_registrado("Maria", Decimal("64.8"), None)
    assert texto == "Maria: 64,8 kg registrado (primeira pesagem)"


def test_resposta_consulta():
    texto = resposta_ultimo_peso("João", (Decimal("82.40"), date(2026, 11, 1)))
    assert texto == "João: 82,4 kg em dom 01/11"


def test_resposta_consulta_sem_pesagem():
    assert resposta_ultimo_peso("João", None) == "João: nenhuma pesagem registrada ainda. Ex.: /peso 82,4"


def test_textos_de_erro():
    assert TEXTO_PESO_FORA_DA_FAIXA == "Peso fora do esperado (30 a 300 kg). Ex.: /peso 82,4"
    assert TEXTO_PESO_NAO_ENTENDI == "Não entendi o peso. Ex.: /peso 82,4"


# --- comando_peso com banco falso (sem Postgres e sem Telegram) ---

class MensagemFalsa:
    def __init__(self, momento):
        self.date = momento
        self.respostas = []

    async def reply_text(self, texto):
        self.respostas.append(texto)


@pytest.fixture
def banco_falso(monkeypatch):
    """Troca as funções do db por versões em memória e guarda as chamadas."""
    chamadas = {"usuarios": [], "pesos": []}
    estado = {"anterior": None, "ultimo": None}

    async def salvar_usuario(pool, telegram_id, nome):
        chamadas["usuarios"].append((telegram_id, nome))

    async def registrar_peso(pool, telegram_id, chat_id, peso_kg, data, hora):
        chamadas["pesos"].append((telegram_id, chat_id, peso_kg, data, hora))
        return estado["anterior"]

    async def ultimo_peso(pool, telegram_id):
        return estado["ultimo"]

    monkeypatch.setattr(handlers.db, "salvar_usuario", salvar_usuario)
    monkeypatch.setattr(handlers.db, "registrar_peso", registrar_peso)
    monkeypatch.setattr(handlers.db, "ultimo_peso", ultimo_peso)
    return chamadas, estado


def criar(args, momento=datetime(2026, 11, 2, 2, 30, tzinfo=timezone.utc)):
    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=-100123),
        effective_user=SimpleNamespace(id=111, first_name="João"),
        effective_message=MensagemFalsa(momento),
    )
    context = SimpleNamespace(args=args, bot_data={"pool": object()})
    return update, context


@pytest.mark.asyncio
async def test_comando_registra_no_dia_de_sao_paulo(banco_falso):
    chamadas, estado = banco_falso
    estado["anterior"] = (Decimal("83.10"), date(2026, 10, 28))
    update, context = criar(["82,4"])

    await comando_peso(update, context)

    assert chamadas["usuarios"] == [(111, "João")]
    assert chamadas["pesos"] == [(111, -100123, Decimal("82.4"), date(2026, 11, 1), time(23, 30))]
    assert update.effective_message.respostas == ["João: 82,4 kg registrado (anterior: 83,1 kg em 28/10)"]


@pytest.mark.asyncio
async def test_comando_com_kg_separado(banco_falso):
    chamadas, _ = banco_falso
    update, context = criar(["82,4", "kg"])
    await comando_peso(update, context)
    assert chamadas["pesos"][0][2] == Decimal("82.4")
    assert update.effective_message.respostas == ["João: 82,4 kg registrado (primeira pesagem)"]


@pytest.mark.asyncio
async def test_comando_sem_numero_consulta(banco_falso):
    chamadas, estado = banco_falso
    estado["ultimo"] = (Decimal("82.40"), date(2026, 11, 1))
    update, context = criar([])
    await comando_peso(update, context)
    assert chamadas["usuarios"] == [(111, "João")]
    assert chamadas["pesos"] == []
    assert update.effective_message.respostas == ["João: 82,4 kg em dom 01/11"]


@pytest.mark.asyncio
async def test_comando_sem_numero_e_sem_pesagem(banco_falso):
    update, context = criar([])
    await comando_peso(update, context)
    assert update.effective_message.respostas == ["João: nenhuma pesagem registrada ainda. Ex.: /peso 82,4"]


@pytest.mark.asyncio
@pytest.mark.parametrize("args, esperado", [(["824"], TEXTO_PESO_FORA_DA_FAIXA), (["abc"], TEXTO_PESO_NAO_ENTENDI)])
async def test_comando_valor_invalido_nao_registra(banco_falso, args, esperado):
    chamadas, _ = banco_falso
    update, context = criar(args)
    await comando_peso(update, context)
    assert chamadas["pesos"] == []
    assert update.effective_message.respostas == [esperado]
