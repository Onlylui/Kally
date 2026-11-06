# Andamento do KALLY

Onde o projeto está no [roteiro](bot-dieta-planejamento.md#9-roteiro-de-desenvolvimento). **Leia este arquivo antes de começar qualquer etapa** e atualize-o quando uma etapa for aprovada pelo usuário.

**Etapa atual:** 3 — `/r` com o Gemini (em andamento)
**Última atualização:** 04/11/2026

---

## Etapas

| # | Etapa | Status | Plano |
|---|---|---|---|
| 1 | Bot papagaio, `/id` e filtro de `ALLOWED_CHAT_IDS` | ✅ concluída | — |
| 2 | Docker, banco, migrações e `/peso` | ✅ concluída (aprovada em 03/11/2026) | [etapa-2-banco-docker-peso.md](etapas/etapa-2-banco-docker-peso.md) |
| 3 | `/r` com o Gemini | 🔧 em andamento | [etapa-3-r-gemini.md](etapas/etapa-3-r-gemini.md) · [decisões](etapas/etapa-3-decisoes.md) |
| 4 | Base de alimentos (IA só para alimentos novos) | ⬜ | — |
| 5 | Botões de corrigir e apagar | ⬜ | — |
| 6 | `/retro` | ⬜ | — |
| 7 | `/dia` e `/semana` | ⬜ | — |
| 8 | `/exportar` | ⬜ | — |
| 9 | Deploy no servidor | ⬜ | — |

Status: ✅ concluída (usuário testou e aprovou) · 🔧 em andamento · ⏳ próxima · ⬜ não iniciada

## O que funciona hoje

- Bot e Postgres sobem juntos com `docker compose up -d --build`; banco na porta `127.0.0.1:5433`.
- Migração `001_inicial.sql` aplicada: as 5 tabelas do MVP mais a `schema_versao`.
- `/id` responde em qualquer chat; os demais comandos só nos chats de `ALLOWED_CHAT_IDS`.
- `/peso` registra e consulta pesagens (RN-012), sem botões.
- O bot papagaio continua ativo, provisório: **sai na etapa 3**, quando o `/r` passa a ser a resposta principal do bot.

## Pendências herdadas

Ressalvas da revisão da etapa 2, ainda não resolvidas. Não bloqueiam a etapa 3, mas convém tratar antes ou junto dela:

- [ ] `banco.dbml` sem alguns `CHECK`s que a `001` cria: macros `>= 0` em `alimentos`, `kcal` e macros `>= 0` em `refeicoes`, `origem IN ('ia','manual')`. Como a `001` já foi aplicada, isso é só documentação: **não** editar a migração.
- [ ] Healthcheck do `db` sem `-h 127.0.0.1`: na primeira subida o bot pode tentar conectar cedo e reiniciar uma vez.
- [ ] RN-012 mostra "82,4 kg em 01/11"; o código e o `exemplos.md` usam "dom 01/11". Alinhar a RN.
- [ ] Comando do `psql` nas seções 6 e 7 do plano da etapa 2 não funciona no host; o do README (`sh -c '...'`) é o correto.
- [ ] Sem resposta ao usuário quando o banco cai durante um comando (só log). Falta definir o texto.

## Como atualizar este arquivo

- Ao começar uma etapa: status 🔧 e link para o plano em `Docs/etapas/`.
- Ao ser aprovada pelo usuário: status ✅ com a data, atualizar "O que funciona hoje" e "Etapa atual", e marcar a etapa no roadmap do `README.md`.
- Ressalvas de revisão que ficarem para depois entram em "Pendências herdadas"; ao resolver, remova a linha.
