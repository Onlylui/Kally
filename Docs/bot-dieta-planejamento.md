# KALLY — Planejamento técnico

Bot de Telegram, num grupo exclusivo, para registrar refeições, estimar calorias e acompanhar o total diário e semanal de cada participante.

| Documento | O que tem |
|---|---|
| [`regras-de-negocio.md`](regras-de-negocio.md) | Como o bot se comporta (fonte da verdade) |
| [`exemplos.md`](exemplos.md) | Conversas de exemplo para cada regra |
| [`decisoes.md`](decisoes.md) | Todas as decisões, com motivo e alternativas descartadas |
| este arquivo | Arquitetura, banco de dados, estrutura e roteiro |

---

## 1. Objetivo

Os participantes registram o que comem com `/r`. O bot calcula as calorias e os macros com uma base própria de alimentos, usa o Gemini só para alimentos que ainda não conhece, grava no Postgres e responde com o total do dia. O histórico pode ser exportado em CSV para análises fora do bot (D-012).

```
João: /r arroz, feijão, 1 bife e salada
KALLY: João: +650 kcal · total hoje: 1.420 kcal
       arroz 200 g · 260 kcal · feijão 100 g · 75 kcal · bife 120 g · 250 kcal · salada 100 g · 65 kcal
       [✏️ Corrigir] [❌ Apagar]
```

---

## 2. Stack

| Camada | Ferramenta | Decisão |
|---|---|---|
| Plataforma | Telegram | D-001 |
| Linguagem | Python 3.12 | D-002 |
| Bot | `python-telegram-bot` v20+ (assíncrono, polling) | D-002, D-005 |
| IA | Gemini via `google-genai`, modelo no `.env` | D-003 |
| Banco | PostgreSQL 16 + `asyncpg` | D-004 |
| Configuração | arquivo `.env` | — |
| Deploy | Docker + Docker Compose | D-007 |

---

## 3. Como funciona

```
Grupo no Telegram ──▶ API do Telegram ◀── KALLY (Python) ──▶ Gemini (só alimentos novos)
                                              │
                                              ▼
                                         PostgreSQL
```

Fluxo de um `/r` (RN-013, RN-016):

1. Pega o texto, o `user_id`, o nome e o horário de envio da mensagem.
2. Separa a descrição em itens e quantidades (`parser.py`).
3. Procura cada alimento na tabela `alimentos`.
4. Os que não estão na base vão ao Gemini, com saída estruturada (`response_schema`), timeout de 15 s e validação (kcal por 100 g entre 0 e 900, macros coerentes). Os novos entram na base.
5. Calcula as calorias e os macros de cada item e grava, numa transação, a refeição e os seus itens. Depois soma o total do dia.
6. Responde no grupo com os botões de corrigir e apagar.

Se o Gemini falhar, nada é registrado (RN-017).

---

## 4. Configuração no Telegram (uma vez só)

1. Conversar com **@BotFather**
2. `/newbot` → escolher nome e username
3. Guardar o **token** gerado (vai no `.env`; nunca subir no GitHub)
4. `/setprivacy` → **Disable**, para o bot ver as mensagens sem comando e avisar quando alguém esquecer o `/r` (RN-013)
5. `/setcommands` → cadastrar `r`, `retro`, `dia`, `semana`, `peso`, `exportar`, para aparecerem no menu do Telegram
6. Criar o grupo e adicionar o bot

---

## 5. Banco de dados

