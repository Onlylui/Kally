# Etapa 4 — Resiliência do Gemini

Plano de implementação da etapa 4, dividido em **tasks pequenas e sequenciais**. Escrito para o `kally-python` (implementa uma task por vez), o `kally-revisor` (revisa) e o usuário (acompanha e testa).

**Status:** ⏳ pronto para implementar · **Etapa anterior:** 3 (concluída) · **Fonte principal:** [etapa-4-decisoes.md](etapa-4-decisoes.md) (D1 a D7, P1 a P13). Este plano não repete o que está lá; em caso de dúvida, vale o doc de decisões e a RN-017.

---

## 1. Objetivo

Ao fim da etapa:
- falhas passageiras do Gemini (5xx, 429, tempo esgotado, conexão) são repetidas sozinhas, até 3 vezes e no máximo 40 s, com "digitando…";
- se ainda assim falhar, a mensagem de falha traz o botão **🔄 Tentar de novo**, que repete o pedido sem reenviar o texto, só para quem mandou o `/r`, com a data do `/r` original;
- as três pendências herdadas da etapa 2 estão resolvidas.

**Continua igual:** a fila de updates (D-047), o prompt (D-043), o banco (nenhuma migração), o `.env.example`.

## 2. Como trabalhar com este plano

- **Uma task por vez**, na ordem. Cada task termina com os testes passando (`docker compose run --rm bot pytest`) e um resumo curto ao usuário. O usuário pode fazer commit entre as tasks.
- Antes de cada task, ler: a task inteira, os documentos que ela cita e o código que ela altera. **Não** adiantar trabalho de tasks seguintes.
- Regras de sempre: nunca ler o `.env`, nunca fazer commit, tudo em Docker, testes sem Gemini nem Telegram reais, textos iguais ao `exemplos.md`.
- **Paralelismo futuro (D-047):** não usar `block=False` nem `concurrent_updates`, mas também não escrever código que dependa da fila para estar certo (ex.: retirar o pendente antes de qualquer `await`).
- Se algo no código contradisser o plano, **pare e pergunte**.

| # | Task | Arquivos principais | Depende de |
|---|---|---|---|
| T1 | Pendências herdadas | `docker-compose.yml`, docs | — |
| T2 | Classificar falhas passageiras | `app/gemini.py`, `tests/test_gemini.py` | — |
| T3 | Laço de tentativas com orçamento | `app/gemini.py`, `tests/test_gemini.py` | T2 |
| T4 | Extrair o fluxo do `/r` + "digitando…" | `app/handlers.py`, testes | T3 |
| T5 | Pendentes em memória + botão na falha | `app/handlers.py`, testes | T4 |
| T6 | Handler do clique no botão | `app/handlers.py`, `app/main.py`, testes | T5 |
| T7 | Docs, comentários e fechamento | docs, comentários | T6 |

---

## T1 — Pendências herdadas

**Objetivo:** fechar as três ressalvas da etapa 2 (P13). Task de aquecimento, sem código Python.

**Ler:** `Docs/andamento.md` (Pendências herdadas), `docker-compose.yml`, RN-012 em `Docs/regras-de-negocio.md`, `handlers.formatar_dia_semana` e `resposta_peso_registrado`, `Docs/exemplos.md` (seção do `/peso`), seções 6 e 7 de `Docs/etapas/etapa-2-banco-docker-peso.md`, README (linha do `psql`).

**Fazer:**
1. `docker-compose.yml`: healthcheck do `db` com `pg_isready -h 127.0.0.1 -U $${POSTGRES_USER} -d $${POSTGRES_DB}`, mantendo o comentário sobre o `$$`.
2. RN-012: o exemplo passa a usar o formato do código e do `exemplos.md` (`dom 01/11`). Conferir no código o formato exato antes de escrever.
3. Plano da etapa 2, seções 6 e 7: o comando do `psql` igual ao do README (`docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'`).
4. `andamento.md`: etapa 4 em 🔧 com link para este plano (só se ainda não estiver).

**Pronto quando:** `docker compose up -d` sobe o `db` como `healthy`; os três itens batem; testes passando. As linhas das pendências só saem do `andamento.md` na T7.

---

## T2 — Classificar falhas passageiras

**Objetivo:** uma função pura que diz se um erro da chamada ao Gemini merece nova tentativa (P1).

**Ler:** P1 do doc de decisões; `app/gemini.py` (`estimar`, `criar_cliente`); `tests/test_gemini.py` (`criar_cliente_falso`, `ServidorFalso`); a hierarquia de erros do `google-genai` instalado (`google.genai.errors`: `APIError`, `ClientError`, `ServerError`, atributo `code`) — **conferir no pacote dentro do container**, não de memória.

