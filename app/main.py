"""Ponto de entrada do KALLY. Roda no container: docker compose up -d (D-035)."""

import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, TypeHandler, filters

from app import db, gemini, handlers

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
    # O SDK do Gemini registra detalhes das chamadas em INFO.
    logging.getLogger("google_genai").setLevel(logging.WARNING)


async def iniciar_banco(app: Application) -> None:
    """post_init: conecta ao banco e aplica as migrações antes de receber mensagens.

    Se algo falhar, lança RuntimeError e o bot não sobe pela metade.
    """
    try:
        pool = await db.criar_pool()
    except Exception as erro:
        raise RuntimeError(f"não consegui conectar ao banco ({type(erro).__name__}: {erro})") from erro

    try:
        await db.aplicar_migracoes(pool)
    except Exception as erro:
        await pool.close()
        raise RuntimeError(f"falha ao aplicar as migrações ({type(erro).__name__}: {erro})") from erro

    app.bot_data["pool"] = pool
    logger.info("Banco conectado e migrações em dia.")
    logger.info("KALLY iniciado (polling).")


async def fechar_banco(app: Application) -> None:
    """post_shutdown: devolve as conexões do pool."""
    pool = app.bot_data.get("pool")
    if pool is not None:
        await pool.close()


def ler_config_gemini() -> tuple[str, str]:
    """Devolve a chave e o modelo do Gemini. Sem eles o bot não sobe."""
    chave = os.getenv("GEMINI_API_KEY")
    modelo = os.getenv("GEMINI_MODEL")
    if not chave:
        raise SystemExit("Faltou o GEMINI_API_KEY no .env.")
    if not modelo:
        raise SystemExit("Faltou o GEMINI_MODEL no .env.")
    return chave, modelo


def registrar_handlers(app: Application) -> None:
    """Liga os comandos. Mensagem sem comando não tem handler: o bot fica em silêncio."""
    # RN-002: o filtro roda no grupo -1, antes de todos os outros handlers.
    app.add_handler(TypeHandler(Update, handlers.filtrar_chats), group=-1)
    app.add_handler(CommandHandler("id", handlers.comando_id, filters=filters.UpdateType.MESSAGE))
    app.add_handler(CommandHandler("peso", handlers.comando_peso, filters=filters.UpdateType.MESSAGE))
    app.add_handler(CommandHandler("r", handlers.comando_r, filters=filters.UpdateType.MESSAGE))
    app.add_error_handler(handlers.tratar_erro)


def main() -> None:
    configurar_log()
    load_dotenv()

    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("Faltou o TELEGRAM_TOKEN no .env.")

    chave_gemini, modelo_gemini = ler_config_gemini()

    try:
        permitidos = ler_chat_ids(os.getenv("ALLOWED_CHAT_IDS"))
    except ValueError:
        raise SystemExit("ALLOWED_CHAT_IDS inválido: use números inteiros separados por vírgula.") from None

    if not permitidos:
        logger.warning("ALLOWED_CHAT_IDS vazio: o bot só vai responder ao /id.")
    else:
        logger.info("%d chat(s) autorizado(s).", len(permitidos))

    app = (
        Application.builder()
        .token(token)
        .post_init(iniciar_banco)
        .post_shutdown(fechar_banco)
        .build()
    )
    app.bot_data["allowed_chat_ids"] = permitidos
    app.bot_data["gemini"] = gemini.criar_cliente(chave_gemini)
    app.bot_data["gemini_modelo"] = modelo_gemini

    registrar_handlers(app)

    logger.info("Iniciando o KALLY...")
    # Sem drop_pending_updates: mensagens enviadas com o bot fora do ar
    # são processadas quando ele volta (RN-007).
    try:
        app.run_polling()
    except RuntimeError as erro:
        logger.critical("KALLY parou na inicialização: %s", erro)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
