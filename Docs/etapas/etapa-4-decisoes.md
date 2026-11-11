# Etapa 4: decisões para a resiliência do Gemini

**Status:** decisões e premissas confirmadas pelo usuário em 10/11/2026 · **Plano:** [etapa-4-resiliencia-gemini.md](etapa-4-resiliencia-gemini.md) · **Data:** 10/11/2026

Base para os agentes `kally-python` e `kally-revisor`. Este documento não substitui `regras-de-negocio.md`, `exemplos.md` nem `decisoes.md`; a RN-017 já reflete tudo o que está aqui (D-045, D-047, D-048).

---

## 1. Decisões do usuário

| # | Decisão | Registro |
|---|---|---|
| D1 | A etapa 4 antiga (base de alimentos com `parser.py` e `alimentos.py`) **sai do roteiro**. O Gemini sempre separa a descrição e converte qualquer medida, inclusive as caseiras, em gramas; a base fornece os valores por 100 g pelo nome e aprende os alimentos novos. | D-041 (substitui D-026) |
| D2 | Sem cache de resposta por linha e sem os nomes da base no prompt. | D-042 |
| D3 | O nome do alimento é o que o Gemini devolve. **O prompt não muda.** Correções de grafia que o Gemini fizer mesmo assim são aceitas; o risco D10 da etapa 3 vira permanente. | D-043 (substitui D-034) |
| D4 | A porção padrão continua sendo pedida, validada e gravada, só como referência. | D-044 |
| D5 | **Nova etapa 4: resiliência do Gemini** = nova tentativa automática + botão "🔄 Tentar de novo" na mensagem de falha. Sem modelo reserva. | D-045 (substitui D-023) |
| D6 | Novo roteiro: 4. Resiliência do Gemini · 5. `/dia` · 6. Botões · 7. `/retro` · 8. `/semana` · 9. `/exportar` · 10. Deploy. | D-046 |
| D7 | **Updates continuam em fila** (um por vez). Sem `block=False`, sem `concurrent_updates`, sem trava no banco. Chamadas paralelas ficam para o futuro, e o código não deve dificultá-las. | D-047 |

**Motivo de D5:** em 10/11/2026, cerca de 6 de 12 chamadas falharam (5 `ServerError` e 1 `TimeoutError`), e uma nova tentativa segundos depois funcionou.

## 2. Premissas confirmadas (10/11/2026)

| # | Assunto | Decisão |
|---|---|---|
| P1 | Quais erros repetem sozinhos | Só os passageiros: `ServerError` (5xx, inclusive 503), `ClientError` com código 429, `TimeoutError` e falha de conexão (`httpx.TransportError` e subclasses). **Não** repetem: outros 4xx (configuração), resposta fora do schema e item inválido. |
| P2 | Tentativas e tempos | Até **3 tentativas**; esperas de **2 s** e **5 s**; **15 s** por tentativa; **40 s** de orçamento total. Cada tentativa usa o menor entre 15 s e o que sobra do orçamento; com menos de 5 s sobrando, não começa outra. (A resposta bem-sucedida mais lenta nos logs levou 9,5 s.) |
| P3 | Aviso enquanto tenta | "digitando…" (`send_chat_action`) antes de cada tentativa. Falha ao mandar a ação só vai para o log. |
| P4 | Concorrência | **Fila mantida** (D-047). Não usar `block=False` nem trava no banco. |
| P5 | Mensagem de falha e botão | `Não consegui estimar agora. Nada foi registrado.` + `[🔄 Tentar de novo]`. O botão aparece em **toda** falha do Gemini (passageira esgotada, fora do schema, item inválido) e em nenhum outro erro. |
| P6 | Pedido pendente | Em memória, `bot_data["pendentes"]`, chave `(chat_id, message_id do /r original)`, `callback_data` = `tentar:<message_id>`. Guarda: `telegram_id` e nome do dono, `descricao` original, texto limpo e `message.date` do `/r`. Reiniciar o bot perde os pendentes. |
| P7 | Expiração | 7 dias desde o envio do `/r`, conferido no clique. Vencidos são limpos quando um novo pendente é guardado. Expirado ou perdido: aviso no clique `Esse pedido expirou. Mande o /r de novo.` e o botão sai da mensagem. |
| P8 | Data da refeição | O `message.date` do `/r` original. "total hoje" ou "total de 09/11" compara com a data do clique, como hoje. |
| P9 | Quem pode apertar | Só o dono. Outra pessoa recebe o aviso `Só João pode tentar de novo.`, sem mensagem nova. O `filtrar_chats` já cobre o clique (`effective_chat`); falta o teste. |
| P10 | Duplo clique | O pendente é retirado (`pop`) antes de qualquer `await`; a mensagem vira `Tentando de novo…` sem botão. Caso aceito: reenviar o `/r` e depois apertar o botão antigo registra duas vezes. |
| P11 | Resultado do clique | **Sucesso:** a mensagem de falha é editada e vira a resposta do registro. **Falhou de novo:** o pendente volta e a mensagem volta ao texto de falha com o botão. **Nenhum alimento:** edita para esse texto, sem botão. **Banco fora do ar ou erro inesperado:** resposta de sempre, e o pendente **não** volta. |
| P12 | Prompt | **Não muda** (D-043). |
| P13 | Pendências herdadas | Entram as três: `-h 127.0.0.1` no healthcheck do `db`; RN-012 alinhada ao código (`dom 01/11`); comando do `psql` no plano da etapa 2 igual ao do README. |