**Fazer:**
1. `eh_falha_passageira(erro: BaseException) -> bool` em `app/gemini.py`:
   - `True`: `errors.ServerError` (qualquer 5xx); `errors.ClientError` com `code == 429`; `TimeoutError`; `httpx.TransportError` e subclasses (conexão recusada, leitura interrompida etc.).
   - `False`: qualquer outra coisa, inclusive outros 4xx (400, 401, 403, 404).
2. Não mudar o comportamento de `estimar` ainda.

**Testes:** parametrizado com um caso por tipo: 500, 503, 429 → `True`; 400, 403, 404, `ValueError` → `False`; `TimeoutError` e `httpx.ConnectError` → `True`. Criar as exceções do SDK do jeito que o pacote instalado aceita (conferir o construtor).

**Pronto quando:** testes novos e antigos passando.

---

## T3 — Laço de tentativas com orçamento

**Objetivo:** `estimar` passa a tentar até 3 vezes nas falhas passageiras, dentro de 40 s (P2), e avisa o chamador antes de cada tentativa (para o "digitando…" da T4).

**Ler:** P1, P2 e P3; `estimar` atual; testes `test_timeout_total` e `test_erro_da_chamada_vira_falha`.

**Fazer:**
1. Constantes no topo de `app/gemini.py`: `TENTATIVAS = 3`, `ESPERAS_SEGUNDOS = (2, 5)`, `TIMEOUT_SEGUNDOS = 15`, `ORCAMENTO_SEGUNDOS = 40`, `MINIMO_PARA_TENTAR_SEGUNDOS = 5`.
2. Separar a chamada única atual numa função interna (ex.: `_chamar_uma_vez(cliente, modelo, texto, limite)`), que continua validando schema e itens e lançando `FalhaGemini`.
3. `estimar(cliente, modelo, texto, antes_de_tentar=None, relogio=time.monotonic, dormir=asyncio.sleep)`:
   - `antes_de_tentar`: função assíncrona opcional, chamada antes de cada tentativa. Se ela lançar exceção, registra no log e segue (o "digitando…" nunca derruba o `/r`).
   - Cada tentativa usa `min(TIMEOUT_SEGUNDOS, orçamento restante)`.
   - Falha passageira (T2) com tentativas e orçamento sobrando: espera `ESPERAS_SEGUNDOS[i]` e tenta de novo. Se depois da espera sobrarem menos de `MINIMO_PARA_TENTAR_SEGUNDOS`, desiste.
   - Falha não passageira, resposta fora do schema ou item inválido: `FalhaGemini` na hora, sem repetir.
   - Lista vazia de itens continua **não** sendo falha.
   - `relogio` e `dormir` existem só para os testes.
4. Log por tentativa, sem o texto da pessoa: `Gemini tentativa 2/3 falhou em 0,8 s: ServerError` e, no sucesso, a linha atual com o número da tentativa.
5. `FalhaGemini` continua sendo a única exceção que sai de `estimar`.

**Testes** (relógio e espera falsos, sem dormir de verdade):
- 503 e depois sucesso → devolve a resposta, 2 chamadas, esperou 2 s;
- 503, 503, sucesso → 3 chamadas, esperou 2 s e 5 s;
- 503 três vezes → `FalhaGemini`, 3 chamadas;
- 404 → `FalhaGemini` com 1 chamada só; idem resposta fora do schema e item inválido;
- orçamento: tempo esgotado de 15 s duas vezes → a terceira não começa (sobrariam menos de 5 s) → `FalhaGemini` com 2 chamadas;
- a última tentativa recebe um limite menor que 15 s quando o orçamento está no fim;
- `antes_de_tentar` é chamada uma vez por tentativa; se ela lançar exceção, a estimativa segue;
- os testes antigos de `estimar` continuam passando (ajustar só o necessário).

**Pronto quando:** testes passando; `handlers.py` sem mudança (a assinatura nova é compatível).

---

## T4 — Extrair o fluxo do `/r` e o "digitando…"

**Objetivo:** preparar o terreno para o botão sem mudar o comportamento: o miolo do `/r` vira uma função reutilizável, e o "digitando…" entra (P3).

**Ler:** `comando_r` inteiro; `tests/test_refeicao.py` (fixtures `bot_teste`, `gemini_falso`, `banco_falso`); RN-007; P3 e P8.

**Fazer:**
1. Criar `processar_refeicao(context, chat_id, usuario_id, nome, descricao, texto_limpo, momento) -> str | None` (o nome pode ser outro, desde que claro):
   - chama `gemini.estimar` com `antes_de_tentar` que manda `ChatAction.TYPING` para o `chat_id`;
   - nenhum alimento → devolve o texto de "nenhum alimento";
   - sucesso → grava (como hoje) e devolve o texto da resposta;
   - `FalhaGemini` **sobe** para quem chamou (o `/r` e, na T6, o botão decidem o que fazer);
   - erro de banco sobe, como hoje, para o `tratar_erro`.
   - `momento` é o `message.date` do `/r` original (RN-007). A data e a hora saem dele, nunca do relógio.
