"""Validação e chamada do Gemini. Nada aqui sai da máquina: há cliente falso e servidor local."""

import asyncio
import json
import logging
import math
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors

from app import gemini
from app.gemini import (
    FalhaGemini,
    ItemEstimado,
    RespostaGemini,
    eh_falha_passageira,
    normalizar_nome,
    validar_item,
)


def criar_item(**campos) -> ItemEstimado:
    valores = {
        "nome": "arroz",
        "texto": "150 g de arroz",
        "gramas": 150,
        "kcal_100g": 130,
        "proteina_100g": 2.5,
        "carbo_100g": 28,
        "gordura_100g": 0.3,
        "porcao_g": 45,
        "porcao_nome": "1 colher de servir",
        "alcoolico": False,
    }
    return ItemEstimado(**(valores | campos))


# --- normalizar_nome (P7) ---

@pytest.mark.parametrize(
    "nome, esperado",
    [
        ("feijão", "feijao"),
        ("Pão de Queijo", "pao de queijo"),
        ("  maçã  ", "maca"),
        ("AÇAÍ", "acai"),
        ("ovo", "ovo"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalizar_nome(nome, esperado):
    assert normalizar_nome(nome) == esperado


def test_normalizar_nao_mexe_em_plural_nem_em_nome_composto():
    # D11: sem regra por alimento. O singular é com o Gemini.
    assert normalizar_nome("Ovos") == "ovos"
    assert normalizar_nome("pão francês") == "pao frances"


# --- validar_item (RN-016) ---

def test_item_valido():
    assert validar_item(criar_item())


@pytest.mark.parametrize("kcal", [0, 900])
def test_limites_de_kcal_sao_validos(kcal):
    # Macros coerentes com cada limite: 100 g de gordura são 900 kcal.
    item = criar_item(kcal_100g=kcal, proteina_100g=0, carbo_100g=0, gordura_100g=kcal / 9)
    assert validar_item(item)


@pytest.mark.parametrize(
    "campos",
    [
        {"kcal_100g": -1},
        {"kcal_100g": 900.1},
        {"proteina_100g": -0.1},
        {"carbo_100g": -0.1},
        {"gordura_100g": -0.1},
        {"gramas": 0},
        {"gramas": -10},
        {"porcao_g": 0},
        {"porcao_g": -1},
        {"nome": ""},
        {"nome": "   "},
        {"texto": ""},
        {"texto": "  "},
        {"porcao_nome": ""},
        {"porcao_nome": "   "},
        {"gramas": math.inf},
        {"gramas": math.nan},
        {"kcal_100g": math.nan},
        {"porcao_g": math.inf},
        {"proteina_100g": math.inf, "alcoolico": True},
        {"carbo_100g": math.nan, "alcoolico": True},
        {"gordura_100g": math.inf, "alcoolico": True},
    ],
)
def test_item_invalido(campos):
    assert not validar_item(criar_item(**campos))


# --- tetos (D-040) ---

@pytest.mark.parametrize("campo", ["gramas", "porcao_g"])
def test_teto_de_gramas_aceita_o_limite_exato(campo):
    assert gemini.GRAMAS_MAXIMO == 10000
    assert validar_item(criar_item(**{campo: 10000}))


@pytest.mark.parametrize("campo", ["gramas", "porcao_g"])
@pytest.mark.parametrize("valor", [10000.01, 10001, 1e30])
def test_teto_de_gramas_recusa_o_que_passa_dele(campo, valor):
    assert not validar_item(criar_item(**{campo: valor}))


def criar_item_com_macro(macro: str, valor: float, alcoolico: bool) -> ItemEstimado:
    """Kcal coerente com o macro, para só o teto decidir."""
    macros = {"proteina_100g": 0, "carbo_100g": 0, "gordura_100g": 0, macro: valor}
    kcal = 900 if macro == "gordura_100g" else 400
    return criar_item(**macros, kcal_100g=kcal, alcoolico=alcoolico)


MACROS = ["proteina_100g", "carbo_100g", "gordura_100g"]


@pytest.mark.parametrize("macro", MACROS)
@pytest.mark.parametrize("alcoolico", [False, True])
def test_teto_de_macro_aceita_100(macro, alcoolico):
    assert validar_item(criar_item_com_macro(macro, 100, alcoolico))


@pytest.mark.parametrize("macro", MACROS)
@pytest.mark.parametrize("alcoolico", [False, True])
def test_teto_de_macro_recusa_acima_de_100(macro, alcoolico):
    assert not validar_item(criar_item_com_macro(macro, 100.1, alcoolico))


@pytest.mark.parametrize("campo", ["nome", "texto", "porcao_nome"])
@pytest.mark.parametrize("valor", ["ar\x00roz", "\x00", "arroz\x00"])
def test_nul_em_texto_e_invalido(campo, valor):
    assert not validar_item(criar_item(**{campo: valor}))


@pytest.mark.parametrize(
    "campos, valido",
    [
        # 4P + 4C + 9G = 120. Margem: 20% das kcal.
        ({"kcal_100g": 100, "proteina_100g": 30, "carbo_100g": 0, "gordura_100g": 0}, True),
        ({"kcal_100g": 150, "proteina_100g": 30, "carbo_100g": 0, "gordura_100g": 0}, True),
        ({"kcal_100g": 99, "proteina_100g": 30, "carbo_100g": 0, "gordura_100g": 0}, False),
        ({"kcal_100g": 151, "proteina_100g": 30, "carbo_100g": 0, "gordura_100g": 0}, False),
        # Com poucas kcal vale o mínimo de 10: café tem 2 kcal e quase nenhum macro.
        ({"kcal_100g": 2, "proteina_100g": 3, "carbo_100g": 0, "gordura_100g": 0}, True),
        ({"kcal_100g": 2, "proteina_100g": 3.1, "carbo_100g": 0, "gordura_100g": 0}, False),
        ({"kcal_100g": 0, "proteina_100g": 0, "carbo_100g": 0, "gordura_100g": 0}, True),
    ],
)
def test_coerencia_de_macros(campos, valido):
    assert validar_item(criar_item(**campos)) is valido


def test_alcoolico_dispensa_a_coerencia_de_macros():
    cerveja = {"kcal_100g": 43, "proteina_100g": 0.5, "carbo_100g": 3.5, "gordura_100g": 0}
    assert not validar_item(criar_item(**cerveja))
    assert validar_item(criar_item(**cerveja, alcoolico=True))


def test_alcoolico_nao_dispensa_as_outras_validacoes():
    assert not validar_item(criar_item(alcoolico=True, kcal_100g=901))
    assert not validar_item(criar_item(alcoolico=True, gramas=0))


# --- estimar com cliente falso ---

def criar_cliente_falso(resposta=None, erro=None):
    chamadas = []

    async def generate_content(**argumentos):
        chamadas.append(argumentos)
        if erro:
            raise erro
        return SimpleNamespace(parsed=resposta)

    modelos = SimpleNamespace(generate_content=generate_content)
    return SimpleNamespace(aio=SimpleNamespace(models=modelos)), chamadas


@pytest.mark.asyncio
async def test_estimar_devolve_a_resposta_validada():
    resposta = RespostaGemini(itens=[criar_item()], ignorados=["kkkk"])
    cliente, chamadas = criar_cliente_falso(resposta)

    assert await gemini.estimar(cliente, "modelo", "150 g de arroz kkkk") is resposta

    assert len(chamadas) == 1
    assert chamadas[0]["model"] == "modelo"
    assert chamadas[0]["contents"] == "150 g de arroz kkkk"
    configuracao = chamadas[0]["config"]
    assert configuracao.temperature == 0
    assert configuracao.system_instruction == gemini.PROMPT
    assert configuracao.response_schema is RespostaGemini
    assert "150 g de arroz kkkk" not in gemini.PROMPT


@pytest.mark.asyncio
async def test_estimar_com_lista_vazia_nao_e_falha():
    resposta = RespostaGemini(itens=[], ignorados=["kkkkk"])
    cliente, _ = criar_cliente_falso(resposta)
    assert (await gemini.estimar(cliente, "modelo", "kkkkk")).itens == []


@pytest.mark.asyncio
async def test_parsed_vazio_e_falha():
    # O SDK não lança exceção com JSON truncado, fora do schema ou sem candidatos.
    cliente, _ = criar_cliente_falso(None)
    with pytest.raises(FalhaGemini):
        await gemini.estimar(cliente, "modelo", "arroz")


@pytest.mark.asyncio
async def test_item_invalido_entre_validos_cancela_tudo():
    resposta = RespostaGemini(
        itens=[criar_item(), criar_item(nome="feijão", kcal_100g=1000), criar_item(nome="ovo")],
        ignorados=[],
    )
    cliente, _ = criar_cliente_falso(resposta)
    with pytest.raises(FalhaGemini):
        await gemini.estimar(cliente, "modelo", "arroz, feijão e ovo")


@pytest.mark.asyncio
@pytest.mark.parametrize("erro", [RuntimeError("cota"), OSError("rede"), ValueError("resposta")])
async def test_erro_da_chamada_vira_falha(erro):
    cliente, chamadas = criar_cliente_falso(erro=erro)
    with pytest.raises(FalhaGemini):
        await gemini.estimar(cliente, "modelo", "arroz")
    assert len(chamadas) == 1


async def dormir_falso(_segundos):
    """Não dorme de verdade: o teste não fica lento."""


@pytest.mark.asyncio
async def test_timeout_por_tentativa(monkeypatch):
    monkeypatch.setattr(gemini, "TIMEOUT_SEGUNDOS", 0.05)
    chamadas = []

    async def generate_content(**_):
        chamadas.append(1)
        await asyncio.sleep(5)

    modelos = SimpleNamespace(generate_content=generate_content)
    cliente = SimpleNamespace(aio=SimpleNamespace(models=modelos))
    with pytest.raises(FalhaGemini):
        await gemini.estimar(cliente, "modelo", "arroz", dormir=dormir_falso)
    # Tempo esgotado é passageiro: as 3 tentativas estouram.
    assert len(chamadas) == 3


def test_constantes_de_tempo():
    # RN-017 / P2 / P3
    assert gemini.TENTATIVAS == 3
    assert gemini.ESPERAS_SEGUNDOS == (2, 5)
    assert gemini.TIMEOUT_SEGUNDOS == 15
    assert gemini.ORCAMENTO_SEGUNDOS == 40
    assert gemini.MINIMO_PARA_TENTAR_SEGUNDOS == 5
    assert gemini.AVISO_SEGUNDOS == 2


# --- laço de tentativas (RN-017, P1, P2), com relógio e espera falsos ---

class TempoFalso:
    """Relógio que só anda quando o teste manda; `dormir` só soma e anota."""

    def __init__(self):
        self.agora = 0.0
        self.esperas = []

    def relogio(self) -> float:
        return self.agora

    async def dormir(self, segundos):
        self.esperas.append(segundos)
        self.agora += segundos


RESPOSTA_OK = RespostaGemini(itens=[criar_item()], ignorados=[])


def criar_cliente_roteiro(tempo: TempoFalso, roteiro):
    """Cada chamada consome um passo `(duracao, resultado)`: avança o relógio e lança ou devolve."""
    passos = iter(roteiro)
    chamadas = []

    async def generate_content(**_):
        chamadas.append(1)
        duracao, resultado = next(passos)
        tempo.agora += duracao
        if isinstance(resultado, BaseException):
            raise resultado
        return SimpleNamespace(parsed=resultado)

    modelos = SimpleNamespace(generate_content=generate_content)
    return SimpleNamespace(aio=SimpleNamespace(models=modelos)), chamadas


async def estimar_com_roteiro(tempo, roteiro, **argumentos):
    cliente, chamadas = criar_cliente_roteiro(tempo, roteiro)
    try:
        return await gemini.estimar(
            cliente, "modelo", "arroz", relogio=tempo.relogio, dormir=tempo.dormir, **argumentos
        ), chamadas
    except FalhaGemini as falha:
        falha.chamadas = chamadas
        raise


def erro_503():
    return errors.ServerError(503, {})


@pytest.mark.asyncio
async def test_503_e_depois_sucesso():
    tempo = TempoFalso()
    resposta, chamadas = await estimar_com_roteiro(tempo, [(1, erro_503()), (1, RESPOSTA_OK)])
    assert resposta is RESPOSTA_OK
    assert len(chamadas) == 2
    assert tempo.esperas == [2]


@pytest.mark.asyncio
async def test_503_duas_vezes_e_depois_sucesso():
    tempo = TempoFalso()
    resposta, chamadas = await estimar_com_roteiro(
        tempo, [(1, erro_503()), (1, erro_503()), (1, RESPOSTA_OK)]
    )
    assert resposta is RESPOSTA_OK
    assert len(chamadas) == 3
    assert tempo.esperas == [2, 5]


@pytest.mark.asyncio
async def test_503_tres_vezes_e_falha():
    tempo = TempoFalso()
    with pytest.raises(FalhaGemini) as falha:
        await estimar_com_roteiro(tempo, [(1, erro_503())] * 3)
    assert len(falha.value.chamadas) == 3
    assert tempo.esperas == [2, 5]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "erro", [errors.ClientError(429, {}), TimeoutError(), httpx.ConnectError("recusada")]
)
async def test_outras_falhas_passageiras_sao_repetidas(erro):
    tempo = TempoFalso()
    resposta, chamadas = await estimar_com_roteiro(tempo, [(1, erro), (1, RESPOSTA_OK)])
    assert resposta is RESPOSTA_OK
    assert len(chamadas) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "erro", [errors.ClientError(404, {}), errors.ClientError(400, {}), ValueError("x")]
)
async def test_falha_nao_passageira_nao_repete(erro):
    tempo = TempoFalso()
    with pytest.raises(FalhaGemini) as falha:
        await estimar_com_roteiro(tempo, [(1, erro), (1, RESPOSTA_OK)])
    assert len(falha.value.chamadas) == 1
    assert tempo.esperas == []


ITEM_INVALIDO = RespostaGemini(itens=[criar_item(kcal_100g=1000)], ignorados=[])


@pytest.mark.asyncio
@pytest.mark.parametrize("resultado", [None, ITEM_INVALIDO])
async def test_fora_do_schema_e_item_invalido_nao_repetem(resultado):
    tempo = TempoFalso()
    with pytest.raises(FalhaGemini) as falha:
        await estimar_com_roteiro(tempo, [(1, resultado), (1, RESPOSTA_OK)])
    assert len(falha.value.chamadas) == 1
    assert tempo.esperas == []


@pytest.mark.asyncio
async def test_503_e_depois_fora_do_schema_para_na_segunda():
    tempo = TempoFalso()
    with pytest.raises(FalhaGemini) as falha:
        await estimar_com_roteiro(tempo, [(1, erro_503()), (1, None), (1, RESPOSTA_OK)])
    assert len(falha.value.chamadas) == 2


@pytest.mark.asyncio
async def test_lista_vazia_nao_repete():
    tempo = TempoFalso()
    vazia = RespostaGemini(itens=[], ignorados=["kkkk"])
    resposta, chamadas = await estimar_com_roteiro(tempo, [(1, vazia)])
    assert resposta.itens == []
    assert len(chamadas) == 1


@pytest.mark.asyncio
async def test_orcamento_impede_a_terceira_tentativa(caplog):
    # 15 s esgotados + 2 s de espera + 15 s esgotados = 32 s; com a espera de 5 s sobrariam 3 s.
    tempo = TempoFalso()
    with caplog.at_level(logging.WARNING, logger="app.gemini"):
        with pytest.raises(FalhaGemini) as falha:
            await estimar_com_roteiro(tempo, [(15, TimeoutError()), (15, TimeoutError()), (1, RESPOSTA_OK)])
    assert len(falha.value.chamadas) == 2
    assert tempo.esperas == [2]
    assert "desistiu" in caplog.text


@pytest.mark.asyncio
async def test_limite_da_ultima_tentativa_respeita_o_orcamento(monkeypatch):
    tempo = TempoFalso()
    limites = []
    duracoes = iter([None, 10, None])  # None: esgota o limite recebido

    async def chamar_falso(cliente, modelo, texto, limite):
        limites.append(limite)
        duracao = next(duracoes)
        tempo.agora += limite if duracao is None else duracao
        if len(limites) < 3:
            raise TimeoutError if duracao is None else erro_503()
        return RESPOSTA_OK

    monkeypatch.setattr(gemini, "_chamar_uma_vez", chamar_falso)
    resposta = await gemini.estimar(None, "modelo", "arroz", relogio=tempo.relogio, dormir=tempo.dormir)

    # 15 + 2 + 10 + 5 = 32 s gastos: sobram 8 s para a terceira.
    assert resposta is RESPOSTA_OK
    assert limites == [15, 15, 8]
    assert tempo.esperas == [2, 5]


@pytest.mark.asyncio
@pytest.mark.parametrize("gasto_antes, tenta", [(30, False), (29.9, True)])
async def test_borda_do_minimo_para_tentar(gasto_antes, tenta):
    # Depois da 2ª falha e da espera de 5 s sobram 40 - gasto_antes - 5. Com 5 s exatos, desiste.
    tempo = TempoFalso()
    primeira = gasto_antes - 2 - 1  # 1ª tentativa + espera de 2 s + 2ª tentativa de 1 s
    roteiro = [(primeira, erro_503()), (1, erro_503()), (1, RESPOSTA_OK)]
    if tenta:
        resposta, chamadas = await estimar_com_roteiro(tempo, roteiro)
        assert resposta is RESPOSTA_OK
        assert len(chamadas) == 3
    else:
        with pytest.raises(FalhaGemini) as falha:
            await estimar_com_roteiro(tempo, roteiro)
        assert len(falha.value.chamadas) == 2


@pytest.mark.asyncio
async def test_antes_de_tentar_e_chamado_em_cada_tentativa():
    tempo = TempoFalso()
    avisos = []

    async def avisar():
        avisos.append(tempo.agora)

    resposta, _ = await estimar_com_roteiro(
        tempo, [(1, erro_503()), (1, erro_503()), (1, RESPOSTA_OK)], antes_de_tentar=avisar
    )
    assert resposta is RESPOSTA_OK
    assert len(avisos) == 3


@pytest.mark.asyncio
async def test_aviso_com_erro_nao_derruba_a_estimativa(caplog):
    tempo = TempoFalso()

    async def avisar():
        raise RuntimeError("telegram fora")

    with caplog.at_level(logging.WARNING, logger="app.gemini"):
        resposta, chamadas = await estimar_com_roteiro(tempo, [(1, RESPOSTA_OK)], antes_de_tentar=avisar)
    assert resposta is RESPOSTA_OK
    assert len(chamadas) == 1
    assert "RuntimeError" in caplog.text
    assert "telegram fora" not in caplog.text


@pytest.mark.asyncio
async def test_aviso_travado_e_cortado(monkeypatch, caplog):
    monkeypatch.setattr(gemini, "AVISO_SEGUNDOS", 0.01)
    tempo = TempoFalso()

    async def avisar():
        await asyncio.sleep(5)

    with caplog.at_level(logging.WARNING, logger="app.gemini"):
        resposta, _ = await estimar_com_roteiro(tempo, [(1, RESPOSTA_OK)], antes_de_tentar=avisar)
    assert resposta is RESPOSTA_OK
    assert "TimeoutError" in caplog.text


@pytest.mark.asyncio
async def test_tempo_do_aviso_conta_no_limite(monkeypatch):
    tempo = TempoFalso()
    limites = []

    async def avisar():
        tempo.agora += 30

    async def chamar_falso(cliente, modelo, texto, limite):
        limites.append(limite)
        return RESPOSTA_OK

    monkeypatch.setattr(gemini, "_chamar_uma_vez", chamar_falso)
    await gemini.estimar(
        None, "modelo", "arroz", antes_de_tentar=avisar, relogio=tempo.relogio, dormir=tempo.dormir
    )
    assert limites == [10]


@pytest.mark.asyncio
async def test_aviso_que_esgota_o_orcamento_desiste_sem_chamar():
    tempo = TempoFalso()
    avisos = []

    async def avisar():
        avisos.append(1)
        if len(avisos) == 2:
            tempo.agora += 32  # 1 + 2 + 32 = 35 s: sobram 5 s, não tenta

    with pytest.raises(FalhaGemini) as falha:
        await estimar_com_roteiro(tempo, [(1, erro_503()), (1, RESPOSTA_OK)], antes_de_tentar=avisar)
    assert len(falha.value.chamadas) == 1


@pytest.mark.asyncio
async def test_cancelamento_durante_a_espera_nao_vira_falha():
    entrou = asyncio.Event()

    async def dormir_para_sempre(_segundos):
        entrou.set()
        await asyncio.Event().wait()

    cliente, _ = criar_cliente_roteiro(TempoFalso(), [(0, erro_503())])
    tarefa = asyncio.create_task(gemini.estimar(cliente, "modelo", "arroz", dormir=dormir_para_sempre))
    await entrou.wait()
    tarefa.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tarefa


# --- estimar com o SDK de verdade, contra um servidor HTTP local ---

class ServidorFalso:
    """Imita o endpoint do Gemini e conta as requisições.

    `status` e `texto` podem ser listas: um valor por requisição, na ordem.
    """

    def __init__(self, status=200, texto="", atraso=0.0):
        self.status = status
        self.texto = texto
        self.atraso = atraso
        self.corpos = []

    def _da_vez(self, valor):
        if isinstance(valor, list):
            return valor[len(self.corpos) - 1]
        return valor

    async def atender(self, leitor, escritor):
        cabecalhos = (await leitor.readuntil(b"\r\n\r\n")).decode().lower()
        tamanho = next(
            int(linha.split(":")[1]) for linha in cabecalhos.splitlines() if linha.startswith("content-length")
        )
        self.corpos.append(json.loads(await leitor.readexactly(tamanho)))
        await asyncio.sleep(self.atraso)

        corpo = json.dumps(
            {"candidates": [{"content": {"role": "model", "parts": [{"text": self._da_vez(self.texto)}]}}]}
        ).encode()
        escritor.write(
            f"HTTP/1.1 {self._da_vez(self.status)} X\r\ncontent-type: application/json\r\n"
            f"content-length: {len(corpo)}\r\nconnection: close\r\n\r\n".encode()
            + corpo
        )
        await escritor.drain()
        escritor.close()


@pytest.fixture
def subir_servidor(monkeypatch):
    """Sobe o servidor falso e aponta o SDK para ele, com uma chave falsa."""

    async def subir(falso: ServidorFalso):
        servidor = await asyncio.start_server(falso.atender, "127.0.0.1", 0)
        porta = servidor.sockets[0].getsockname()[1]
        monkeypatch.setenv("GOOGLE_GEMINI_BASE_URL", f"http://127.0.0.1:{porta}")
        return servidor, gemini.criar_cliente("chave-falsa")

    return subir


ITEM_JSON = {
    "nome": "arroz",
    "texto": "150 g de arroz",
    "gramas": 150,
    "kcal_100g": 130,
    "proteina_100g": 2.5,
    "carbo_100g": 28,
    "gordura_100g": 0.3,
    "porcao_g": 45,
    "porcao_nome": "1 colher de servir",
    "alcoolico": False,
}


@pytest.mark.asyncio
async def test_sdk_com_resposta_valida(subir_servidor):
    falso = ServidorFalso(texto=json.dumps({"itens": [ITEM_JSON], "ignorados": ["kkkk"]}))
    servidor, cliente = await subir_servidor(falso)
    async with servidor:
        resposta = await gemini.estimar(cliente, "modelo-falso", "150 g de arroz kkkk")

    assert resposta.itens[0].nome == "arroz"
    assert resposta.ignorados == ["kkkk"]
    assert len(falso.corpos) == 1
    corpo = falso.corpos[0]
    assert corpo["contents"][0]["parts"][0]["text"] == "150 g de arroz kkkk"
    assert "systemInstruction" in corpo
    assert corpo["generationConfig"]["temperature"] == 0
    assert corpo["generationConfig"]["responseMimeType"] == "application/json"


@pytest.mark.asyncio
@pytest.mark.parametrize("status, tentativas", [(429, 3), (500, 3), (503, 3), (400, 1), (404, 1)])
async def test_sdk_com_erro_http_conta_as_tentativas(subir_servidor, status, tentativas):
    falso = ServidorFalso(status=status, texto="{}")
    servidor, cliente = await subir_servidor(falso)
    async with servidor:
        with pytest.raises(FalhaGemini):
            await gemini.estimar(cliente, "modelo-falso", "arroz", dormir=dormir_falso)
    assert len(falso.corpos) == tentativas


@pytest.mark.asyncio
async def test_sdk_503_e_depois_sucesso(subir_servidor):
    valido = json.dumps({"itens": [ITEM_JSON], "ignorados": []})
    falso = ServidorFalso(status=[503, 200], texto=["{}", valido])
    servidor, cliente = await subir_servidor(falso)
    async with servidor:
        resposta = await gemini.estimar(cliente, "modelo-falso", "arroz", dormir=dormir_falso)
    assert resposta.itens[0].nome == "arroz"
    assert len(falso.corpos) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("texto", ['{"itens": [{"nome": "arr', '{"outra": 1}', "não é json", ""])
async def test_sdk_com_resposta_fora_do_schema_e_falha(subir_servidor, texto):
    falso = ServidorFalso(texto=texto)
    servidor, cliente = await subir_servidor(falso)
    async with servidor:
        with pytest.raises(FalhaGemini):
            await gemini.estimar(cliente, "modelo-falso", "arroz")
    assert len(falso.corpos) == 1


@pytest.mark.asyncio
async def test_sdk_com_servidor_lento_respeita_o_timeout(subir_servidor, monkeypatch):
    monkeypatch.setattr(gemini, "TIMEOUT_SEGUNDOS", 0.2)
    falso = ServidorFalso(texto="{}", atraso=2)
    servidor, cliente = await subir_servidor(falso)
    async with servidor:
        with pytest.raises(FalhaGemini):
            await asyncio.wait_for(
                gemini.estimar(cliente, "modelo-falso", "arroz", dormir=dormir_falso), timeout=3
            )
    # Tempo esgotado é passageiro: as 3 tentativas chegam ao servidor.
    assert len(falso.corpos) == 3


# --- eh_falha_passageira (P1, RN-017) ---

@pytest.mark.parametrize(
    "erro, passageira",
    [
        (errors.ServerError(500, {}), True),
        (errors.ServerError(503, {}), True),
        (errors.ClientError(429, {}), True),
        (TimeoutError(), True),
        (httpx.ConnectError("recusada"), True),
        (httpx.ReadTimeout("lento"), True),
        (httpx.RemoteProtocolError("cortada"), True),
        (errors.ClientError(400, {}), False),
        (errors.ClientError(401, {}), False),
        (errors.ClientError(403, {}), False),
        (errors.ClientError(404, {}), False),
        (errors.APIError(302, {}), False),
        (ValueError(), False),
        (RuntimeError(), False),
        # P1 à risca: OSError solto não é falha de conexão do httpx.
        (OSError(), False),
        (ConnectionError(), False),
        (FalhaGemini(), False),
        # Cancelamento nunca vira nova tentativa.
        (asyncio.CancelledError(), False),
    ],
)
def test_eh_falha_passageira(erro, passageira):
    assert eh_falha_passageira(erro) is passageira


async def erro_do_sdk(cliente) -> BaseException:
    """Chama o SDK direto, sem passar por estimar, e devolve a exceção que ele lançou."""
    with pytest.raises(Exception) as capturado:
        await cliente.aio.models.generate_content(model="modelo-falso", contents="arroz")
    return capturado.value


@pytest.mark.asyncio
@pytest.mark.parametrize("status, passageira", [(503, True), (500, True), (429, True), (400, False), (404, False)])
async def test_sdk_erro_http_classificado(subir_servidor, status, passageira):
    falso = ServidorFalso(status=status, texto="{}")
    servidor, cliente = await subir_servidor(falso)
    async with servidor:
        erro = await erro_do_sdk(cliente)
    assert isinstance(erro, errors.APIError)
    assert erro.code == status
    assert eh_falha_passageira(erro) is passageira


@pytest.mark.asyncio
async def test_sdk_porta_fechada_e_passageira(monkeypatch):
    # Protege contra o SDK trocar o httpx por outro transporte (ex.: aiohttp).
    # Risco remoto aceito: outro processo ocupar a porta entre o close e a conexão.
    servidor = await asyncio.start_server(lambda *_: None, "127.0.0.1", 0)
    porta = servidor.sockets[0].getsockname()[1]
    servidor.close()
    await servidor.wait_closed()
    monkeypatch.setenv("GOOGLE_GEMINI_BASE_URL", f"http://127.0.0.1:{porta}")

    erro = await erro_do_sdk(gemini.criar_cliente("chave-falsa"))
    assert isinstance(erro, httpx.TransportError)
    assert eh_falha_passageira(erro)


# --- log ---

@pytest.mark.asyncio
async def test_log_tem_a_duracao_e_nao_tem_o_texto(caplog):
    resposta = RespostaGemini(itens=[criar_item()], ignorados=[])
    cliente, _ = criar_cliente_falso(resposta)
    with caplog.at_level(logging.INFO, logger="app.gemini"):
        await gemini.estimar(cliente, "modelo", "texto-secreto-da-pessoa")
    assert "Gemini respondeu em" in caplog.text
    assert "na tentativa 1/3" in caplog.text
    assert "texto-secreto-da-pessoa" not in caplog.text


@pytest.mark.asyncio
async def test_log_da_falha_passageira_nao_vaza_detalhes(caplog):
    tempo = TempoFalso()
    secreto = errors.ServerError(503, {"error": {"message": "chave-secreta"}})
    cliente, _ = criar_cliente_roteiro(tempo, [(0.8, secreto), (1, RESPOSTA_OK)])
    with caplog.at_level(logging.INFO, logger="app.gemini"):
        await gemini.estimar(
            cliente, "modelo", "texto-secreto-da-pessoa", relogio=tempo.relogio, dormir=tempo.dormir
        )
    assert "Gemini tentativa 1/3 falhou em 0.8 s: ServerError" in caplog.text
    assert "na tentativa 2/3" in caplog.text
    assert "chave-secreta" not in caplog.text
    assert "texto-secreto-da-pessoa" not in caplog.text


@pytest.mark.asyncio
async def test_log_de_resposta_invalida_tem_o_motivo(caplog):
    tempo = TempoFalso()
    cliente, _ = criar_cliente_roteiro(tempo, [(1.2, None)])
    with caplog.at_level(logging.WARNING, logger="app.gemini"):
        with pytest.raises(FalhaGemini):
            await gemini.estimar(cliente, "modelo", "arroz", relogio=tempo.relogio, dormir=tempo.dormir)
    assert "Gemini tentativa 1/3 respondeu em 1.2 s: resposta fora do schema" in caplog.text


@pytest.mark.asyncio
async def test_log_de_falha_nao_tem_a_mensagem_do_erro(caplog):
    cliente, _ = criar_cliente_falso(erro=RuntimeError("chave-secreta na mensagem"))
    with caplog.at_level(logging.INFO, logger="app.gemini"):
        with pytest.raises(FalhaGemini):
            await gemini.estimar(cliente, "modelo", "texto-secreto-da-pessoa")
    assert "RuntimeError" in caplog.text
    assert "chave-secreta" not in caplog.text
    assert "texto-secreto-da-pessoa" not in caplog.text
