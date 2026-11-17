# Etapa 4 · T4 — Extrair o fluxo do `/r` e o "digitando…"

Documento de implementação da **T4** da [etapa 4](etapa-4-resiliencia-gemini.md#t4--extrair-o-fluxo-do-r-e-o-digitando). Detalha a seção T4 do plano com o que foi decidido na rodada de planejamento de 16/11/2026: plano do `kally-python`, revisão do `kally-revisor` e respostas do usuário.

**Para quem:** `kally-python` (implementa), `kally-revisor` (revisa o diff contra este documento) e o usuário (testa no Telegram).

**Status:** ⏳ aprovado para implementar · **Depende de:** T3 (commit `453a186`) · **Linha de base:** 356 testes passando.

Em caso de conflito, valem nesta ordem: [etapa-4-decisoes.md](etapa-4-decisoes.md), RN-017, o plano da etapa 4 e este documento. Se o código atual contradisser este documento, **pare e pergunte**.

---

## 1. Escopo

**Entra:**
1. O miolo do `/r` (estimar, gravar e montar a resposta) vira a função `processar_refeicao`, que o botão da T6 vai reaproveitar.
2. O "digitando…" é mandado antes de cada tentativa do Gemini, pelo `antes_de_tentar` que a T3 criou.
3. O `andamento.md` passa para "em andamento, T4".

**Fica fora:**
- **T5:** textos novos (`TEXTO_TENTANDO_DE_NOVO`, `TEXTO_PEDIDO_EXPIRADO`, `TEXTO_SO_O_DONO`), pendentes (`guardar_pendente`, `retirar_pendente`, `VALIDADE_PENDENTE`), `teclado_tentar` e o botão na falha.
- **T6:** `botao_tentar`, `CallbackQueryHandler` no `main.py`, ajustes no `tratar_erro` e no `filtrar_chats`.
- **T7:** comentários de decisões substituídas e ajustes de docs.
- **Não muda:** `app/gemini.py`, `app/main.py`, prompt, banco, migrações, `.env.example`, textos do bot e `requirements.txt`.

O comportamento visível do `/r` continua igual, a não ser pelo "digitando…". Na falha do Gemini, a resposta continua o `TEXTO_FALHA_GEMINI` atual, **sem botão**.

## 2. Regras e decisões cobertas

| Ref. | Como a T4 atende |
|---|---|
| RN-001 / RN-007 | Data e hora da refeição vêm do `momento` (o `message.date` do `/r`), convertido por `data_hora_sao_paulo`. O relógio só escolhe o texto "hoje" / "total de DD/MM". |
| RN-002 | O filtro de chats continua antes de tudo: chat não autorizado não recebe "digitando…". |
| RN-013 / RN-016 | Fluxo de estimativa e gravação igual ao de hoje. |
| RN-017 / P3 | "digitando…" antes de cada tentativa (até 3 por `/r`). Se falhar, só vai para o log. |
| P8 | O `momento` entra por parâmetro, para o clique da T6 gravar com a data do `/r` original. |
| D-047 | A fila de updates continua; o fluxo fica numa função só, sem depender da fila. |

## 3. Decisões tomadas nesta rodada

Respostas do usuário em 16/11/2026, com o parecer do revisor:

1. **Retorno:** `processar_refeicao` devolve `str` (e não `str | None`). Todos os caminhos devolvem texto; a falha é exceção.
2. **"digitando…" sem renovação:** sai **só antes de cada tentativa**, como manda a P3. O Telegram apaga o aviso depois de uns 5 s, então numa tentativa longa (até 15 s) ele some antes da resposta. Não criar tarefa de fundo para renovar. Se isso incomodar no teste, vira decisão nova.
3. **`salvar_usuario`:** fica no `comando_r`, **fora** de `processar_refeicao`. A T6 **não** chama de novo: se existe pendente, o usuário já foi salvo. No clique, usar `usuario_id` e `nome` **do pendente**, não do `effective_user`.
4. **`conftest.py`:** mudanças aprovadas, com os dois ajustes do revisor (seção 5).
5. **`andamento.md`:** passa para "em andamento, T4", com data de 16/11/2026.

## 4. Código — `app/handlers.py`

### 4.1 Import

```python
from telegram.constants import ChatAction
```

### 4.2 Função nova `processar_refeicao`

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
1. Define um `avisar()` interno, assíncrono, que faz `await context.bot.send_chat_action(chat_id, ChatAction.TYPING)`. **Conferir o `await`**: sem ele, o teste de ordem dos eventos falha (é ele que pega esse erro).
2. Chama `gemini.estimar(context.bot_data["gemini"], context.bot_data["gemini_modelo"], texto_limpo, antes_de_tentar=avisar)`. O limite de 2 s e o tratamento de erro do aviso já estão no `_avisar` da T3; não repetir aqui.
3. Sem itens: devolve `TEXTO_R_NENHUM_ALIMENTO` e não grava nada.
4. Com itens, segue como o `comando_r` faz hoje:
   - `data_hora_sao_paulo(momento)` para data e hora (RN-007);
   - `db.salvar_alimentos`, `calcular_itens`, `db.registrar_refeicao` (refeição e itens numa transação só, como hoje);
   - `resposta_refeicao(..., hoje=datetime.now(FUSO).date(), ...)` e devolve o texto.
5. **Não trata erros:** `FalhaGemini` sobe para quem chamou; erro de banco sobe para o `tratar_erro`.
6. **Não chama** `salvar_usuario` (seção 3, item 3).
7. Não toca em pendentes (P10 continua livre para a T6).

Nenhum SQL novo: usa as funções de `app/db.py` que já existem.

### 4.3 `comando_r` depois da mudança

1. `salvar_usuario` continua **antes** das validações. Há teste que exige que banco fora do ar não gaste a chamada ao Gemini.
2. `extrair_descricao` e `limpar_descricao`; validações de vazio (`TEXTO_R_SEM_DESCRICAO`) e de tamanho (`TEXTO_R_MUITO_LONGO`).
3. `texto = await processar_refeicao(context, chat.id, usuario.id, nome, descricao, texto_limpo, mensagem.date)` dentro de `try`.
4. `except gemini.FalhaGemini`: responde `TEXTO_FALHA_GEMINI` (o atual) e encerra.
5. Sucesso ou "nenhum alimento": `reply_text(texto)`.

## 5. Testes

Rodar com `docker compose run --rm bot pytest`. Os testes atuais do `/r` continuam passando **sem mudar o que verificam**; só as fixtures mudam.

### 5.1 `tests/conftest.py`

- **`RequisicaoFalsa`:**
  - nova lista `eventos`, com uma entrada por chamada, na ordem: `("acao", chat_id, action)` para `sendChatAction` e `("mensagem", texto)` para envios;
  - nova opção `falhar_acoes`: quando ligada, o `sendChatAction` devolve status 400 com `{"ok": false, "description": "..."}`, e o PTB lança `BadRequest`;
  - a lista `enviadas` continua igual.
- **`bot_teste`:** passa a expor a requisição (para ler `eventos` e ligar `falhar_acoes`).
- **`gemini_falso`:**
  - aceita `antes_de_tentar=None`. Isso é **obrigatório**: com a assinatura atual `(cliente, modelo, texto)`, todos os testes do `/r` quebram com `TypeError` assim que o handler passar `antes_de_tentar=`;
  - chama `await antes_de_tentar()` uma vez, **sem** tratar erro;
  - depois registra `("gemini", texto)` **na mesma lista `eventos` da requisição** (ajuste 🟡 do revisor), para os testes provarem a ordem. Para isso, a fixture precisa ter acesso à requisição (por exemplo, dependendo de `bot_teste`).

### 5.2 Testes novos em `tests/test_refeicao.py`

| Teste | O que verifica |
|---|---|
| `test_r_manda_digitando_no_chat_certo_antes_do_gemini` | `eventos` é `[("acao", CHAT_AUTORIZADO, "typing"), ("gemini", ...), ("mensagem", ...)]`. |
| `test_r_vazio_e_longo_nao_mandam_digitando` (parametrizado) | Nenhum evento `"acao"`. |
| `test_falha_no_digitando_nao_impede_o_registro` | Usa o **`estimar` real**, com `gemini._chamar_uma_vez` trocado por uma função que devolve resposta válida; `falhar_acoes=True`. A refeição é gravada, a resposta é a de sucesso e o `caplog` tem "Aviso antes da tentativa falhou". |
| `test_digitando_em_cada_tentativa` | `estimar` real; `_chamar_uma_vez` lança `errors.ServerError(503, {})` uma vez e depois responde. Dois eventos `typing` e o registro feito. |
| `test_processar_refeicao_usa_o_momento_recebido` | Chamada direta com `context` montado a partir do `bot_teste.app`. `momento` = segunda 02:30 UTC grava como domingo 23:30 em São Paulo (RN-001/RN-007), e a resposta diz "total de DD/MM". |
| `test_processar_refeicao_deixa_falha_gemini_subir` | `gemini_falso.erro = FalhaGemini()`: a função lança `FalhaGemini` e nada é gravado. |
| `test_processar_refeicao_sem_alimento_devolve_o_texto` | Devolve `TEXTO_R_NENHUM_ALIMENTO` e não grava. |

**Espera falsa (ajuste 🟡 do revisor):** em `test_digitando_em_cada_tentativa`, zerar a espera com `monkeypatch.setattr(gemini, "ESPERAS_SEGUNDOS", (0, 0))`, ou envolver o `estimar` real passando `dormir=` falso. **Nunca** trocar `asyncio.sleep` no módulo `asyncio`: o padrão `dormir=asyncio.sleep` do `estimar` é fixado na definição (a troca não teria efeito) e a troca afetaria o PTB e o próprio asyncio.

**Trocar `_chamar_uma_vez`:** com `monkeypatch.setattr(gemini, "_chamar_uma_vez", ...)`, como em `tests/test_gemini.py`. Funciona porque o `estimar` busca a função pelo nome a cada tentativa.

### 5.3 Ajustes em testes existentes

- **`/r` em chat não autorizado:** conferir também que não houve evento `"acao"` (RN-002 barra antes do "digitando…").
- **Falha do Gemini** e **"nenhum alimento":** conferir que o "digitando…" sai antes da resposta.

## 6. Docs

- **`Docs/andamento.md`:** linha 5 → "4 — Resiliência do Gemini (em andamento, T4)"; "Última atualização" → 16/11/2026. As pendências herdadas continuam até a T7.
- Nenhum outro doc muda nesta task.

## 7. Pronto quando

- [ ] `processar_refeicao` existe com a assinatura da seção 4.2 e o `comando_r` a usa.
- [ ] `docker compose run --rm bot pytest` passa: os 356 de antes mais os novos, resultado real informado.
- [ ] Nenhuma mudança em `app/gemini.py`, `app/main.py`, banco, migrações ou textos.
- [ ] `andamento.md` atualizado.
- [ ] Resumo ao usuário no formato de sempre (arquivos, regras, testes, como testar, pendências).
- [ ] Nenhum commit (o usuário faz).

## 8. Como testar no Telegram

1. `docker compose restart bot` e `docker compose logs -f bot`.
2. `/r 150 g de arroz e 2 ovos`: aparece "KALLY está digitando…" e logo a resposta com o total. O log mostra a tentativa 1/3.
3. `/r` vazio e `/r` com mais de 500 caracteres: os textos de sempre, sem "digitando…".
4. `/r kkkkk`: "Não identifiquei nenhum alimento…".
5. `/peso` e `/id`: iguais a antes.
6. **Opcional — Gemini fora do ar** (bloqueio do `/etc/hosts` da seção 3 do plano da etapa 4):
   - `/r 1 banana` mostra "digitando…" a cada tentativa, e o log mostra as 3 tentativas com as esperas;
   - a resposta é o texto atual de falha, **ainda sem botão** (vem na T5);
   - desbloquear o Gemini no fim.
7. Conferir no banco que o registro do passo 2 tem a data e a hora do envio:
   ```bash
   docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT id, data, hora, descricao, kcal FROM refeicoes ORDER BY id DESC LIMIT 3"'
   ```

## 9. Pontos em aberto

- **Queda do bot depois de recriar o `db`** (vista na T1): o bot só voltou com `docker compose restart bot`. O usuário ainda não decidiu se entra em "Pendências herdadas" do `andamento.md`. **Não registrar sem confirmação.**
