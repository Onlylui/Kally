# Andamento do KALLY

Onde o projeto está no [roteiro](bot-dieta-planejamento.md#9-roteiro-de-desenvolvimento). **Leia este arquivo antes de começar qualquer etapa** e atualize-o quando uma etapa for aprovada pelo usuário.

**Etapa atual:** 4 — Resiliência do Gemini (em andamento, T1)
**Última atualização:** 11/11/2026

---

## Etapas

Roteiro revisto em 10/11/2026 ([D-046](decisoes.md#d-046--novo-roteiro)).

| # | Etapa | Status | Plano |
|---|---|---|---|
| 1 | Bot papagaio, `/id` e filtro de `ALLOWED_CHAT_IDS` | ✅ concluída | — |
| 2 | Docker, banco, migrações e `/peso` | ✅ concluída (aprovada em 03/11/2026) | [etapa-2-banco-docker-peso.md](etapas/etapa-2-banco-docker-peso.md) |
| 3 | `/r` com o Gemini | ✅ concluída (aprovada em 08/11/2026) | [etapa-3-r-gemini.md](etapas/etapa-3-r-gemini.md) · [decisões](etapas/etapa-3-decisoes.md) |
| 4 | Resiliência do Gemini (nova tentativa automática e botão "Tentar de novo") | 🔧 em andamento | [plano](etapas/etapa-4-resiliencia-gemini.md) · [decisões](etapas/etapa-4-decisoes.md) |
| 5 | `/dia` | ⬜ | — |
| 6 | Botões de corrigir e apagar | ⬜ | — |
| 7 | `/retro` | ⬜ | — |
| 8 | `/semana` | ⬜ | — |
| 9 | `/exportar` | ⬜ | — |
| 10 | Deploy no servidor | ⬜ | — |

Status: ✅ concluída (usuário testou e aprovou) · 🔧 em andamento · ⏳ próxima · ⬜ não iniciada · ✂️ cortada

### Etapas cortadas

| Etapa antiga | Status | Motivo |
|---|---|---|
| 4 — Base de alimentos (`parser.py`, `alimentos.py`, IA só para alimentos novos) | ✂️ cortada em 10/11/2026 | O modelo da etapa 3 virou o definitivo: o Gemini separa e converte as medidas, inclusive as caseiras, e a base fornece os valores por 100 g ([D-041](decisoes.md#d-041--sem-parser-local-o-gemini-separa-e-converte-a-base-fornece-os-valores)). |

## O que funciona hoje

- Bot e Postgres sobem juntos com `docker compose up -d --build`; banco na porta `127.0.0.1:5433`.
- Migração `001_inicial.sql` aplicada: as 5 tabelas do MVP mais a `schema_versao`.
- `/id` responde em qualquer chat; os demais comandos só nos chats de `ALLOWED_CHAT_IDS`.
- `/peso` registra e consulta pesagens (RN-012), sem botões.
- `/r <descrição>` estima com o Gemini, grava `alimentos`, `refeicoes` e `refeicao_itens` e responde com o total do dia. Todo `/r` chama o Gemini, e alimentos já conhecidos usam os valores por 100 g da base: é o modelo definitivo (D-041). Ainda sem nova tentativa: falha do Gemini exige reenviar o `/r` (resolve na etapa 4).
- Mensagem sem comando recebe silêncio; o papagaio saiu. Privacidade do bot no grupo em **Enable** (P9).
- Banco fora do ar durante `/r` ou `/peso` responde ao usuário (P8); erro inesperado responde o texto de D-040.
- Testes de banco rodam em Postgres real, no banco separado `kally_teste`.

## Pendências herdadas

Ressalvas da revisão da etapa 2, ainda não resolvidas. Não bloqueiam a etapa 4; a proposta é resolvê-las nela (P13 de [etapa-4-decisoes.md](etapas/etapa-4-decisoes.md)):

- [ ] Healthcheck do `db` sem `-h 127.0.0.1`: na primeira subida o bot pode tentar conectar cedo e reiniciar uma vez.
- [ ] RN-012 mostra "82,4 kg em 01/11"; o código e o `exemplos.md` usam "dom 01/11". Alinhar a RN.
- [ ] Comando do `psql` nas seções 6 e 7 do plano da etapa 2 não funciona no host; o do README (`sh -c '...'`) é o correto.

## Como atualizar este arquivo

- Ao começar uma etapa: status 🔧 e link para o plano em `Docs/etapas/`.
- Ao ser aprovada pelo usuário: status ✅ com a data, atualizar "O que funciona hoje" e "Etapa atual", e marcar a etapa no roadmap do `README.md`.
- Ressalvas de revisão que ficarem para depois entram em "Pendências herdadas"; ao resolver, remova a linha.
