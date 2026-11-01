# Bot de Dieta — Planejamento

Chatbot em grupo do Telegram para registrar refeições, estimar calorias com IA (Gemini) e acompanhar o total diário de cada participante.

---

## 1. Objetivo

- Duas pessoas num grupo do Telegram enviam o que comeram (texto e, futuramente, foto).
- O bot identifica **quem** enviou, manda a descrição para o **Gemini**, recebe calorias e macros, grava no **Postgres** e responde com o **total acumulado do dia**.

Exemplo de interação:

```
João: almocei arroz, feijão, 1 bife e salada
Bot:  João: +650 kcal · total hoje: 1.420 kcal
```

---

## 2. Decisões tomadas

| Tema | Decisão | Motivo |
|---|---|---|
| Plataforma | **Telegram** | Bots em grupo são nativos, gratuitos e sem burocracia |
| WhatsApp | Descartado | API oficial de grupos exige Official Business Account (verificada) e limita a 8 participantes; bibliotecas não oficiais violam os termos e arriscam banimento do número |
| Linguagem | **Python** | — |
| IA | **Gemini** via SDK `google-genai` | O antigo `google-generativeai` foi descontinuado |
| Banco | **PostgreSQL** | — |
| Framework web | **Sem Django** (por enquanto) | Evitar aprender muita coisa ao mesmo tempo; pode entrar depois se quisermos painel/site |
| Recebimento de mensagens | **Polling** | Não precisa de porta aberta, IP fixo, domínio nem HTTPS |
| Deploy | **Docker Compose** | Roda igual na VPS ou no servidor caseiro (Linux) |

---

## 3. Stack

| Camada | Ferramenta |
|---|---|
| Bot | `python-telegram-bot` (v20+, assíncrono) |
| IA | `google-genai` (Gemini) |
| Banco | PostgreSQL 16 |
| Driver do banco | `asyncpg` (ou SQLAlchemy async) |
| Configuração | arquivo `.env` |
| Containers | Docker + Docker Compose |

---

## 4. Como a integração funciona

```
Você no grupo ──▶ Servidores do Telegram ◀──── programa Python ────▶ Gemini API
                                                     │
                                                     ▼
                                                 PostgreSQL
```

- **No Telegram** só existe o *cadastro* do bot. Toda a lógica fica no código Python.
- O programa fica num loop perguntando ao Telegram se chegou mensagem nova (**polling**).
- Para cada mensagem:
  1. Pega texto, `user_id`, nome e `chat_id`
  2. Envia o texto ao Gemini pedindo **resposta em JSON** (itens, kcal, proteína, carbo, gordura)
  3. Grava no Postgres
  4. Soma o total do dia do usuário
  5. Responde no grupo

---

## 5. Configuração no Telegram (uma vez só)

1. Conversar com **@BotFather**
2. `/newbot` → escolher nome e username (ex.: `dieta_dupla_bot`)
3. Guardar o **token** gerado (vai no `.env`; nunca subir no GitHub)
4. `/setprivacy` → **Disable**, para o bot ler todas as mensagens do grupo
5. Criar o grupo e adicionar o bot

---

## 6. Banco de dados (proposta inicial)

**usuarios**

| Coluna | Tipo |
|---|---|
| telegram_id | BIGINT (PK) |
| nome | TEXT |
| meta_kcal | INT (opcional) |
| criado_em | TIMESTAMPTZ |

**refeicoes**

| Coluna | Tipo |
|---|---|
| id | BIGSERIAL (PK) |
| telegram_id | BIGINT (FK → usuarios) |
| chat_id | BIGINT |
| descricao | TEXT |
| itens | JSONB (resposta detalhada do Gemini) |
| kcal | INT |
| proteina_g / carbo_g / gordura_g | NUMERIC |
| criado_em | TIMESTAMPTZ |

Índice em `(telegram_id, criado_em)`.

Total do dia:

```sql
SELECT SUM(kcal)
FROM refeicoes
WHERE telegram_id = $1
  AND criado_em >= $2   -- início do dia em America/Sao_Paulo
  AND criado_em <  $3;  -- início do dia seguinte
```

---

## 7. Estrutura do projeto

```
dieta-bot/
├── docker-compose.yml
├── Dockerfile
├── .env.example        # modelo das variáveis (o .env real fica fora do git)
├── .gitignore
├── requirements.txt
└── app/
    ├── main.py         # inicia o bot
    ├── handlers.py     # o que fazer com cada mensagem/comando
    ├── gemini.py       # chamada à IA
    └── db.py           # conexão e consultas no Postgres
```

### Variáveis de ambiente (`.env`)

```
TELEGRAM_TOKEN=
GEMINI_API_KEY=
GEMINI_MODEL=            # ex.: alias "flash latest"; trocar sem mexer no código
ALLOWED_CHAT_IDS=        # id(s) do grupo de vocês
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
TZ=America/Sao_Paulo
```

---

## 8. Docker

Dois serviços no Compose:

- **db**: imagem oficial do Postgres, volume para persistir dados, sem porta exposta para fora
- **bot**: imagem do código Python, sobe só depois do Postgres estar saudável (healthcheck)

Subir no servidor:

```bash
git clone <repo> && cd dieta-bot
cp .env.example .env   # preencher
docker compose up -d
```

---

## 9. Cuidados

- **`restart: unless-stopped`** no compose, para voltar sozinho após queda de luz ou reboot
- **Modelo do Gemini no `.env`**, porque o Google troca versões com frequência
- **Restringir a `ALLOWED_CHAT_IDS`**, para ninguém usar o bot em outro grupo e gastar a cota do Gemini
- **Fuso `America/Sao_Paulo`** no cálculo do dia (gravar `timestamptz`), senão refeição das 22h cai no dia seguinte em UTC
- **Backup**: `pg_dump` agendado (cron), principalmente no servidor caseiro
- **Token e chaves** nunca no repositório
- **Estimativas da IA são aproximadas**: incentivar informar quantidades ("150 g de arroz")

---

## 10. Comandos planejados

| Comando | Função |
|---|---|
| (mensagem livre) | Registra refeição |
| `/hoje` | Total do dia e lista de refeições |
| `/meta 2000` | Define meta diária |
| `/desfazer` | Apaga o último registro |
| `/corrigir` | Ajusta o último registro |
| `/id` | Mostra o `chat_id` (para configurar `ALLOWED_CHAT_IDS`) |

---

## 11. Roteiro de desenvolvimento

1. Criar o bot no BotFather e rodar um bot "papagaio" (só repete a mensagem)
2. Trocar a resposta fixa por uma chamada ao Gemini com saída em JSON
3. Plugar o Postgres e calcular o total do dia
4. Adicionar comandos (`/hoje`, `/meta`, `/desfazer`)
5. Empacotar com Docker e subir no servidor
6. Extras: fotos de pratos, resumo semanal, Django/painel web se fizer falta
