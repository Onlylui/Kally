from types import SimpleNamespace

import pytest

from app import main as modulo_main
from app.main import ler_chat_ids, ler_config_gemini


def test_vazio_ou_ausente_vira_conjunto_vazio():
    assert ler_chat_ids(None) == set()
    assert ler_chat_ids("") == set()


def test_um_id():
    assert ler_chat_ids("-1001234567890") == {-1001234567890}


def test_varios_ids_com_espacos():
    assert ler_chat_ids("-100123, -100456 ,789") == {-100123, -100456, 789}


def test_ignora_virgula_sobrando():
    assert ler_chat_ids("-100123,") == {-100123}


def test_valor_invalido_lanca_erro():
    with pytest.raises(ValueError):
        ler_chat_ids("-100123,abc")


# --- inicialização do banco ---


@pytest.mark.asyncio
async def test_banco_fora_do_ar_impede_a_inicializacao(monkeypatch):
    async def criar_pool_falhando():
        raise OSError("conexão recusada")

    monkeypatch.setattr(modulo_main.db, "criar_pool", criar_pool_falhando)
    app = SimpleNamespace(bot_data={})
    with pytest.raises(RuntimeError, match="não consegui conectar ao banco"):
        await modulo_main.iniciar_banco(app)
    assert "pool" not in app.bot_data


@pytest.mark.asyncio
async def test_migracao_com_erro_fecha_o_pool_e_impede_a_inicializacao(monkeypatch):
    pool = SimpleNamespace(fechado=False)

    async def fechar():
        pool.fechado = True

    pool.close = fechar

    async def criar_pool():
        return pool

    async def aplicar_migracoes_falhando(pool):
        raise ValueError("erro de sintaxe")

    monkeypatch.setattr(modulo_main.db, "criar_pool", criar_pool)
    monkeypatch.setattr(modulo_main.db, "aplicar_migracoes", aplicar_migracoes_falhando)
    app = SimpleNamespace(bot_data={})
    with pytest.raises(RuntimeError, match="falha ao aplicar as migrações"):
        await modulo_main.iniciar_banco(app)
    assert pool.fechado
    assert "pool" not in app.bot_data


# --- configuração do Gemini ---


def test_config_do_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-falsa")
    monkeypatch.setenv("GEMINI_MODEL", "modelo-falso")
    assert ler_config_gemini() == ("chave-falsa", "modelo-falso")


@pytest.mark.parametrize("faltando", ["GEMINI_API_KEY", "GEMINI_MODEL"])
@pytest.mark.parametrize("valor", [None, ""])
def test_bot_nao_sobe_sem_a_config_do_gemini(monkeypatch, faltando, valor):
    monkeypatch.setenv("TELEGRAM_TOKEN", "123:abc")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-falsa")
    monkeypatch.setenv("GEMINI_MODEL", "modelo-falso")
    if valor is None:
        monkeypatch.delenv(faltando)
    else:
        monkeypatch.setenv(faltando, valor)
    monkeypatch.setattr(modulo_main, "load_dotenv", lambda: None)

    def nao_deve_chegar_aqui():
        raise AssertionError("o bot tentou subir sem a configuração do Gemini")

    monkeypatch.setattr(modulo_main.Application, "builder", nao_deve_chegar_aqui)

    with pytest.raises(SystemExit, match=faltando):
        modulo_main.main()
