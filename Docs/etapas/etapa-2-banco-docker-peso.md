# Etapa 2 — Docker, banco e `/peso`

Instruções para implementar a etapa 2 do roteiro. Escrito para os agentes `kally-python` (implementa) e `kally-revisor` (revisa), e para o usuário acompanhar.

**Status:** concluída (aprovada em 03/11/2026; ressalvas em [andamento.md](../andamento.md)) · **Etapa anterior:** 1 (bot papagaio, concluída)

---

## 1. Objetivo

Ao fim desta etapa:
- o bot e o Postgres rodam juntos com `docker compose up`;
- o banco é criado pelas migrações, com todas as tabelas do [`banco.dbml`](../banco.dbml);
- o `/peso` registra e consulta pesagens, testando o banco de ponta a ponta **sem depender do Gemini**.

## 2. Escopo

**Entra:**
- `Dockerfile`, `.dockerignore` e `docker-compose.yml` com os serviços `db` e `bot`
- `migrations/001_inicial.sql` com **todas** as tabelas do MVP
- `app/db.py`: pool de conexões, aplicação das migrações e as consultas desta etapa
- Cadastro automático do usuário (`usuarios`)
- Comando `/peso` (RN-012), sem botões
- Testes da lógica pura
- Atualização dos docs afetados (seção 9)

**Não entra** (fica para as próximas etapas):
- `/r`, Gemini e base de alimentos (etapas 3 e 4)
- Botões de corrigir e apagar, inclusive no `/peso` (etapa 5)
- `/retro`, `/dia`, `/semana` e `/exportar` (etapas 6 a 8)
- O papagaio continua como está; ele sai na etapa 3.

## 3. Leitura obrigatória antes de começar

| Documento | Por quê |
|---|---|
| [`banco.dbml`](../banco.dbml) | Estrutura exata das tabelas, `CHECK`s e índices |
| [`regras-de-negocio.md`](../regras-de-negocio.md) | RN-001, RN-002, RN-007 e RN-012 |
| [`exemplos.md`](../exemplos.md), seção 5 | Textos exatos das respostas do `/peso` |
| [`decisoes.md`](../decisoes.md) | D-004, D-007, D-013, D-021, D-033 e **D-035** |
| `app/main.py` e `app/handlers.py` | Código da etapa 1, que esta etapa estende |

## 4. Regras que valem em toda a etapa

- **Nunca leia, exiba ou edite o `.env`.** Use o `.env.example` como referência.
- **Nunca faça commit nem push.** O usuário faz os commits.
- **Tudo roda em Docker (D-035).** Não crie instruções para rodar o bot fora do container.
- **SQL sempre parametrizado** (`$1`, `$2`). Nunca f-string montando SQL.
- **Fuso** com `ZoneInfo("America/Sao_Paulo")` explícito (RN-001); **horário** vindo de `message.date` (RN-007).
- **Simplicidade:** funções diretas, sem ORM, sem classes que a etapa não exige.
- Se algo neste documento contradizer as regras ou o `banco.dbml`, **pare e pergunte**.

---

## 5. Entregas, arquivo por arquivo

### 5.1 `requirements.txt`
Acrescentar `asyncpg`, com versão fixa (`asyncpg==x.y.z`), compatível com Python 3.12.

### 5.2 `Dockerfile`
- Imagem base `python:3.12-slim`.
- `WORKDIR /app`.
- Copiar primeiro o `requirements.txt` e instalar com `pip install --no-cache-dir`, para o Docker reaproveitar essa camada quando só o código mudar.
- Depois copiar `app/`, `migrations/`, `tests/` e `pytest.ini`.
- `CMD ["python", "-m", "app.main"]`.
- O `.env` **nunca** entra na imagem.

### 5.3 `.dockerignore`
No mínimo: `.env`, `.venv`, `.git`, `__pycache__/`, `.pytest_cache/`, `Docs/`.

### 5.4 `docker-compose.yml`

