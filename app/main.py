"""Ponto de entrada do KALLY. Rodar com: python -m app.main"""

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, TypeHandler, filters

from app import handlers

logger = logging.getLogger(__name__)


def ler_chat_ids(valor: str | None) -> set[int]:
    """Converte o ALLOWED_CHAT_IDS num conjunto de inteiros.

    Vazio ou ausente vira conjunto vazio (o bot só responde ao /id).
    Lança ValueError se algum item não for número inteiro.
    """
    if not valor:
        return set()
    ids = set()
    for parte in valor.split(","):
        parte = parte.strip()
        if parte:
            ids.add(int(parte))
    return ids


def configurar_log() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    # O httpx registra a URL de cada requisição, e a URL do Telegram contém o token.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    configurar_log()
    load_dotenv()

    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("Faltou o TELEGRAM_TOKEN no .env.")

    try:
        permitidos = ler_chat_ids(os.getenv("ALLOWED_CHAT_IDS"))
    except ValueError:
        raise SystemExit("ALLOWED_CHAT_IDS inválido: use números inteiros separados por vírgula.") from None

    if not permitidos:
        logger.warning("ALLOWED_CHAT_IDS vazio: o bot só vai responder ao /id.")
    else:
        logger.info("%d chat(s) autorizado(s).", len(permitidos))

    app = Application.builder().token(token).build()
    app.bot_data["allowed_chat_ids"] = permitidos

    # RN-002: o filtro roda no grupo -1, antes de todos os outros handlers.
    app.add_handler(TypeHandler(Update, handlers.filtrar_chats), group=-1)
    app.add_handler(CommandHandler("id", handlers.comando_id, filters=filters.UpdateType.MESSAGE))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE,
            handlers.ecoar,
        )
    )
    app.add_error_handler(handlers.tratar_erro)

    logger.info("KALLY iniciado (polling).")
    # Sem drop_pending_updates: mensagens enviadas com o bot fora do ar
    # são processadas quando ele volta (RN-007).
    app.run_polling()


if __name__ == "__main__":
    main()