2. `comando_r` fica: usuário, extrair e limpar, validações de vazio e tamanho, `processar_refeicao`, responder. Na `FalhaGemini`, continua respondendo `TEXTO_FALHA_GEMINI` (o botão é a T5).
3. Nada de pendentes, botão ou `main.py` nesta task.

**Testes:** todos os testes atuais do `/r` passam sem mudar o que verificam. Novo: o "digitando…" é enviado ao chat certo antes da chamada; falha ao mandar o "digitando…" não impede o registro.

**Pronto quando:** testes passando e o `/r` se comporta igual no Telegram, agora com "digitando…".

---

## T5 — Pendentes em memória e botão na falha

**Objetivo:** quando o Gemini falha, guardar o pedido e mandar a mensagem nova com o botão (P5, P6, P7).

**Ler:** P5, P6, P7, P10; `Docs/exemplos.md`, seção "O Gemini falha" (textos da etapa 4); RN-017.

**Fazer:**
1. Textos novos em `handlers.py`, iguais ao `exemplos.md`:
   - `TEXTO_FALHA_GEMINI = "Não consegui estimar agora. Nada foi registrado."` (substitui o atual);
   - `TEXTO_TENTANDO_DE_NOVO = "Tentando de novo…"`;
   - `TEXTO_PEDIDO_EXPIRADO = "Esse pedido expirou. Mande o /r de novo."`;
   - `TEXTO_SO_O_DONO = "Só {nome} pode tentar de novo."`;
   - rótulo do botão `🔄 Tentar de novo`.
2. Funções puras para os pendentes, que recebem o dicionário (`bot_data["pendentes"]`, criado com `setdefault`):
   - `guardar_pendente(pendentes, chat_id, message_id, dono_id, nome, descricao, texto_limpo, momento)`: guarda e, antes, remove os vencidos;
   - `retirar_pendente(pendentes, chat_id, message_id, agora) -> dict | None`: faz `pop`; devolve `None` se não existe ou se passou de 7 dias desde `momento` (P7);
   - `devolver_pendente(...)` ou reaproveitar `guardar_pendente` para a falha no clique (P11).
   - Constante `VALIDADE_PENDENTE = timedelta(days=7)`.
3. `teclado_tentar(message_id)`: `InlineKeyboardMarkup` com um botão, `callback_data = f"tentar:{message_id}"` (P6). Conferir que cabe nos 64 bytes.
4. Em `comando_r`, na `FalhaGemini`: guardar o pendente com a chave `(chat_id, message_id do /r)` e responder `TEXTO_FALHA_GEMINI` com o teclado.
5. O botão **não** aparece em: banco fora do ar, erro inesperado, vazio, longo, nenhum alimento (P5).

**Testes:**
- falha do Gemini → resposta com o texto novo e o botão `tentar:<id>`; pendente guardado com os campos de P6, inclusive o `message.date` original;
- vazio, longo, nenhum alimento, banco fora → sem botão e sem pendente;
- `retirar_pendente`: devolve e remove; segunda chamada devolve `None`; com 7 dias e 1 segundo devolve `None`; com exatamente 7 dias, decidir e documentar no teste (sugestão: ainda vale);
- `guardar_pendente` limpa os vencidos.

**Pronto quando:** testes passando. O botão aparece no Telegram, mas apertá-lo ainda não faz nada (T6).

---

## T6 — Handler do clique no botão

**Objetivo:** o clique repete o pedido, com todas as regras de P8 a P11.

**Ler:** P8 a P11; `filtrar_chats` e `deve_processar`; `tratar_erro`; `registrar_handlers` em `app/main.py`; a documentação do `CallbackQueryHandler` e do `CallbackQuery.answer`/`edit_message_text` na versão instalada do `python-telegram-bot`.

**Fazer:**
1. `botao_tentar(update, context)` em `handlers.py`, nesta ordem:
   1. Lê o `message_id` do `callback_data`. Formato inválido → `answer()` e encerra.
   2. Confere o dono **antes** de retirar o pendente: se o pendente existe e quem clicou não é o dono → `answer(TEXTO_SO_O_DONO, show_alert=False)` e encerra, sem mexer no pendente (P9).
   3. `retirar_pendente` (antes de qualquer outro `await`). Não existe ou expirou → `answer(TEXTO_PEDIDO_EXPIRADO)`, tira o botão da mensagem e encerra (P7).
   4. `answer()` e edita a mensagem para `TEXTO_TENTANDO_DE_NOVO`, sem botão (P10).
   5. `processar_refeicao` com os dados do pendente, inclusive o `momento` original (P8).
   6. Resultado (P11):
      - sucesso ou nenhum alimento → edita a mensagem para o texto devolvido, sem botão;
      - `FalhaGemini` → devolve o pendente e edita para `TEXTO_FALHA_GEMINI` com o botão;
      - erro de banco ou inesperado → **não** devolve o pendente; deixa subir para o `tratar_erro`.