**Serviço `db`:**
- imagem `postgres:16`;
- `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` lidos do `.env` (o Compose lê o `.env` da pasta automaticamente);
- volume nomeado `kally_dados` em `/var/lib/postgresql/data`;
- porta `127.0.0.1:5433:5432`: acessível só da própria máquina, para consulta com DBeaver ou pgAdmin. A 5433 evita conflito com o Postgres local que já usa a 5432 (D-035);
- `healthcheck` com `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`;
- `restart: unless-stopped`.

**Serviço `bot`:**
- `build: .`;
- `env_file: .env`;
- `environment`: `POSTGRES_HOST=db` e `POSTGRES_PORT=5432`. Ficam fixos no Compose, não no `.env`, porque dentro da rede do Compose o endereço do banco é sempre esse;
- `depends_on` o `db` com `condition: service_healthy`;
- volumes `./app:/app/app`, `./migrations:/app/migrations` e `./tests:/app/tests`, para o código editado valer sem reconstruir a imagem;
- `restart: unless-stopped`.

### 5.5 `.env.example`
- Sem `POSTGRES_HOST` e `POSTGRES_PORT` (ficam no Compose).
- Comentário dizendo que `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` são usados pelo container do banco para criá-lo na primeira vez, e pelo bot para conectar.

### 5.6 `migrations/001_inicial.sql`
Cria as tabelas `usuarios`, `alimentos`, `refeicoes`, `refeicao_itens` e `pesos` **exatamente** como no `banco.dbml`, inclusive o que o DBML só registra em notas:

| Tabela | Restrições |
|---|---|
| `alimentos` | `nome` UNIQUE; `CHECK (kcal_100g BETWEEN 0 AND 900)`; macros `>= 0`; `CHECK (porcao_g > 0)`; `CHECK (origem IN ('ia', 'manual'))` |
| `refeicoes` | FK para `usuarios`; `CHECK (kcal >= 0)`; macros `>= 0`; índice `(telegram_id, data)` |
| `refeicao_itens` | FK para `refeicoes` com `ON DELETE CASCADE`; FK para `alimentos` com `ON DELETE RESTRICT`; `CHECK (gramas > 0)`; índices em `refeicao_id` e `alimento_id` |
| `pesos` | FK para `usuarios`; `CHECK (peso_kg BETWEEN 30 AND 300)`; índice `(telegram_id, data)` |

Todas as tabelas do MVP entram já nesta migração, mesmo as que só serão usadas nas próximas etapas: assim o banco nasce igual ao diagrama.

A `schema_versao` **não** entra no `001`: quem a cria é o aplicador de migrações (5.7), porque ele precisa dela antes de rodar qualquer migração.

### 5.7 `app/db.py`

**Conexão:**
- `criar_pool()`: cria o pool do `asyncpg` com `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB`.

**Migrações:**
- `aplicar_migracoes(pool)`:
  1. cria a `schema_versao` com `CREATE TABLE IF NOT EXISTS`;
  2. lista os arquivos de `migrations/` em ordem pelo número do nome (`001_...`, `002_...`);
  3. para cada número que ainda não está na `schema_versao`, executa o arquivo e grava o número, **na mesma transação**. Se falhar, nada daquela migração fica pela metade;
  4. registra no log cada migração aplicada.

**Consultas desta etapa:**
- `salvar_usuario(pool, telegram_id, nome)`: `INSERT ... ON CONFLICT (telegram_id) DO UPDATE SET nome = EXCLUDED.nome`.
- `registrar_peso(pool, telegram_id, chat_id, peso_kg, data, hora)`: grava a pesagem e devolve a **pesagem anterior** da mesma pessoa (a mais recente antes desta, de qualquer data), ou `None` se for a primeira. As duas coisas na mesma transação.
- `ultimo_peso(pool, telegram_id)`: a pesagem mais recente, ou `None`.

"Mais recente" é por `data` e `hora`, com `id` como desempate.

