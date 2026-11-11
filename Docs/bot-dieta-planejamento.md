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

Os participantes registram o que comem com `/r`. O Gemini separa os itens e converte as quantidades em gramas; as calorias e os macros saem dos valores por 100 g de uma base própria de alimentos, que aprende cada alimento novo (D-041). O bot grava no Postgres e responde com o total do dia. O histórico pode ser exportado em CSV para análises fora do bot (D-012).

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
Grupo no Telegram ──▶ API do Telegram ◀── KALLY (Python) ──▶ Gemini (todo /r)
                                              │
                                              ▼
                                         PostgreSQL
```

Fluxo de um `/r` (RN-013, RN-016):

1. Pega o texto, o `user_id`, o nome e o horário de envio da mensagem.
2. Limpa a descrição e manda inteira ao Gemini, com saída estruturada (`response_schema`). Ele separa os itens, converte as quantidades em gramas (inclusive medidas caseiras) e devolve os valores por 100 g (D-041).
3. Valida a resposta (kcal por 100 g entre 0 e 900, macros coerentes, tetos de D-040).
4. Grava os alimentos novos na base; os que já existem não são sobrescritos e usam os valores por 100 g da base.
5. Calcula as calorias e os macros de cada item (valores da base × gramas do Gemini) e grava, numa transação, a refeição e os seus itens. Depois soma o total do dia.
6. Responde no grupo com os botões de corrigir e apagar (etapa 6).

Se o Gemini falhar, nada é registrado. Nas falhas passageiras o bot tenta de novo sozinho, e a mensagem de falha traz o botão "Tentar de novo" (RN-017, D-045).

---

## 4. Configuração no Telegram (uma vez só)

1. Conversar com **@BotFather**
2. `/newbot` → escolher nome e username
3. Guardar o **token** gerado (vai no `.env`; nunca subir no GitHub)
4. `/setprivacy` → **Enable**: o bot só precisa receber comandos e fica em silêncio na conversa (D-036). Ao mudar essa opção com o bot já no grupo, remova-o e adicione-o de novo
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
| nome | TEXT (UNIQUE) | nome devolvido pelo Gemini (palavras da pessoa, no singular, sem quantidade; correções de grafia do Gemini são aceitas), normalizado: minúsculo, sem acento (D-043) |
| kcal_100g | NUMERIC | entre 0 e 900 |
| proteina_100g / carbo_100g / gordura_100g | NUMERIC | `>= 0` |
| porcao_g | NUMERIC | gramas de 1 porção padrão, `> 0`; só referência, não entra na conta (D-044) |
| porcao_nome | TEXT | ex.: "1 bife", "1 unidade", "1 colher de servir" |
| origem | TEXT | `ia` (padrão) ou `manual`, quando corrigido no banco; `CHECK` só aceita esses dois |
| criado_em | TIMESTAMPTZ | |

A busca é só pelo `nome` normalizado (D-030); o `UNIQUE` já cria o índice.

### refeicoes

| Coluna | Tipo | Observação |
|---|---|---|
| id | BIGSERIAL (PK) | |
| telegram_id | BIGINT (FK → usuarios) | |
| chat_id / message_id | BIGINT | mensagem de resposta do bot, para os botões (RN-015) |
| descricao | TEXT | o texto enviado |
| kcal | INT | soma dos itens, ou o valor digitado quando `kcal_manual`; `>= 0` |
| proteina_g / carbo_g / gordura_g | NUMERIC | `>= 0` |
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
| gramas | NUMERIC | quantidade convertida em gramas pelo Gemini (RN-016) |
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
├── docker-compose.yml  # serviços db e bot (D-035)
├── Dockerfile          # imagem do bot
├── .dockerignore       # o que não entra na imagem (inclusive o .env)
├── .env.example        # modelo das variáveis (o .env real fica fora do git)
├── .gitignore
├── requirements.txt
├── pytest.ini          # configuração dos testes (rodar com: docker compose run --rm bot pytest)
├── migrations/
│   └── 001_inicial.sql # todas as tabelas do MVP
├── tests/              # lógica pura, Gemini com servidor falso e Postgres real em kally_teste
└── app/
    ├── main.py         # inicia o bot e aplica as migrações
    ├── handlers.py     # comandos: /r, /retro, /dia, /semana, /peso, /exportar, /id
    ├── botoes.py       # corrigir e apagar (RN-015)
    ├── parser.py       # só as datas do /retro (D-041)
    ├── gemini.py       # chamada à IA, novas tentativas, schema, prompt, normalização do nome e validação
    ├── relatorios.py   # textos do /dia e /semana, geração dos CSVs
    └── db.py           # conexão e consultas no Postgres
```

