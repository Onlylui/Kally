import pytest

from app.db import PASTA_MIGRACOES, ordenar_migracoes


def test_ordem_pelo_numero_e_nao_pelo_texto():
    nomes = ["010_dez.sql", "002_dois.sql", "001_inicial.sql"]
    assert ordenar_migracoes(nomes) == [
        (1, "001_inicial.sql"),
        (2, "002_dois.sql"),
        (10, "010_dez.sql"),
    ]


def test_ignora_arquivos_que_nao_sao_sql():
    assert ordenar_migracoes(["001_inicial.sql", "LEIAME.md", ".gitkeep"]) == [(1, "001_inicial.sql")]


@pytest.mark.parametrize("nome", ["inicial.sql", "001.sql", "abc_inicial.sql", "001-inicial.sql"])
def test_nome_fora_do_padrao_da_erro(nome):
    with pytest.raises(ValueError):
        ordenar_migracoes([nome])


def test_numero_repetido_da_erro():
    with pytest.raises(ValueError):
        ordenar_migracoes(["001_inicial.sql", "001_outra.sql"])


def test_pasta_do_projeto_tem_a_001():
    nomes = [arquivo.name for arquivo in PASTA_MIGRACOES.iterdir()]
    assert ordenar_migracoes(nomes)[0] == (1, "001_inicial.sql")