**Efeito da fila (P4) sobre o duplo clique (P10):** os cliques ficam em fila. Um segundo clique só é processado depois que o primeiro termina: se o primeiro deu certo, o pendente não existe mais e o segundo recebe o aviso de expirado; se falhou, o pendente voltou e o segundo clique é uma nova tentativa legítima.

## 3. Escopo

**Entra:**
- nova tentativa automática nas falhas passageiras (P1, P2), com "digitando…" (P3);
- botão "🔄 Tentar de novo" na falha do Gemini, com o pedido pendente em memória (P5 a P11);
- pendências herdadas (P13);
- testes;
- docs da seção 6.

**Fica de fora:**
- paralelismo (`block=False`, `concurrent_updates`, trava no banco) (D-047);
- mudança no prompt (D-043);
- modelo reserva (D-045);
- `parser.py` e `alimentos.py` (D-041);
- botões de corrigir e apagar, e o `message_id` em `refeicoes` (etapa 6);
- migração nova e mudanças no `.env.example`: os tempos ficam como constantes no código.

## 4. Direção técnica

| Arquivo | Mudança |
|---|---|
| `app/gemini.py` | Classificação dos erros (P1) e laço de tentativas com os tempos de P2. O cliente continua com `HttpRetryOptions(attempts=1)`: as novas tentativas são do código, para o orçamento valer. Relógio e espera injetáveis para os testes. |
| `app/handlers.py` | O miolo do `/r` (estimar, gravar, montar a resposta) vira uma função usada pelo `/r` e pelo botão. Pendentes em memória, botão na falha e o handler do clique. |
| `app/main.py` | `CallbackQueryHandler(handlers.botao_tentar, pattern=r"^tentar:")`. Sem `block=False`. |
| `docker-compose.yml` | `-h 127.0.0.1` no healthcheck (P13). |
| `tests/` | Classificação, tempos com relógio falso, pendentes (dono, expiração, duplo clique), clique pelo filtro de chats, fluxo do botão. |

**Pontos de atenção:**
- As esperas usam `asyncio.sleep`, nunca `time.sleep`; o orçamento é medido com `time.monotonic()`.
- O clique usa o mesmo fluxo do `/r`, inclusive as novas tentativas. Mais tarde, `/retro` (etapa 7) e a correção pela descrição (etapa 6) usam a mesma função, sem código novo de resiliência.
- `callback_data` com prefixo de ação (`tentar:`): os botões da etapa 6 entram com outros prefixos, sem mexer no handler desta etapa.
- `tratar_erro` responde à `effective_message`, que no clique é a mensagem do bot. Conferir se fica legível.
- Log por tentativa, sem o texto da pessoa nem a chave: `Gemini tentativa 2/3 falhou em 0,8 s: ServerError`.
- Custo: no pior caso, 3 chamadas por `/r` e 3 por clique. Aceitável no nível gratuito.
- Paralelismo futuro (D-047): manter o fluxo numa função só, retirar o pendente antes de qualquer `await` e a gravação numa transação só.

## 5. Critérios de aceite

1. Falha passageira seguida de sucesso registra normalmente, com teste.
2. Resposta fora do schema, item inválido e 4xx diferente de 429 não são repetidos.
3. Nenhum `/r` passa de 40 s de tentativas, com teste de relógio falso.
4. Esgotadas as tentativas, nada é gravado e a resposta traz o texto e o botão de P5.
5. O botão não aparece em banco fora do ar, descrição vazia, longa ou "nenhum alimento".
6. O clique registra com a data do `/r` original, inclusive em outro dia.
7. Só o dono usa o botão; outra pessoa recebe o aviso de P9, sem mensagem nova.
8. Duplo clique registra uma vez só.
9. Pedido perdido no reinício ou com mais de 7 dias responde o texto de expirado e tira o botão.
10. Clique em chat não autorizado é ignorado e não chama o Gemini.
11. `/peso`, `/id` e o `/r` sem falha continuam iguais.
12. Pendências herdadas resolvidas e removidas do `andamento.md`.
13. Todos os testes passam com `docker compose run --rm bot pytest`.

## 6. Docs a ajustar na etapa

| Documento | Mudança |
|---|---|
| `regras-de-negocio.md` | RN-012 (`dom 01/11`) |
| `exemplos.md` | Seção "O Gemini falha": tirar o texto da etapa 3 e a nota, deixando só os exemplos da etapa 4 |
| `bot-dieta-planejamento.md` | Seção 8 (Gemini) com os tempos finais |
| `etapa-2-banco-docker-peso.md` | Comando do `psql` igual ao do README (P13) |
| `.claude/agents/kally-revisor.md` | Linhas sobre "sem nova tentativa" (RN-017) e nome do alimento (D-043) |
| `andamento.md` | Início: 🔧 e link do plano. Aprovação: ✅, "O que funciona hoje", pendências removidas |
| `README.md` | Roadmap na aprovação |

Comentários no código que citam decisões substituídas (`gemini.py`: D-023 em `criar_cliente` e "a etapa 4 passa só o que a base não conhece" em `estimar`; `handlers.py`: D-034 em `alimentos_para_salvar`) são ajustados junto com o código.