### Variáveis de ambiente (`.env`)

```
TELEGRAM_TOKEN=
GEMINI_API_KEY=
GEMINI_MODEL=            # trocar de modelo sem mexer no código
ALLOWED_CHAT_IDS=        # id(s) do grupo, separados por vírgula
POSTGRES_USER=          # usados pelo container do banco (criação) e pelo bot (conexão)
POSTGRES_PASSWORD=
POSTGRES_DB=
TZ=America/Sao_Paulo
```

`POSTGRES_HOST` e `POSTGRES_PORT` não ficam no `.env`: estão fixos no `docker-compose.yml` (`db` e `5432`), porque dentro da rede do Compose o endereço do banco é sempre esse.

---

## 7. Docker

Tudo roda em Docker Compose desde a etapa 2, no desenvolvimento e no servidor, inclusive os testes (D-035). Dois serviços:

- **db**: imagem oficial do Postgres 16, volume nomeado `kally_dados` para persistir os dados, healthcheck com `pg_isready`. A porta fica presa ao `127.0.0.1:5433`: só a própria máquina acessa (DBeaver, pgAdmin), e a 5433 não conflita com um Postgres local na 5432.
- **bot**: imagem do código Python (`Dockerfile`), sobe só depois do Postgres estar saudável. Lê o `.env` por `env_file` (o `.env` nunca entra na imagem; está no `.dockerignore`). Encontra o banco em `db:5432`. As pastas `app/`, `migrations/` e `tests/` são montadas no container: mudou o código, basta `docker compose restart bot`, sem reconstruir a imagem.

Ambos com `restart: unless-stopped`, para voltar sozinhos depois de queda de luz ou reboot.

**Banco de teste:** os testes de banco usam `kally_teste`, no mesmo servidor do Compose. O nome é fixo no código (`tests/conftest.py`). A cada teste, o banco é recriado pelo banco de manutenção `postgres`, recebe as migrações reais e é apagado ao final. Os testes nunca conectam ao `POSTGRES_DB` e se recusam a rodar se ele se chamar `kally_teste`. Banco inacessível faz o teste falhar, nunca pular.

---

## 8. Cuidados

- **Fuso:** calcular o dia com `ZoneInfo("America/Sao_Paulo")` no código, sem depender da variável `TZ` do container (RN-001).
- **Horário da mensagem:** usar `message.date` do Telegram, não a hora do processamento (RN-007).
- **Grupos autorizados:** filtrar por `ALLOWED_CHAT_IDS` antes de qualquer outra coisa (RN-002).
- **Gemini:** saída estruturada, resposta validada, novas tentativas só nas falhas passageiras e dentro de um tempo máximo (RN-017; tempos definidos na etapa 4). No plano gratuito, o Google pode usar os dados enviados.
- **Botões:** conferir no clique se quem apertou é o dono do registro e se o registro tem até 7 dias (RN-015).
- **Backup:** `pg_dump` agendado no cron, principalmente em servidor caseiro.
- **Segredos:** token e chaves nunca no repositório.

---

## 9. Roteiro de desenvolvimento

Cada etapa termina com algo funcionando no grupo.

1. **Bot papagaio:** criar o bot no BotFather, responder no grupo, `/id` e o filtro de `ALLOWED_CHAT_IDS`
2. **Docker, banco e `/peso`:** bot e Postgres no Docker Compose (D-035), migrações e o comando mais simples, que testa o banco de ponta a ponta sem IA
3. **`/r` com o Gemini:** registro chamando a IA para a descrição inteira, com o total do dia
4. **Resiliência do Gemini:** nova tentativa automática nas falhas passageiras e botão "Tentar de novo" (D-045)
5. **`/dia`**
6. **Botões:** corrigir e apagar
7. **`/retro`**
8. **`/semana`**
9. **`/exportar`:** os dois CSVs
10. **Deploy** no servidor (o Docker já vem da etapa 2)

A antiga etapa 4 (base de alimentos com `parser.py` e `alimentos.py`) foi cortada: o modelo da etapa 3 é o definitivo (D-041). O roteiro atual é o de D-046.

### Fora do MVP
- Fotos de pratos
- Comando para ver e corrigir a base de alimentos (D-028)
- Apagar todos os dados de uma pessoa (D-025)
- Carregar a tabela TACO (D-027)
- Modelo reserva do Gemini (D-045)
- Cache de resposta por linha e nomes da base no prompt (D-042)
- Painel web
