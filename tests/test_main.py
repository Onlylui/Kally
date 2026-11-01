import pytest

from app.main import ler_chat_ids


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