`message_id` fica nulo nesta etapa; ele só passa a ser usado com os botões, na etapa 5.

### 5.8 `app/main.py`
- Criar o pool e aplicar as migrações na inicialização (`post_init` do `Application`), guardando o pool em `bot_data["pool"]`.
- Fechar o pool no encerramento (`post_shutdown`).
- Se o banco não estiver acessível ou uma migração falhar, o bot **para** com uma mensagem clara no log. Não sobe pela metade.
- Registrar o handler do `/peso`.

### 5.9 Comando `/peso` (RN-012)

**Cadastro do usuário:** antes de registrar ou consultar, chamar `salvar_usuario` com o `first_name` do Telegram. Isso atende "criado no primeiro comando, nome atualizado a cada mensagem".

**Data e hora:** `message.date` convertido para `America/Sao_Paulo`; `data` e `hora` gravadas já no fuso de São Paulo.

**Leitura do valor** (função pura, testável, ex.: `ler_peso(texto) -> Decimal | None`):
- aceita vírgula ou ponto: `82,4`, `82.4`, `82`;
- até 2 casas decimais;
- aceita a unidade colada ou separada: `82,4kg`, `82,4 kg`;
- qualquer outra coisa é inválida.

**Respostas** (iguais às de `exemplos.md`, sem os botões nesta etapa):

| Situação | Resposta |
|---|---|
| `/peso 82,4` com pesagem anterior | `João: 82,4 kg registrado (anterior: 83,1 kg em 28/10)` |
| `/peso 64.8`, primeira pesagem | `Maria: 64,8 kg registrado (primeira pesagem)` |
| `/peso` sem número | `João: 82,4 kg em dom 01/11` |
| `/peso` sem nenhuma pesagem | `João: nenhuma pesagem registrada ainda. Ex.: /peso 82,4` |
| `/peso 824` (fora de 30 a 300) | `Peso fora do esperado (30 a 300 kg). Ex.: /peso 82,4` |
| `/peso abc` (não é número) | `Não entendi o peso. Ex.: /peso 82,4` |

As duas últimas linhas novas ("nenhuma pesagem" e "não entendi") não estão em `exemplos.md`: acrescente-as lá (seção 9).

**Formatação:**
- peso com vírgula decimal e sem zeros sobrando à direita: `82,40` → `82,4`; `82,00` → `82`;
- data como `DD/MM`;
- dia da semana abreviado em português (`seg`, `ter`, `qua`, `qui`, `sex`, `sáb`, `dom`), com uma lista própria no código. **Não** usar `locale`, que depende do sistema.

### 5.10 Testes
Lógica pura, sem banco real, sem Telegram e sem Gemini:

- `ler_peso`: vírgula, ponto, inteiro, `kg` colado e separado, 2 casas, 3 casas (inválido), negativo, vazio, texto.
- Faixa de 30 a 300: limites `30` e `300` válidos; `29,99` e `300,01` inválidos.
- Formatação do peso e da data, incluindo o dia da semana.
- **Fuso:** uma mensagem enviada às `02:30 UTC` de segunda conta como domingo em São Paulo (`23:30`).
- Ordem das migrações: `002` depois de `001`, `010` depois de `002`.
- Montagem de cada uma das respostas da tabela 5.9.

Os testes da etapa 1 continuam passando.

Teste do banco de verdade é feito à mão, pelo roteiro da seção 7.

---

## 6. Comandos do dia a dia

```bash
docker compose up -d --build        # sobe tudo (o --build é necessário na primeira vez e quando o requirements.txt muda)
docker compose logs -f bot          # acompanha o log do bot
docker compose restart bot          # aplica mudanças no código
docker compose run --rm bot pytest  # roda os testes
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"   # abre o banco no terminal
docker compose down                 # para tudo (os dados continuam no volume)
```

⚠️ `docker compose down -v` **apaga o volume e todos os dados**. Só para recomeçar do zero.

Estes comandos vão para o README (seção 9).

---

## 7. Como o usuário testa no Telegram

