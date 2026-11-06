"""Handlers do bot: filtro de chats autorizados, /id, /peso e /r."""

import logging
import re
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

import asyncpg
from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from app import db, gemini

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

LIMITE_DESCRICAO = 500

TEXTO_R_SEM_DESCRICAO = "Descreva o que comeu, ex.: /r 150 g de arroz e 1 filé de frango"
TEXTO_R_MUITO_LONGO = "Descrição muito longa. Use até 500 caracteres."
TEXTO_R_NENHUM_ALIMENTO = (
    "Não identifiquei nenhum alimento. Descreva o que comeu, ex.: /r 150 g de arroz e 1 filé de frango"
)
TEXTO_FALHA_GEMINI = "Não consegui estimar agora. Nada foi registrado, tente de novo em instantes."
# Não diz "nada foi registrado": a confirmação do commit pode se perder com a refeição já gravada.
TEXTO_BANCO_FORA_DO_AR = "Não consegui confirmar o registro agora. Tente de novo em instantes."
TEXTO_ERRO_INESPERADO = "Algo deu errado. Tente de novo em instantes."


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


# --- /r (RN-013, RN-016, RN-017) ---

def extrair_descricao(texto: str) -> str:
    """Tira o /r ou /r@bot e devolve o resto como a pessoa escreveu, com as quebras de linha."""
    partes = texto.split(maxsplit=1)
    return partes[1] if len(partes) > 1 else ""


def limpar_descricao(texto: str) -> str:
    """Reduz os espaços repetidos em cada linha e remove as linhas vazias."""
    linhas = [" ".join(linha.split()) for linha in texto.splitlines()]
    return "\n".join(linha for linha in linhas if linha)


def para_decimal(valor: float) -> Decimal:
    """Passa por str para o Decimal não herdar o erro de representação do float."""
    return Decimal(str(valor))


def alimentos_para_salvar(itens: list[gemini.ItemEstimado]) -> list[dict]:
    """Monta as linhas de `alimentos` com o nome normalizado (D-034)."""
    return [
        {
            "nome": gemini.normalizar_nome(item.nome),
            "kcal_100g": para_decimal(item.kcal_100g),
            "proteina_100g": para_decimal(item.proteina_100g),
            "carbo_100g": para_decimal(item.carbo_100g),
            "gordura_100g": para_decimal(item.gordura_100g),
            "porcao_g": para_decimal(item.porcao_g),
            "porcao_nome": item.porcao_nome.strip(),
        }
        for item in itens
    ]


def _proporcional(valor_100g: Decimal, gramas: Decimal, casas: str) -> Decimal:
    return (valor_100g * gramas / 100).quantize(Decimal(casas), rounding=ROUND_HALF_UP)


def calcular_itens(itens: list[gemini.ItemEstimado], base: dict) -> list[dict]:
    """Calcula cada item com os valores da base e os gramas do Gemini (P2).

    Kcal inteira e macros com 1 casa (P4).
    """
    calculados = []
    for item in itens:
        alimento = base[gemini.normalizar_nome(item.nome)]
        gramas = para_decimal(item.gramas)
        calculados.append(
            {
                "alimento_id": alimento["id"],
                "nome": item.nome.strip(),  # a resposta usa o nome como veio do Gemini (P10)
                "texto": item.texto.strip(),
                "gramas": gramas,
                "kcal": _proporcional(alimento["kcal_100g"], gramas, "1"),
                "proteina_g": _proporcional(alimento["proteina_100g"], gramas, "0.1"),
                "carbo_g": _proporcional(alimento["carbo_100g"], gramas, "0.1"),
                "gordura_g": _proporcional(alimento["gordura_100g"], gramas, "0.1"),
            }
        )
    return calculados


def formatar_kcal(kcal: int | Decimal) -> str:
    """Inteiro com ponto no milhar. Ex.: 1420 → 1.420"""
    return f"{int(kcal):,}".replace(",", ".")


