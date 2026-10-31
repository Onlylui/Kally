# KALLY

**KALLY** é um bot de Telegram para controle de dieta em grupo. Os participantes enviam o que comeram, o bot estima calorias e macros com IA (Gemini), guarda tudo num banco PostgreSQL e responde com o total acumulado do dia de cada um.

> 🚧 **Status:** em planejamento. Veja [`bot-dieta-planejamento.md`](bot-dieta-planejamento.md) para as decisões de projeto.

```
João: almocei arroz, feijão, 1 bife e salada
KALLY: João: +650 kcal · total hoje: 1.420 kcal
```

---

## Funcionalidades

- Registro de refeições por mensagem de texto no grupo
- Identificação automática de quem enviou
- Estimativa de calorias, proteína, carboidrato e gordura via Gemini
- Total diário por pessoa (fuso `America/Sao_Paulo`)
- Meta diária de calorias
- Correção e remoção do último registro
- *(futuro)* Análise de fotos de pratos e resumo semanal

---

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Bot | [python-telegram-bot](https://python-telegram-bot.org/) (assíncrono, polling) |
| IA | [google-genai](https://pypi.org/project/google-genai/) (Gemini) |
| Banco | PostgreSQL 16 + `asyncpg` |
| Deploy | Docker + Docker Compose |

---

## Como funciona

```
Grupo no Telegram ──▶ API do Telegram ◀── KALLY (Python) ──▶ Gemini
                                              │
                                              ▼
                                         PostgreSQL
```

O KALLY busca novas mensagens no Telegram (polling), envia a descrição da refeição ao Gemini pedindo resposta em JSON, grava o resultado no Postgres e responde no grupo com o total do dia.

Como usa polling, **não precisa de porta aberta, IP fixo, domínio ou HTTPS**. Roda em qualquer servidor Linux com internet, inclusive um servidor caseiro.

---

## Pré-requisitos

- Docker e Docker Compose
- Um bot criado no Telegram ([@BotFather](https://t.me/BotFather))
- Uma chave da API do Gemini ([Google AI Studio](https://aistudio.google.com/))

### Criando o bot no Telegram

1. Abra o **@BotFather** e envie `/newbot`
2. Escolha nome e username, e guarde o **token** gerado
3. Envie `/setprivacy`, selecione o bot e escolha **Disable** (para ler todas as mensagens do grupo)
4. Crie o grupo e adicione o bot

---

## Instalação

```bash
git clone <url-do-repositorio> kally
cd kally
cp .env.example .env
# edite o .env com seus tokens e senhas
docker compose up -d
```

Ver os logs:

```bash
docker compose logs -f bot
```

Parar:

```bash
docker compose down
```

---

## Configuração (`.env`)

| Variável | Descrição |
|---|---|
| `TELEGRAM_TOKEN` | Token do bot gerado pelo BotFather |
| `GEMINI_API_KEY` | Chave da API do Gemini |
| `GEMINI_MODEL` | Modelo do Gemini a usar (configurável, pois o Google troca versões com frequência) |
| `ALLOWED_CHAT_IDS` | IDs dos grupos autorizados, separados por vírgula (use `/id` no grupo para descobrir) |
| `POSTGRES_USER` | Usuário do banco |
| `POSTGRES_PASSWORD` | Senha do banco |
| `POSTGRES_DB` | Nome do banco |
| `TZ` | Fuso horário (`America/Sao_Paulo`) |

> ⚠️ Nunca suba o arquivo `.env` para o repositório.

---

## Comandos

| Comando | Descrição |
|---|---|
| *(mensagem livre)* | Registra uma refeição |
| `/hoje` | Mostra o total e as refeições do dia |
| `/meta <kcal>` | Define sua meta diária (ex.: `/meta 2000`) |
| `/desfazer` | Remove seu último registro |
| `/corrigir` | Ajusta seu último registro |
| `/id` | Mostra o ID do chat atual |

**Dica:** quanto mais específica a descrição, melhor a estimativa. Prefira `150 g de arroz e 1 filé de frango grelhado` a `um prato de almoço`. As calorias são estimativas aproximadas.

---

## Estrutura do projeto

```
kally/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── requirements.txt
└── app/
    ├── main.py         # inicialização do bot
    ├── handlers.py     # tratamento de mensagens e comandos
    ├── gemini.py       # integração com o Gemini
    └── db.py           # conexão e consultas no PostgreSQL
```

---

## Banco de dados

- **usuarios**: `telegram_id`, `nome`, `meta_kcal`, `criado_em`
- **refeicoes**: `id`, `telegram_id`, `chat_id`, `descricao`, `itens` (JSONB), `kcal`, `proteina_g`, `carbo_g`, `gordura_g`, `criado_em`

Os dados ficam num volume Docker e sobrevivem a reinicializações.

### Backup

```bash
docker compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%F).sql
```

Recomendado agendar via `cron` no servidor.

---

## Roadmap

- [ ] Bot "papagaio" funcionando no grupo
- [ ] Integração com o Gemini (resposta em JSON)
- [ ] Persistência no PostgreSQL e total diário
- [ ] Comandos `/hoje`, `/meta`, `/desfazer`, `/corrigir`
- [ ] Docker Compose para deploy
- [ ] Análise de fotos de pratos
- [ ] Resumo semanal
- [ ] Painel web (avaliar Django)