1. `docker compose up -d --build` e conferir no log: as migrações aplicadas e "KALLY iniciado".
2. No grupo, `/peso`: deve responder "nenhuma pesagem registrada ainda".
3. `/peso 82,4`: "82,4 kg registrado (primeira pesagem)".
4. `/peso 81.9`: "81,9 kg registrado (anterior: 82,4 kg em ...)".
5. `/peso`: mostra 81,9 kg com a data de hoje.
6. `/peso 824` e `/peso abc`: as duas mensagens de erro.
7. A outra pessoa manda `/peso 64,8`: "primeira pesagem" para ela, sem misturar com a primeira.
8. `docker compose restart bot` e `/peso` de novo: o dado continua lá, e o log não reaplica a migração.
9. No `psql`, `SELECT * FROM schema_versao;` mostra a versão 1, e `\dt` lista as 6 tabelas.

## 8. Critérios de aceite

- [ ] `docker compose up -d --build` sobe `db` e `bot` sem erro, numa máquina com o Postgres local na 5432
- [ ] Na primeira subida, a migração `001` é aplicada; nas seguintes, nenhuma é reaplicada
- [ ] As 6 tabelas existem com as restrições da tabela 5.6
- [ ] O `/peso` funciona em todas as situações da tabela 5.9
- [ ] A data da pesagem respeita o fuso de São Paulo
- [ ] Banco fora do ar na inicialização → o bot para com mensagem clara
- [ ] O `.env` não está na imagem (`.dockerignore`)
- [ ] A porta do banco está presa ao `127.0.0.1`
- [ ] Todos os testes passam com `docker compose run --rm bot pytest`
- [ ] O papagaio e o `/id` da etapa 1 continuam funcionando
- [ ] Docs da seção 9 atualizados

## 9. Docs a atualizar junto com o código

| Documento | Mudança |
|---|---|
| `bot-dieta-planejamento.md` | Roteiro: Docker passa a fazer parte da etapa 2 (D-035), e a etapa 9 vira só o deploy no servidor. Seção 7 (Docker): a porta `127.0.0.1:5433`, os volumes do código e o bot no Compose desde já. Seção 6: incluir `Dockerfile`, `.dockerignore` e `migrations/001_inicial.sql` |
| `README.md` | Instalação e uso só com Docker; os comandos da seção 6; roadmap com a etapa 1 marcada |
| `exemplos.md`, seção 5 | As respostas "nenhuma pesagem registrada ainda" e "não entendi o peso" |
| `.env.example` | Como na 5.5 |
| `.claude/agents/kally-python.md` | Seção de Docker: tudo em container, `.env` só via `env_file`, porta do banco no `127.0.0.1`, comandos de rodar e testar |
| `.claude/agents/kally-revisor.md` | No checklist: `.env` fora da imagem, porta presa ao `127.0.0.1`, healthcheck, testes rodando no container |

## 10. Fluxo de trabalho

1. **`kally-python`** implementa as seções 5 e 9, roda os testes no container e entrega o resumo (arquivos, regras cobertas, resultado dos testes, o que ficou pendente).
2. **`kally-revisor`** revisa contra este documento, o `banco.dbml` e as regras, usando também a seção 8 como checklist.
3. Achados 🔴 são corrigidos pelo `kally-python`, e o revisor confere de novo.
4. **O usuário** testa no Telegram pelo roteiro da seção 7 e faz o commit.

## 11. Pontos de atenção para a revisão

- A migração bate coluna a coluna com o `banco.dbml`?
- Migração e registro na `schema_versao` estão na mesma transação?
- `registrar_peso` devolve a anterior correta quando há duas pesagens no mesmo dia?
- Conexões voltam ao pool em todos os caminhos, inclusive de erro?
- Algum `datetime.now()` ou dependência do fuso do container?
- O filtro de chats (RN-002) continua rodando antes do `/peso`?
- Alguma variável de ambiente, senha ou token aparece no log?