def formatar_gramas(gramas: Decimal) -> str:
    """No máximo 1 casa, com vírgula. Ex.: 150.0 → 150; 62.5 → 62,5"""
    return formatar_peso(gramas.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def resposta_refeicao(
    nome: str,
    itens: list[dict],
    total_dia: int,
    data: date,
    hoje: date,
    ignorados: list[str],
) -> str:
    """Monta a resposta do /r. `hoje` entra por parâmetro para o texto não depender do relógio."""
    kcal = sum(item["kcal"] for item in itens)
    dia = "total hoje" if data == hoje else f"total de {formatar_data(data)}"
    linhas = [
        f"{nome}: +{formatar_kcal(kcal)} kcal · {dia}: {formatar_kcal(total_dia)} kcal",
        " · ".join(
            f"{item['nome']} {formatar_gramas(item['gramas'])} g · {formatar_kcal(item['kcal'])} kcal"
            for item in itens
        ),
    ]
    trechos = [trecho.strip() for trecho in ignorados if trecho.strip()]
    if trechos:
        linhas.append(f"Ignorei: {', '.join(trechos)}")
    return "\n".join(linhas)


async def comando_r(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/r <descrição>: estima com o Gemini, grava a refeição e responde com o total do dia."""
    mensagem = update.effective_message
    usuario = update.effective_user
    pool = context.bot_data["pool"]
    nome = usuario.first_name

    await db.salvar_usuario(pool, usuario.id, nome)

    # `descricao` fica como a pessoa escreveu; só o texto limpo vai ao Gemini.
    descricao = extrair_descricao(mensagem.text)
    texto_limpo = limpar_descricao(descricao)
    if not texto_limpo:
        await mensagem.reply_text(TEXTO_R_SEM_DESCRICAO)
        return
    if len(texto_limpo) > LIMITE_DESCRICAO:
        await mensagem.reply_text(TEXTO_R_MUITO_LONGO)
        return

    try:
        estimativa = await gemini.estimar(
            context.bot_data["gemini"],
            context.bot_data["gemini_modelo"],
            texto_limpo,
        )
    except gemini.FalhaGemini:
        await mensagem.reply_text(TEXTO_FALHA_GEMINI)
        return

    if not estimativa.itens:
        await mensagem.reply_text(TEXTO_R_NENHUM_ALIMENTO)
        return

    # RN-007: vale o horário de envio da mensagem, não o do processamento.
    data, hora = data_hora_sao_paulo(mensagem.date)

    base = await db.salvar_alimentos(pool, alimentos_para_salvar(estimativa.itens))
    itens = calcular_itens(estimativa.itens, base)
    total_dia = await db.registrar_refeicao(
        pool,
        usuario.id,
        update.effective_chat.id,
        descricao,
        int(sum(item["kcal"] for item in itens)),
        sum(item["proteina_g"] for item in itens),
        sum(item["carbo_g"] for item in itens),
        sum(item["gordura_g"] for item in itens),
        data,
        hora,
        itens,
    )

    # O relógio só decide o texto ("hoje" ou a data), nunca o dia da refeição (P5).
    hoje = datetime.now(FUSO).date()
    await mensagem.reply_text(resposta_refeicao(nome, itens, total_dia, data, hoje, estimativa.ignorados))


# --- Erros ---

def eh_erro_de_banco(erro: BaseException | None) -> bool:
    """Diz se o erro veio do banco. O OSError cobre conexão recusada e banco fora da rede.

    Revisar quando o /exportar trouxer I/O de arquivo (etapa 8).
    """
    return isinstance(erro, (asyncpg.PostgresError, asyncpg.InterfaceError, OSError))


async def tratar_erro(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra no log qualquer erro de handler e avisa a pessoa, se houver a quem responder."""
    logger.error("Erro ao processar um update", exc_info=context.error)

    mensagem = update.effective_message if isinstance(update, Update) else None
    if mensagem is None:
        return
    texto = TEXTO_BANCO_FORA_DO_AR if eh_erro_de_banco(context.error) else TEXTO_ERRO_INESPERADO
    try:
        await mensagem.reply_text(texto)
    except Exception:
        logger.exception("Não consegui avisar a pessoa sobre o erro")