2. `app/main.py`: `CallbackQueryHandler(handlers.botao_tentar, pattern=r"^tentar:")`. **Sem** `block=False` (D-047).
3. `tratar_erro`: conferir que, num clique, a resposta de banco fora do ar sai legível (ela responde à mensagem do bot). Se precisar, ajustar o mínimo.
4. `filtrar_chats`: conferir que um clique em chat não autorizado é barrado antes do `botao_tentar` (P9). Só mudar se o teste mostrar que não é.

**Testes:**
- clique do dono com sucesso → mensagem editada para a resposta do registro; gravou com a data do `/r` original, inclusive quando o clique é no dia seguinte (resposta com `total de 31/10`);
- clique de outra pessoa → aviso de P9, pendente intacto, Gemini não chamado;
- clique sem pendente (reinício) e com pendente vencido → aviso de expirado, botão removido;
- duplo clique → o segundo encontra o pendente já retirado (sucesso) ou devolvido (falha), conforme P10;
- clique com nova falha → pendente devolvido, mensagem volta com o botão;
- clique com banco fora → pendente não devolvido;
- clique em chat não autorizado → nada acontece, Gemini não chamado;
- `callback_data` malformado → só `answer()`.

**Pronto quando:** testes passando e o fluxo completo funciona no Telegram (seção 3, passos 4 a 9).

---

## T7 — Docs, comentários e fechamento

**Objetivo:** deixar docs e comentários batendo com o código, e preparar a revisão.

**Fazer:**
1. Seção 6 do doc de decisões, item por item: `exemplos.md` (seção "O Gemini falha" só com os exemplos da etapa 4, sem a nota), `bot-dieta-planejamento.md` seção 8 com os tempos finais, `.claude/agents/kally-revisor.md` (RN-017 e D-043).
2. Comentários no código que citam decisões substituídas: D-023 em `criar_cliente`, "a etapa 4 passa só o que a base não conhece" em `estimar`, D-034 em `alimentos_para_salvar`.
3. `andamento.md`: remover as três pendências herdadas resolvidas. **Não** marcar a etapa como ✅: isso só depois do teste e da aprovação do usuário.
4. Rodar a suíte inteira e informar o resultado real.
5. Responder ao usuário no formato de "Ao terminar" do `kally-python`.

Depois da T7: `kally-revisor` revisa a etapa inteira contra o doc de decisões, a RN-017 e este plano.

---

## 3. Como o usuário testa no Telegram

1. `docker compose up -d --build` e `docker compose logs -f bot`. O `db` aparece como `healthy` em `docker compose ps`.
2. `/r 150 g de arroz e 2 ovos`: aparece "digitando…" e o registro sai normal.
3. `/peso 82,4`, `/id` e `/r` sem descrição: iguais a antes.
4. **Simular o Gemini fora do ar** (bloqueia só o Gemini dentro do container; o Telegram continua funcionando):
   ```bash
   docker compose exec -u root bot sh -c 'echo "127.0.0.1 generativelanguage.googleapis.com" >> /etc/hosts'
   ```
5. `/r 1 banana`: o log mostra 3 tentativas com falha de conexão e esperas de 2 s e 5 s; a resposta é `Não consegui estimar agora. Nada foi registrado.` com o botão. Nada foi gravado.
6. Com o Gemini ainda bloqueado, aperte o botão: a mensagem vira `Tentando de novo…` e volta à falha com o botão.
7. **Desbloquear o Gemini:**
   ```bash
   docker compose exec -u root bot sh -c 'grep -v generativelanguage /etc/hosts > /tmp/hosts && cat /tmp/hosts > /etc/hosts'
   ```
8. Aperte o botão de novo: a mesma mensagem vira a resposta do registro, com o total certo.
9. A outra pessoa aperta um botão de falha seu: aparece o aviso "Só <nome> pode tentar de novo." só para ela, sem mensagem nova.
10. Deixe um botão de falha sem apertar, rode `docker compose restart bot` e aperte: aviso de pedido expirado e o botão some.
11. No banco, confira que a refeição do passo 8 está com a data e a hora do `/r` original:
    ```bash
    docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT id, data, hora, descricao, kcal FROM refeicoes ORDER BY id DESC LIMIT 3"'
    ```

**Limitação conhecida (D-047):** enquanto um `/r` está nas novas tentativas (até ~40 s), os outros comandos esperam na fila.

## 4. Critérios de aceite

Os da seção 5 de [etapa-4-decisoes.md](etapa-4-decisoes.md), mais: cada task entregue com os testes passando.
