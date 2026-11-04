"""Handlers do bot: filtro de chats autorizados, /id, /peso e eco."""

import logging
import re
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from app import db

logger = logging.getLogger(__name__)

# RN-001: o dia é contado no fuso de São Paulo, nunca no fuso do sistema.
FUSO = ZoneInfo("America/Sao_Paulo")

# Lista própria (sem locale, que depende do sistema). Índice = date.weekday(): 0 é segunda.
DIAS_DA_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

PESO_MINIMO = Decimal("30")
PESO_MAXIMO = Decimal("300")

# Número com até 2 casas (vírgula ou ponto), com "kg" opcional, colado ou separado.
_PESO = re.compile(r"(\d+)(?:[.,](\d{1,2}))?\s*(?:kg)?", re.IGNORECASE | re.ASCII)

TEXTO_PESO_FORA_DA_FAIXA = "Peso fora do esperado (30 a 300 kg). Ex.: /peso 82,4"
TEXTO_PESO_NAO_ENTENDI = "Não entendi o peso. Ex.: /peso 82,4"


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


# --- /peso (RN-012) ---

def ler_peso(texto: str) -> Decimal | None:
    """Lê o peso digitado: 82,4 · 82.4 · 82 · 82,4kg · 82,4 kg. Qualquer outra coisa é None.

    Não confere a faixa de 30 a 300 kg: isso é com peso_na_faixa.
    """
    achado = _PESO.fullmatch(texto.strip())
    if not achado:
        return None
    inteiro, decimais = achado.groups()
    return Decimal(f"{inteiro}.{decimais}" if decimais else inteiro)


def peso_na_faixa(peso: Decimal) -> bool:
    """RN-012: aceita de 30 a 300 kg, com os limites."""
    return PESO_MINIMO <= peso <= PESO_MAXIMO


def formatar_peso(peso: Decimal) -> str:
    """Vírgula decimal, sem zeros sobrando à direita: 82.40 → 82,4; 82.00 → 82."""
    texto = format(peso, "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def formatar_data(dia: date) -> str:
    """DD/MM. Ex.: 28/10"""
    return dia.strftime("%d/%m")


def formatar_dia_semana(dia: date) -> str:
    """Dia da semana abreviado e DD/MM. Ex.: dom 01/11"""
    return f"{DIAS_DA_SEMANA[dia.weekday()]} {formatar_data(dia)}"


def data_hora_sao_paulo(momento: datetime) -> tuple[date, time]:
    """Converte o horário de envio da mensagem (UTC) para data e hora de São Paulo (RN-001, RN-007)."""
    local = momento.astimezone(FUSO)
    return local.date(), local.time().replace(microsecond=0)


def resposta_peso_registrado(nome: str, peso: Decimal, anterior: tuple[Decimal, date] | None) -> str:
    if anterior is None:
        return f"{nome}: {formatar_peso(peso)} kg registrado (primeira pesagem)"
    peso_anterior, data_anterior = anterior
    return (
        f"{nome}: {formatar_peso(peso)} kg registrado "
        f"(anterior: {formatar_peso(peso_anterior)} kg em {formatar_data(data_anterior)})"
    )


def resposta_ultimo_peso(nome: str, ultimo: tuple[Decimal, date] | None) -> str:
    if ultimo is None:
        return f"{nome}: nenhuma pesagem registrada ainda. Ex.: /peso 82,4"
    peso, dia = ultimo
    return f"{nome}: {formatar_peso(peso)} kg em {formatar_dia_semana(dia)}"


async def comando_peso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/peso 82,4 registra; /peso sozinho mostra a última pesagem (RN-012)."""
    mensagem = update.effective_message
    usuario = update.effective_user
    pool = context.bot_data["pool"]
    nome = usuario.first_name

    # Cria o usuário no primeiro comando e mantém o nome atualizado.
    await db.salvar_usuario(pool, usuario.id, nome)

    texto = " ".join(context.args or [])
    if not texto.strip():
        ultimo = await db.ultimo_peso(pool, usuario.id)
        await mensagem.reply_text(resposta_ultimo_peso(nome, ultimo))
        return

    peso = ler_peso(texto)
    if peso is None:
        await mensagem.reply_text(TEXTO_PESO_NAO_ENTENDI)
        return
    if not peso_na_faixa(peso):
        await mensagem.reply_text(TEXTO_PESO_FORA_DA_FAIXA)
        return

    # RN-007: vale o horário de envio da mensagem, não o do processamento.
    data, hora = data_hora_sao_paulo(mensagem.date)
    anterior = await db.registrar_peso(pool, usuario.id, update.effective_chat.id, peso, data, hora)
    await mensagem.reply_text(resposta_peso_registrado(nome, peso, anterior))


async def ecoar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot papagaio: repete o texto recebido. Será substituído nas próximas etapas."""
    await update.effective_message.reply_text(update.effective_message.text)


async def tratar_erro(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra no log qualquer erro de handler, para o bot não cair por uma mensagem."""
    logger.error("Erro ao processar um update", exc_info=context.error)
