# Etapa 4 · T4 — Extrair o fluxo do `/r` e o "digitando…"

Documento de implementação da **T4** da [etapa 4](etapa-4-resiliencia-gemini.md#t4--extrair-o-fluxo-do-r-e-o-digitando). Detalha a seção T4 do plano com o que foi decidido na rodada de planejamento de 16/11/2026 (plano do `kally-python`, revisão do `kally-revisor` e respostas do usuário) e no ajuste de 17/11/2026 ([seção 0](#0-ajuste-de-17112026)).

**Para quem:** `kally-python` (implementa), `kally-revisor` (revisa o diff contra este documento) e o usuário (testa no Telegram).

**Status:** implementada no commit `0615ae8`; ajuste de 17/11/2026 (D-049) implementado, aguardando o teste do usuário · **Depende de:** T3 (commit `453a186`) · **Linha de base do ajuste:** 365 testes passando.

Em caso de conflito, valem nesta ordem: [etapa-4-decisoes.md](etapa-4-decisoes.md), RN-017, o plano da etapa 4 e este documento. Se o código atual contradisser este documento, **pare e pergunte**.

---

## 0. Ajuste de 17/11/2026

**Motivo:** no teste no Telegram, o "digitando…" sumia depois de uns 5 s. A versão do commit `0615ae8` mandava o aviso só antes de cada tentativa do Gemini, e o Telegram apaga o aviso sozinho: numa tentativa longa (até 15 s), nas esperas de 2 s e 5 s e na gravação, o chat ficava sem indicação até a resposta.

**Decisão:** [D-049](../decisoes.md#d-049--digitando-contínuo-durante-o-r), que revisa a P3. O "digitando…" fica visível durante todo o `/r`: sai no início e é renovado a cada 4 s até o fim, fora do orçamento de 40 s. O mecanismo mora no `handlers.py` (`digitando`), e o `antes_de_tentar` da T3 foi removido do `gemini.py`.

As seções abaixo já descrevem o comportamento depois do ajuste.

## 1. Escopo

**Entra:**
1. O miolo do `/r` (estimar, gravar e montar a resposta) vira a função `processar_refeicao`, que o botão da T6 vai reaproveitar.
2. O "digitando…" contínuo (D-049): `processar_refeicao` roda inteira dentro de `async with digitando(...)`.
3. No ajuste: remover `antes_de_tentar`, `_avisar` e `AVISO_SEGUNDOS` de `app/gemini.py`, com os testes deles.
4. O `andamento.md` fica em "em andamento, T4".

**Fica fora:**
- **T5:** textos novos (`TEXTO_TENTANDO_DE_NOVO`, `TEXTO_PEDIDO_EXPIRADO`, `TEXTO_SO_O_DONO`), pendentes (`guardar_pendente`, `retirar_pendente`, `VALIDADE_PENDENTE`), `teclado_tentar` e o botão na falha.
- **T6:** `botao_tentar`, `CallbackQueryHandler` no `main.py`, ajustes no `tratar_erro` e no `filtrar_chats`.
- **T7:** comentários de decisões substituídas e ajustes de docs.
- **Não muda:** `app/main.py`, prompt, tempos do Gemini, banco, migrações, `.env.example`, textos do bot e `requirements.txt`. O `app/gemini.py` muda só no ajuste (remoção do aviso).

O comportamento visível do `/r` continua igual, a não ser pelo "digitando…". Na falha do Gemini, a resposta continua o `TEXTO_FALHA_GEMINI` atual, **sem botão**.

## 2. Regras e decisões cobertas

| Ref. | Como a T4 atende |
|---|---|
| RN-001 / RN-007 | Data e hora da refeição vêm do `momento` (o `message.date` do `/r`), convertido por `data_hora_sao_paulo`. O relógio só escolhe o texto "hoje" / "total de DD/MM". |
| RN-002 | O filtro de chats continua antes de tudo: chat não autorizado não recebe "digitando…". |
| RN-013 / RN-016 | Fluxo de estimativa e gravação igual ao de hoje. |
| RN-017 / P3 / D-049 | "digitando…" visível durante todo o `/r` (tentativas, esperas e gravação), renovado a cada 4 s. Falha de um envio só vai para o log. |
| P8 | O `momento` entra por parâmetro, para o clique da T6 gravar com a data do `/r` original. |
| D-047 | A fila de updates continua; o fluxo fica numa função só, sem depender da fila. A tarefa de renovação pertence a cada `/r`. |

## 3. Decisões tomadas

Respostas do usuário em 16/11/2026, com o parecer do revisor, e o ajuste de 17/11/2026:

1. **Retorno:** `processar_refeicao` devolve `str` (e não `str | None`). Todos os caminhos devolvem texto; a falha é exceção.
2. **"digitando…" contínuo (17/11/2026, D-049; substitui a decisão de 16/11/2026 de mandar só antes de cada tentativa, sem renovação):**
   - o primeiro sai no início do `processar_refeicao`; os seguintes, a cada `DIGITANDO_RENOVAR_SEGUNDOS = 4`, numa tarefa paralela;
   - cada envio tem até `DIGITANDO_LIMITE_SEGUNDOS = 2`; uma falha ou demora só perde aquela renovação e vai para o log como `warning`, só com o tipo do erro;
   - a tarefa para ao sair do bloco: sucesso, nenhum alimento, `FalhaGemini`, erro de banco ou cancelamento;
   - fica fora do orçamento de 40 s do Gemini;
   - ressalvas aceitas: se um envio já tiver saído quando o `/r` termina, o aviso pode aparecer por até ~5 s depois da resposta; no clique da T6, editar a mensagem não apaga o aviso.
3. **`salvar_usuario`:** fica no `comando_r`, **fora** de `processar_refeicao`. A T6 **não** chama de novo: se existe pendente, o usuário já foi salvo. No clique, usar `usuario_id` e `nome` **do pendente**, não do `effective_user`.
4. **`conftest.py`:** mudanças aprovadas, com os ajustes do revisor (seção 5).
5. **`andamento.md`:** "em andamento, T4"; no ajuste, "Última atualização" passa a 17/11/2026.

## 4. Código

### 4.1 `app/handlers.py` — o `digitando`

Constantes:

```python
DIGITANDO_RENOVAR_SEGUNDOS = 4
DIGITANDO_LIMITE_SEGUNDOS = 2
```

Funções:
- `async def mandar_digitando(bot: Bot, chat_id: int) -> None`: um envio de `ChatAction.TYPING` com `asyncio.timeout(DIGITANDO_LIMITE_SEGUNDOS)`. O limite é lido **dentro** da função (não como padrão de parâmetro), para o `monkeypatch` dos testes funcionar. `except Exception` registra `Aviso de digitando falhou: <TipoDoErro>`; nunca captura `CancelledError`.
- `async def _renovar_digitando(bot, chat_id, dormir) -> None`: em laço, `await dormir(DIGITANDO_RENOVAR_SEGUNDOS)` e `await mandar_digitando(...)`.
- `digitando(bot: Bot, chat_id: int, dormir=asyncio.sleep)`, com `@asynccontextmanager`:
  1. `await mandar_digitando(...)`: o primeiro é aguardado, porque numa resposta rápida a tarefa nem chegaria a rodar;
  2. `asyncio.create_task(_renovar_digitando(...))`;
  3. `yield` dentro de `try`;
  4. no `finally`: `tarefa.cancel()` e `await asyncio.wait([tarefa])`. O `asyncio.wait` espera a tarefa terminar sem lançar o `CancelledError` dela; um `await tarefa` lançaria esse erro, que se confundiria com o cancelamento do próprio `/r` (bot desligando), que precisa continuar subindo.

`dormir` existe só para os testes.

### 4.2 `app/handlers.py` — `processar_refeicao`

```python
async def processar_refeicao(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    usuario_id: int,
    nome: str,
    descricao: str,
    texto_limpo: str,
    momento: datetime,
) -> str:
```

Comportamento:
1. Todo o corpo roda dentro de `async with digitando(context.bot, chat_id):`.
2. Chama `gemini.estimar(context.bot_data["gemini"], context.bot_data["gemini_modelo"], texto_limpo)`, sem aviso.
3. Sem itens: devolve `TEXTO_R_NENHUM_ALIMENTO` e não grava nada.
4. Com itens, segue como o `comando_r` fazia:
   - `data_hora_sao_paulo(momento)` para data e hora (RN-007);
   - `db.salvar_alimentos`, `calcular_itens`, `db.registrar_refeicao` (refeição e itens numa transação só, como antes);
   - `resposta_refeicao(..., hoje=datetime.now(FUSO).date(), ...)` e devolve o texto.
5. **Não trata erros:** `FalhaGemini` sobe para quem chamou; erro de banco sobe para o `tratar_erro`. O `digitando` para nos dois casos.
6. **Não chama** `salvar_usuario` (seção 3, item 3).
7. Não toca em pendentes (P10 continua livre para a T6).

Nenhum SQL novo: usa as funções de `app/db.py` que já existem.

### 4.3 `comando_r`

1. `salvar_usuario` continua **antes** das validações. Há teste que exige que banco fora do ar não gaste a chamada ao Gemini.
2. `extrair_descricao` e `limpar_descricao`; validações de vazio (`TEXTO_R_SEM_DESCRICAO`) e de tamanho (`TEXTO_R_MUITO_LONGO`).
3. `texto = await processar_refeicao(context, chat.id, usuario.id, nome, descricao, texto_limpo, mensagem.date)` dentro de `try`.
4. `except gemini.FalhaGemini`: responde `TEXTO_FALHA_GEMINI` (o atual) e encerra.
5. Sucesso ou "nenhum alimento": `reply_text(texto)`. A resposta sai depois que o `digitando` parou.

### 4.4 `app/gemini.py` (ajuste)

Removidos: o parâmetro `antes_de_tentar` do `estimar`, a função `_avisar` e a constante `AVISO_SEGUNDOS`. O orçamento passa a contar só as tentativas e as esperas. `relogio` e `dormir` continuam.

## 5. Testes

Rodar com `docker compose run --rm bot pytest`. Nenhum teste dorme de verdade (a única exceção é o limite de 10 ms de `test_envio_travado_e_cortado`) nem troca o `asyncio.sleep` global.

### 5.1 `tests/conftest.py`

- **`RequisicaoFalsa`:**
  - lista `eventos`, com uma entrada por chamada, na ordem: `("acao", chat_id, action)` para `sendChatAction` e `("mensagem", texto)` para envios;
  - opção `falhar_acoes`: quando ligada, o `sendChatAction` devolve status 400 com `{"ok": false, "description": "..."}`, e o PTB lança `BadRequest`;
  - a lista `enviadas` continua igual.
- **`bot_teste`:** expõe a requisição (para ler `eventos` e ligar `falhar_acoes`).
- **`gemini_falso`:** assinatura `(cliente, modelo, texto)`, sem `antes_de_tentar` (removido no ajuste); registra `("gemini", texto)` na mesma lista `eventos` da requisição, para os testes provarem a ordem.

### 5.2 `tests/test_digitando.py` (novo, ajuste)

O mecanismo, com um `BotFalso` e um `DormirFalso`. O `DormirFalso` volta na hora nas `voltas` primeiras chamadas; na seguinte, libera um `asyncio.Event` (`chegou`) e trava. Os testes esperam com `asyncio.wait_for(chegou.wait(), 1)`: quando ele é liberado, as renovações anteriores já terminaram. A tarefa de renovação é achada por `asyncio.all_tasks()` e conferida com `done()`.

| Teste | O que verifica |
|---|---|
| `test_constantes_de_tempo` | 4 s e 2 s. |
| `test_primeiro_sai_na_entrada_no_chat_certo` | Antes de o bloco rodar, já saiu `(CHAT, "typing")`. |
| `test_renova_a_cada_intervalo` | 3 voltas → 4 envios; todos os pedidos de espera são de 4 s. |
| `test_para_ao_sair` | Depois do bloco, a tarefa terminou e não sai mais nada. |
| `test_para_com_excecao_e_deixa_ela_subir` (`FalhaGemini`, `ConnectionRefusedError`) | A exceção sobe e a tarefa terminou. |
| `test_para_no_cancelamento` | O cancelamento do `/r` sobe como `CancelledError` e a tarefa de renovação terminou. |
| `test_falha_numa_renovacao_nao_para_as_seguintes` | A 2ª falha, a 3ª sai; o log tem só o tipo do erro. |
| `test_falha_no_primeiro_nao_impede_o_bloco` | O bloco roda; o log tem o aviso. |
| `test_envio_travado_e_cortado` | Com o limite trocado por 0,01 s, o envio travado é cortado e o log tem `TimeoutError`. |

### 5.3 `tests/test_refeicao.py`

| Teste | O que verifica |
|---|---|
| `test_r_manda_digitando_no_chat_certo_antes_do_gemini` | Com o `digitando` real, `eventos` é `[("acao", CHAT_AUTORIZADO, "typing"), ("gemini", ...), ("mensagem", ...)]`. |
| `test_r_vazio_e_longo_nao_mandam_digitando` (parametrizado) | Nenhum evento `"acao"`. |
| `test_falha_no_digitando_nao_impede_o_registro` | `gemini_falso` com `falhar_acoes=True`: a refeição é gravada, a resposta é a de sucesso e o `caplog` do `app.handlers` tem `Aviso de digitando falhou: BadRequest`. |
| `test_r_grava_dentro_do_digitando` | Com um `digitando` falso que registra `("entrou", chat)` e `("saiu", chat)`: `entrou`, `gemini`, `banco`, `saiu`, `mensagem`. |
| `test_digitando_para_na_falha_do_gemini` | `entrou`, `gemini`, `saiu`, `mensagem` com `TEXTO_FALHA_GEMINI`. |
| `test_digitando_para_no_erro_de_banco` (`salvar_alimentos`, `registrar_refeicao`) | `entrou`, `gemini`, `saiu`, `mensagem` com `TEXTO_BANCO_FORA_DO_AR`. |
| `test_processar_refeicao_usa_o_momento_recebido` | Chamada direta com `context` montado a partir do `bot_teste.app`. `momento` = segunda 02:30 UTC grava como domingo 23:30 em São Paulo (RN-001/RN-007), e a resposta diz "total de DD/MM". |
| `test_processar_refeicao_deixa_falha_gemini_subir` | `gemini_falso.erro = FalhaGemini()`: a função lança `FalhaGemini` e nada é gravado. |
| `test_processar_refeicao_sem_alimento_devolve_o_texto` | Devolve `TEXTO_R_NENHUM_ALIMENTO` e não grava. |

Também conferem os eventos: o `/r` em chat não autorizado (nenhum `"acao"`, RN-002), a falha do Gemini e o "nenhum alimento" (o "digitando…" sai antes da resposta).

**Removido no ajuste:** `test_digitando_em_cada_tentativa` (o aviso não é mais por tentativa).

### 5.4 `tests/test_gemini.py` (ajuste)

Removidos os 5 testes do aviso (`antes_de_tentar` em cada tentativa, aviso com erro, aviso travado, tempo do aviso no limite, aviso que esgota o orçamento) e a linha de `AVISO_SEGUNDOS` em `test_constantes_de_tempo`. O `test_cancelamento_durante_a_espera_nao_vira_falha` fica.

## 6. Docs

- **Commit `0615ae8`:** `Docs/andamento.md` em "em andamento, T4".
- **Ajuste de 17/11/2026:**
  - `Docs/decisoes.md`: D-049 novo e nota no D-048;
  - `Docs/etapas/etapa-4-decisoes.md`: P3 revista e linhas do `gemini.py` e do `handlers.py` na seção 4;
  - `Docs/regras-de-negocio.md`: RN-017 ("Enquanto trabalha no `/r`…");
  - `Docs/etapas/etapa-4-resiliencia-gemini.md`: nota na T3, T4 com o mecanismo novo, ressalva na T6 e passo 5 da seção 3;
  - este documento;
  - `Docs/andamento.md`: "Última atualização" de 17/11/2026.
- `Docs/exemplos.md` não muda.

## 7. Pronto quando

- [x] `processar_refeicao` existe com a assinatura da seção 4.2 e o `comando_r` a usa.
- [x] O `/r` inteiro roda dentro do `digitando`, que para em sucesso, falha, erro de banco e cancelamento.
- [x] `antes_de_tentar`, `_avisar` e `AVISO_SEGUNDOS` removidos do `gemini.py`, com os testes deles.
- [x] `docker compose run --rm bot pytest` passa, resultado real informado.
- [x] Nenhuma mudança em `app/main.py`, banco, migrações ou textos.
- [x] Docs da seção 6 atualizados.
- [ ] Teste do usuário no Telegram.
- [ ] Nenhum commit (o usuário faz).

## 8. Como testar no Telegram

1. `docker compose restart bot` e `docker compose logs -f bot`.
2. `/r 150 g de arroz e 2 ovos`: aparece "KALLY está digitando…" e logo a resposta com o total. O log mostra a tentativa 1/3.
3. `/r` vazio e `/r` com mais de 500 caracteres: os textos de sempre, sem "digitando…".
4. `/r kkkkk`: "Não identifiquei nenhum alimento…".
5. `/peso` e `/id`: iguais a antes.
6. **Gemini fora do ar** (bloqueio do `/etc/hosts` da seção 3 do plano da etapa 4):
   - `/r 1 banana`: o "digitando…" fica visível, sem interrupção, durante as 3 tentativas e as esperas, até a resposta;
   - o log mostra as 3 tentativas com as esperas;
   - a resposta é o texto atual de falha, **ainda sem botão** (vem na T5);
   - desbloquear o Gemini no fim.
7. Conferir no banco que o registro do passo 2 tem a data e a hora do envio:
   ```bash
   docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT id, data, hora, descricao, kcal FROM refeicoes ORDER BY id DESC LIMIT 3"'
   ```

## 9. Pontos em aberto

- **Queda do bot depois de recriar o `db`** (vista na T1): o bot só voltou com `docker compose restart bot`. O usuário ainda não decidiu se entra em "Pendências herdadas" do `andamento.md`. **Não registrar sem confirmação.**
