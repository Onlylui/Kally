"""Handlers do bot. Etapa 1: filtro de chats autorizados, /id e eco."""

import logging

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

logger = logging.getLogger(__name__)


def eh_comando_id(texto: str | None) -> bool:
    """Diz se o texto é o comando /id (aceita também /id@nome_do_bot)."""
    if not texto:
        return False
    partes = texto.split(maxsplit=1)
    if not partes:
        return False
    comando = partes[0].split("@", maxsplit=1)[0]
    return comando.lower() == "/id"


def deve_processar(chat_id: int | None, texto: str | None, permitidos: set[int]) -> bool:
    """RN-002: só processa chats autorizados; o /id passa em qualquer chat."""
    if chat_id is not None and chat_id in permitidos:
        return True
    return eh_comando_id(texto)


async def filtrar_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Roda antes de todos os outros handlers e barra os chats não autorizados (RN-002)."""
    # No PTB, um erro aqui não impede os handlers seguintes de rodarem.
    # Por isso, se o filtro falhar, o update é barrado.
    try:
        permitidos: set[int] = context.bot_data["allowed_chat_ids"]
        chat = update.effective_chat
        mensagem = update.effective_message
        chat_id = chat.id if chat else None
        texto = mensagem.text if mensagem else None
        autorizado = deve_processar(chat_id, texto, permitidos)
    except Exception:
        logger.exception("Erro no filtro de chats; update barrado")
        raise ApplicationHandlerStop from None

    if not autorizado:
        logger.info("Update ignorado: chat %s não autorizado", chat_id)
        raise ApplicationHandlerStop


async def comando_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/id: responde com o ID do chat, para configurar o ALLOWED_CHAT_IDS."""
    await update.effective_message.reply_text(f"ID deste chat: {update.effective_chat.id}")


async def ecoar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot papagaio: repete o texto recebido. Será substituído nas próximas etapas."""
    await update.effective_message.reply_text(update.effective_message.text)


async def tratar_erro(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra no log qualquer erro de handler, para o bot não cair por uma mensagem."""
    logger.error("Erro ao processar um update", exc_info=context.error)
