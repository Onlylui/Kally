# KALLY

**KALLY** é um bot de Telegram para contar calorias em grupo. Os participantes registram o que comeram, o bot calcula calorias e macros com uma base própria de alimentos (usando o Gemini só para alimentos novos), guarda tudo num banco PostgreSQL e mostra o total do dia e da semana de cada um. O histórico pode ser exportado em CSV para análise.

> 🚧 **Status:** regras do MVP fechadas, desenvolvimento ainda não iniciado.

```
João: /r arroz, feijão, 1 bife e salada
KALLY: João: +650 kcal · total hoje: 1.420 kcal
       arroz 200 g · 260 kcal · feijão 100 g · 75 kcal · bife 120 g · 250 kcal · salada 100 g · 65 kcal
       [✏️ Corrigir] [❌ Apagar]
```

## Documentação

| Documento | O que tem |
|---|---|
| [`Docs/regras-de-negocio.md`](Docs/regras-de-negocio.md) | Como o bot se comporta (fonte da verdade) |
| [`Docs/exemplos.md`](Docs/exemplos.md) | Conversas de exemplo para cada situação |
| [`Docs/decisoes.md`](Docs/decisoes.md) | Todas as decisões do projeto, com motivo e alternativas |
| [`Docs/bot-dieta-planejamento.md`](Docs/bot-dieta-planejamento.md) | Arquitetura, banco de dados e roteiro |

---

## Comandos

| Comando | Descrição |
|---|---|
| `/r <descrição>` | Registra uma refeição. Ex.: `/r 150 g de arroz e 1 filé de frango` |
| `/retro <data> [hora] <descrição>` | Registra uma refeição de até 7 dias atrás. Ex.: `/retro ontem pizza` ou `/retro 28/10 20:00 pizza` |
| `/dia` | Refeições e total de hoje |
| `/semana` | Total de cada dia da semana (segunda a domingo) e a média |
| `/peso [kg]` | Registra o peso (`/peso 82,4`) ou mostra o último (`/peso`) |
| `/exportar [dias]` | CSV das refeições e CSV das pesagens. Ex.: `/exportar 30` |
| `/id` | Mostra o ID do chat (para configurar o bot) |

Cada registro tem os botões **✏️ Corrigir** (nova descrição, ou só o número de calorias) e **❌ Apagar**. Só quem registrou pode usá-los.

**Dica:** quanto mais específica a descrição, melhor a estimativa. Prefira `150 g de arroz e 1 filé de frango` a `um prato de almoço`. A resposta mostra os gramas usados em cada item; se não baterem, corrija pelo botão.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.12 |
| Bot | [python-telegram-bot](https://python-telegram-bot.org/) (assíncrono, polling) |
| IA | [google-genai](https://pypi.org/project/google-genai/) (Gemini) |
| Banco | PostgreSQL 16 + `asyncpg` |
| Deploy | Docker + Docker Compose |

Como usa polling, **não precisa de porta aberta, IP fixo, domínio ou HTTPS**. Roda em qualquer servidor Linux com internet, inclusive um servidor caseiro.

---

## Pré-requisitos

- Docker e Docker Compose
- Um bot criado no Telegram ([@BotFather](https://t.me/BotFather))
- Uma chave da API do Gemini ([Google AI Studio](https://aistudio.google.com/))

### Criando o bot no Telegram

1. Abra o **@BotFather** e envie `/newbot`
2. Escolha nome e username, e guarde o **token** gerado
3. Envie `/setprivacy`, selecione o bot e escolha **Disable** (para ele avisar quando alguém esquecer o `/r`)
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

## Backup

Os dados ficam num volume Docker e sobrevivem a reinicializações. Para gerar um backup:

```bash
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup_$(date +%F).sql
```

Recomendado agendar via `cron` no servidor.

---

## Roadmap

- [ ] Bot papagaio funcionando no grupo, com `/id`
- [ ] Banco, migrações e `/peso`
- [ ] `/r` com o Gemini
- [ ] Base de alimentos (IA só para alimentos novos)
- [ ] Botões de corrigir e apagar
- [ ] `/retro`
- [ ] `/dia` e `/semana`
- [ ] `/exportar`
- [ ] Docker Compose e deploy
