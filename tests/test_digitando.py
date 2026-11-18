"""O "digitando…" contínuo do /r (RN-017, D-049), sem Telegram e sem dormir de verdade."""

import asyncio
import logging

import pytest

from app import handlers
from app.gemini import FalhaGemini
from app.handlers import digitando

CHAT = -100123


class BotFalso:
    """Guarda cada send_chat_action. `falhar_em` lista as chamadas (1, 2, …) que dão erro;
    com `travar`, o envio nunca termina."""

    def __init__(self, falhar_em=(), travar=False):
        self.acoes = []
        self.falhar_em = set(falhar_em)
        self.travar = travar

    async def send_chat_action(self, chat_id, action):
        self.acoes.append((chat_id, action))
        if self.travar:
            await asyncio.Event().wait()
        if len(self.acoes) in self.falhar_em:
            raise RuntimeError("telegram fora")


class DormirFalso:
    """Anota os segundos pedidos. As `voltas` primeiras chamadas voltam na hora; a seguinte
    libera `chegou` e trava. Quando `chegou` é liberado, as `voltas` renovações já terminaram."""

    def __init__(self, voltas: int):
        self.voltas = voltas
        self.pedidos = []
        self.chegou = asyncio.Event()

    async def __call__(self, segundos):
        self.pedidos.append(segundos)
        if len(self.pedidos) > self.voltas:
            self.chegou.set()
            await asyncio.Event().wait()


def tarefa_de_renovacao(antes: set) -> asyncio.Task:
    """A única tarefa criada desde `antes`: a que renova o "digitando…"."""
    novas = asyncio.all_tasks() - antes
    assert len(novas) == 1
    return novas.pop()


def test_constantes_de_tempo():
    assert handlers.DIGITANDO_RENOVAR_SEGUNDOS == 4
    assert handlers.DIGITANDO_LIMITE_SEGUNDOS == 2


@pytest.mark.asyncio
async def test_primeiro_sai_na_entrada_no_chat_certo():
    bot = BotFalso()
    async with digitando(bot, CHAT, dormir=DormirFalso(0)):
        # Antes de o bloco fazer qualquer coisa, o primeiro já saiu.
        assert bot.acoes == [(CHAT, "typing")]


@pytest.mark.asyncio
async def test_renova_a_cada_intervalo():
    bot = BotFalso()
    dormir = DormirFalso(3)
    async with digitando(bot, CHAT, dormir=dormir):
        await asyncio.wait_for(dormir.chegou.wait(), 1)
        assert len(bot.acoes) == 4  # o primeiro mais 3 renovações
    assert dormir.pedidos == [4, 4, 4, 4]


@pytest.mark.asyncio
async def test_para_ao_sair():
    bot = BotFalso()
    dormir = DormirFalso(1)
    antes = asyncio.all_tasks()
    async with digitando(bot, CHAT, dormir=dormir):
        tarefa = tarefa_de_renovacao(antes)
        await asyncio.wait_for(dormir.chegou.wait(), 1)
    assert tarefa.done()
    assert len(bot.acoes) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("erro", [FalhaGemini(), ConnectionRefusedError("conexão recusada")])
async def test_para_com_excecao_e_deixa_ela_subir(erro):
    bot = BotFalso()
    antes = asyncio.all_tasks()
    with pytest.raises(type(erro)):
        async with digitando(bot, CHAT, dormir=DormirFalso(0)):
            tarefa = tarefa_de_renovacao(antes)
            raise erro
    assert tarefa.done()
    assert bot.acoes == [(CHAT, "typing")]


@pytest.mark.asyncio
async def test_para_no_cancelamento():
    bot = BotFalso()
    entrou = asyncio.Event()
    renovacao = {}

    async def corpo():
        antes = asyncio.all_tasks()
        async with digitando(bot, CHAT, dormir=DormirFalso(0)):
            renovacao["tarefa"] = tarefa_de_renovacao(antes)
            entrou.set()
            await asyncio.Event().wait()

    tarefa_do_r = asyncio.create_task(corpo())
    await asyncio.wait_for(entrou.wait(), 1)
    tarefa_do_r.cancel()
    # O cancelamento do /r continua subindo: não é engolido pelo digitando.
    with pytest.raises(asyncio.CancelledError):
        await tarefa_do_r
    assert renovacao["tarefa"].done()


@pytest.mark.asyncio
async def test_falha_numa_renovacao_nao_para_as_seguintes(caplog):
    bot = BotFalso(falhar_em={2})
    dormir = DormirFalso(2)
    with caplog.at_level(logging.WARNING, logger="app.handlers"):
        async with digitando(bot, CHAT, dormir=dormir):
            await asyncio.wait_for(dormir.chegou.wait(), 1)
    assert len(bot.acoes) == 3
    assert "Aviso de digitando falhou: RuntimeError" in caplog.text
    assert "telegram fora" not in caplog.text  # só o tipo do erro


@pytest.mark.asyncio
async def test_falha_no_primeiro_nao_impede_o_bloco(caplog):
    bot = BotFalso(falhar_em={1})
    rodou = False
    with caplog.at_level(logging.WARNING, logger="app.handlers"):
        async with digitando(bot, CHAT, dormir=DormirFalso(0)):
            rodou = True
    assert rodou
    assert "Aviso de digitando falhou: RuntimeError" in caplog.text


@pytest.mark.asyncio
async def test_envio_travado_e_cortado(monkeypatch, caplog):
    # Espera real de 10 ms: é o limite de tempo que está sendo testado.
    monkeypatch.setattr(handlers, "DIGITANDO_LIMITE_SEGUNDOS", 0.01)
    bot = BotFalso(travar=True)
    rodou = False
    with caplog.at_level(logging.WARNING, logger="app.handlers"):
        async with digitando(bot, CHAT, dormir=DormirFalso(0)):
            rodou = True
    assert rodou
    assert "Aviso de digitando falhou: TimeoutError" in caplog.text