O diagrama está em [`banco.dbml`](banco.dbml); para visualizar, cole o arquivo em [dbdiagram.io](https://dbdiagram.io). As duas descrições precisam estar sempre iguais.

### usuarios

| Coluna | Tipo | Observação |
|---|---|---|
| telegram_id | BIGINT (PK) | |
| nome | TEXT | atualizado a cada mensagem, porque o nome no Telegram muda |
| criado_em | TIMESTAMPTZ | |

### alimentos (RN-016)

| Coluna | Tipo | Observação |
|---|---|---|
| id | BIGSERIAL (PK) | |
| nome | TEXT (UNIQUE) | o texto que a pessoa escreveu, normalizado: minúsculo, sem acento, singular, sem quantidade (D-034) |
| kcal_100g | NUMERIC | entre 0 e 900 |
| proteina_100g / carbo_100g / gordura_100g | NUMERIC | |
| porcao_g | NUMERIC | gramas de 1 porção padrão |
| porcao_nome | TEXT | ex.: "1 bife", "1 unidade", "1 colher de servir" |
| origem | TEXT | `ia` (ou `manual`, quando corrigido no banco) |
| criado_em | TIMESTAMPTZ | |

A busca é só pelo `nome` normalizado (D-030); o `UNIQUE` já cria o índice.

### refeicoes

| Coluna | Tipo | Observação |
|---|---|---|
| id | BIGSERIAL (PK) | |
| telegram_id | BIGINT (FK → usuarios) | |
| chat_id / message_id | BIGINT | mensagem de resposta do bot, para os botões (RN-015) |
| descricao | TEXT | o texto enviado |
| kcal | INT | soma dos itens, ou o valor digitado quando `kcal_manual` |
| proteina_g / carbo_g / gordura_g | NUMERIC | |
| data | DATE | dia em que a refeição conta, no fuso de São Paulo (RN-001) |
| hora | TIME (nullable) | vazia no retroativo sem hora (RN-014) |
| retroativo | BOOLEAN | registrado com `/retro` |
| kcal_manual | BOOLEAN | calorias corrigidas por número (RN-015) |
| registrado_em | TIMESTAMPTZ | quando o registro foi feito |

O dia é calculado no fuso de São Paulo **na hora de gravar** e guardado em `data`. Assim os totais não dependem de fuso na consulta.

Índice em `(telegram_id, data)`.

O botão Apagar remove a refeição com `DELETE`, e os itens vão junto pelo `ON DELETE CASCADE` (D-033).

```sql
-- total do dia (RN-009)
SELECT COALESCE(SUM(kcal), 0)
FROM refeicoes
WHERE telegram_id = $1 AND data = $2;
```

### refeicao_itens (D-029)

Um alimento dentro de uma refeição.

| Coluna | Tipo | Observação |
|---|---|---|
| id | BIGSERIAL (PK) | |
| refeicao_id | BIGINT (FK → refeicoes, `ON DELETE CASCADE`) | |
| alimento_id | BIGINT (FK → alimentos, `ON DELETE RESTRICT`) | |
| ordem | SMALLINT | posição do item na descrição |
| texto | TEXT | trecho da descrição, ex.: "1 bife" |
| gramas | NUMERIC | informado ou porção padrão × unidades (RN-016) |
| kcal | NUMERIC | **copiado** no momento do registro |
| proteina_g / carbo_g / gordura_g | NUMERIC | copiados no momento do registro |

Índices em `refeicao_id` e em `alimento_id`.

- Os valores são copiados da base ao registrar, então corrigir um alimento no banco não muda refeições antigas (D-028).
- Corrigir pela descrição (RN-015) apaga os itens e grava os novos. Corrigir por número muda só o total em `refeicoes`; os itens guardam a estimativa original.
- O total também fica gravado em `refeicoes`, para o `/dia` e o `/semana` não precisarem somar itens.

```sql
-- quanto de cada alimento uma pessoa comeu no mês
SELECT a.nome, SUM(i.gramas) AS gramas, SUM(i.kcal) AS kcal
FROM refeicao_itens i
JOIN refeicoes r ON r.id = i.refeicao_id
JOIN alimentos a ON a.id = i.alimento_id
WHERE r.telegram_id = $1 AND r.data >= $2
GROUP BY a.nome
ORDER BY kcal DESC;
```

### pesos (RN-012)

| Coluna | Tipo |
|---|---|
| id | BIGSERIAL (PK) |
| telegram_id | BIGINT (FK → usuarios) |
| chat_id / message_id | BIGINT |
| peso_kg | NUMERIC(5,2) |
| data | DATE |
| hora | TIME |
| registrado_em | TIMESTAMPTZ |

### Migrações

Os scripts SQL ficam em `migrations/` (`001_inicial.sql`, `002_...`) e são aplicados pelo bot ao iniciar, controlados por uma tabela `schema_versao`. Um `init.sql` do Postgres não serve, porque só roda com o banco vazio.

---

## 6. Estrutura do projeto

```
kally/
├── docker-compose.yml
├── Dockerfile
├── .env.example        # modelo das variáveis (o .env real fica fora do git)
├── .gitignore
├── requirements.txt
├── pytest.ini          # configuração dos testes (rodar com: pytest)
├── migrations/
│   └── 001_inicial.sql
├── tests/              # parser, cálculos e validação do Gemini
└── app/
    ├── main.py         # inicia o bot e aplica as migrações
    ├── handlers.py     # comandos: /r, /retro, /dia, /semana, /peso, /exportar, /id
    ├── botoes.py       # corrigir e apagar (RN-015)
    ├── parser.py       # separa itens, quantidades e datas do /retro
    ├── alimentos.py    # busca na base e completa com o Gemini (RN-016)
    ├── gemini.py       # chamada à IA, schema e validação
    ├── relatorios.py   # textos do /dia e /semana, geração dos CSVs
    └── db.py           # conexão e consultas no Postgres
```

### Variáveis de ambiente (`.env`)

```
TELEGRAM_TOKEN=
GEMINI_API_KEY=
GEMINI_MODEL=            # trocar de modelo sem mexer no código
ALLOWED_CHAT_IDS=        # id(s) do grupo, separados por vírgula
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
TZ=America/Sao_Paulo
```

---

## 7. Docker

Dois serviços no Compose:

- **db**: imagem oficial do Postgres 16, volume para persistir os dados, sem porta exposta para fora
- **bot**: imagem do código Python, sobe só depois do Postgres estar saudável (healthcheck)

Ambos com `restart: unless-stopped`, para voltar sozinhos depois de queda de luz ou reboot.

---

## 8. Cuidados

- **Fuso:** calcular o dia com `ZoneInfo("America/Sao_Paulo")` no código, sem depender da variável `TZ` do container (RN-001).
- **Horário da mensagem:** usar `message.date` do Telegram, não a hora do processamento (RN-007).
- **Grupos autorizados:** filtrar por `ALLOWED_CHAT_IDS` antes de qualquer outra coisa (RN-002).
- **Gemini:** saída estruturada, timeout de 15 s, sem nova tentativa (RN-017). No plano gratuito, o Google pode usar os dados enviados.
- **Botões:** conferir no clique se quem apertou é o dono do registro e se o registro tem até 7 dias (RN-015).
- **Backup:** `pg_dump` agendado no cron, principalmente em servidor caseiro.
- **Segredos:** token e chaves nunca no repositório.

---

## 9. Roteiro de desenvolvimento

Cada etapa termina com algo funcionando no grupo.

1. **Bot papagaio:** criar o bot no BotFather, responder no grupo, `/id` e o filtro de `ALLOWED_CHAT_IDS`
2. **Banco e `/peso`:** Postgres, migrações e o comando mais simples, que testa o banco de ponta a ponta sem IA
3. **`/r` com o Gemini:** registro chamando a IA para a descrição inteira, com o total do dia
4. **Base de alimentos:** `parser.py` e `alimentos.py`; a IA passa a ser chamada só para alimentos novos
5. **Botões:** corrigir e apagar
6. **`/retro`**
7. **`/dia` e `/semana`**
8. **`/exportar`:** os dois CSVs
9. **Docker e deploy** no servidor

### Fora do MVP
- Fotos de pratos
- Comando para ver e corrigir a base de alimentos (D-028)
- Apagar todos os dados de uma pessoa (D-025)
- Carregar a tabela TACO (D-027)
- Painel web
