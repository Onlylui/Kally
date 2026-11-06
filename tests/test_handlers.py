from types import SimpleNamespace

import pytest
from telegram.ext import ApplicationHandlerStop

from app.handlers import deve_processar, eh_comando_id, filtrar_chats

PERMITIDOS = {-100123}


# --- eh_comando_id ---

@pytest.mark.parametrize("texto", ["/id", "/id@KallyBot", "/ID", "/id qualquer coisa"])
def test_reconhece_comando_id(texto):
    assert eh_comando_id(texto)


@pytest.mark.parametrize("texto", [None, "", "   ", "id", "/identidade", "/r arroz", "olá /id"])
def test_nao_e_comando_id(texto):
    assert not eh_comando_id(texto)


# --- deve_processar (RN-002) ---

def test_chat_autorizado_processa_qualquer_mensagem():
    assert deve_processar(-100123, "arroz e feijão", PERMITIDOS)
    assert deve_processar(-100123, None, PERMITIDOS)


def test_chat_nao_autorizado_ignora_mensagem():
    assert not deve_processar(-999, "arroz e feijão", PERMITIDOS)
    assert not deve_processar(-999, "/r arroz", PERMITIDOS)


def test_chat_nao_autorizado_aceita_id():
    assert deve_processar(-999, "/id", PERMITIDOS)


def test_sem_chats_autorizados_so_id_passa():
    assert not deve_processar(-100123, "oi", set())
    assert deve_processar(-100123, "/id", set())


def test_update_sem_chat_e_ignorado():
    assert not deve_processar(None, None, PERMITIDOS)


# --- handlers com objetos falsos (sem chamar o Telegram) ---

class MensagemFalsa:
    def __init__(self, texto):
        self.text = texto
        self.respostas = []

    async def reply_text(self, texto):
        self.respostas.append(texto)


def criar_update(chat_id, texto):
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id),
        effective_message=MensagemFalsa(texto),
    )


def criar_context():
    return SimpleNamespace(bot_data={"allowed_chat_ids": PERMITIDOS})


@pytest.mark.asyncio
async def test_filtro_barra_chat_nao_autorizado():
    with pytest.raises(ApplicationHandlerStop):
        await filtrar_chats(criar_update(-999, "oi"), criar_context())


@pytest.mark.asyncio
async def test_filtro_deixa_passar_chat_autorizado():
    await filtrar_chats(criar_update(-100123, "oi"), criar_context())


@pytest.mark.asyncio
async def test_filtro_deixa_passar_id_em_chat_nao_autorizado():
    await filtrar_chats(criar_update(-999, "/id"), criar_context())


@pytest.mark.asyncio
async def test_filtro_barra_update_sem_chat_e_sem_mensagem():
    update = SimpleNamespace(effective_chat=None, effective_message=None)
    with pytest.raises(ApplicationHandlerStop):
        await filtrar_chats(update, criar_context())


@pytest.mark.asyncio
async def test_filtro_barra_quando_da_erro():
    # bot_data sem a chave força um KeyError dentro do filtro
    context = SimpleNamespace(bot_data={})
    with pytest.raises(ApplicationHandlerStop):
        await filtrar_chats(criar_update(-100123, "oi"), context)
