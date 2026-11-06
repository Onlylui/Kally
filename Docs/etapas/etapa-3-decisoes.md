# Etapa 3: decisões para o `/r` com o Gemini

**Status:** decisões e premissas confirmadas em 04/11/2026 · **Plano:** [etapa-3-r-gemini.md](etapa-3-r-gemini.md) · **Data:** 04/11/2026

Base para os agentes `kally-python` e `kally-revisor`. O usuário confirmou a seção 3 e pediu a implementação em 04/11/2026.

Este documento não substitui `regras-de-negocio.md`, `exemplos.md` nem `decisoes.md`. Onde ele divergir desses arquivos, vale o que está na seção 1; os docs serão ajustados na etapa (seção 7).

---

## 1. Decisões do usuário

| # | Decisão |
|---|---|
| D1 | `alimentos` é gravado já na etapa 3, porque `refeicao_itens.alimento_id` é obrigatório. |
| D2 | O `/r` **não** consulta a base nesta etapa: todo `/r` chama o Gemini. A consulta será necessária nas próximas etapas, então o código não pode dificultar essa inclusão. |
| D3 | Mensagem sem comando recebe **silêncio**, para o grupo poder conversar. O papagaio sai e nada o substitui. Isso altera a RN-013. |
| D4 | A resposta para banco fora do ar entra nesta etapa. |
| D5 | Das pendências herdadas, entram só a do banco fora do ar e os `CHECK`s no `banco.dbml`. Healthcheck, RN-012 e o comando do `psql` ficam de fora. |
| D6 | A etapa tem testes com Postgres real, em banco de teste separado. |
| D7 | Entrega única, sem dividir em 3a e 3b. |
| D8 | O texto do `/r` recebe limpeza simples antes de ir ao Gemini (seção 2). |
| D9 | A descrição tem limite de 500 caracteres (seção 2). |
| D10 | **Não** haverá conferência em código do trecho devolvido pelo Gemini. Fica fora desta etapa. |
| D11 | **Simplicidade no tratamento do texto:** nada de regra por alimento nem separação de itens em código nesta etapa. |
| D12 | Depois da revisão (05/11/2026): tetos de 10.000 g para `gramas` e `porcao_g` e de 100 g por 100 g para cada macro, também com `alcoolico`; erro inesperado fora de banco no `/r` e no `/peso` responde `Algo deu errado. Tente de novo em instantes.` (D-040 em `decisoes.md`). |

## 2. Tratamento do texto do `/r`

Só isto é feito em código antes do Gemini:

1. Tirar o comando (`/r` ou `/r@bot`), preservando as quebras de linha. **Não** usar `" ".join(context.args)`, como em `handlers.py:145`.
2. Limpar: reduzir espaços repetidos em cada linha e remover linhas vazias.
3. Texto vazio: responder o exemplo de uso e encerrar.
4. Mais de 500 caracteres: responder o texto de limite e encerrar, sem chamar o Gemini.
5. Enviar o texto limpo ao Gemini.

`refeicoes.descricao` guarda o texto como a pessoa escreveu, sem a limpeza.

Referência da limpeza:

```python
LIMITE_DESCRICAO = 500

def limpar_descricao(texto: str) -> str:
    linhas = [" ".join(linha.split()) for linha in texto.splitlines()]
    return "\n".join(linha for linha in linhas if linha)
```

**Texto de limite (aprovado em 04/11/2026):** `Descrição muito longa. Use até 500 caracteres.`

O Gemini é responsável por separar os itens, estimar as quantidades, identificar o que não é comida e passar o nome para o singular.

**Risco aceito (D10):** o nome fica só no prompt. O Gemini pode devolver "pão francês" para "pão", e isso pode entrar na base. A quantidade informada pela pessoa também depende do prompt. A resposta mostra nome e gramas, então a pessoa percebe, mas corrigir a base é direto no banco (D-028).

## 3. Premissas confirmadas

**Todas confirmadas pelo usuário em 04/11/2026**, exatamente como abaixo. P9 é um passo manual do usuário no BotFather (entra no teste manual da etapa). Em P11, o modelo é escolha do usuário no `.env`.

| # | Assunto | Decisão |
|---|---|---|
| P1 | Nome do alimento (D-034) | O Gemini devolve o trecho escrito pela pessoa, no singular. Os exemplos com nome dado pela IA são corrigidos. |
| P2 | Alimento já existente | A base vence e nunca é sobrescrita (`ON CONFLICT DO NOTHING`). O item usa os valores da base e os gramas do Gemini. |
| P3 | Validação de macros | Campo `alcoolico` só na resposta, que dispensa a checagem. Regra geral: `abs(4P + 4C + 9G - kcal) <= max(20% de kcal, 10)`. |
| P4 | Arredondamento | Kcal de cada item vira inteiro (`ROUND_HALF_UP`), e o total é a soma. Macros com 1 casa. |
| P5 | `/r` de ontem enviado depois da meia-noite | Data e total saem de `message.date`, e a resposta mostra `total de 31/10`, como em `exemplos.md:189`. A data atual entra por parâmetro. |
| P6 | Item misturado com lixo | Registra os reconhecidos e avisa: `Ignorei: kkkk`. Exige o campo `ignorados` no schema. |
| P7 | Singular | O Gemini devolve no singular. O código só tira maiúsculas, acentos e espaços nas pontas. |
| P8 | Texto de banco fora do ar | `Não consegui confirmar o registro agora. Tente de novo em instantes.` Não dizer "nada foi registrado": a confirmação do commit pode se perder com a refeição já gravada. |
| P9 | Privacidade do bot no grupo | Voltar para `Enable`, já que o bot não precisa ler a conversa. Exige remover e readicionar o bot ao grupo. |
| P10 | Acento nos nomes | A resposta usa o nome como veio do Gemini (`feijão`); a base usa o normalizado (`feijao`). |
| P11 | `GEMINI_MODEL` | Escolha do usuário, no `.env`. |

## 4. Escopo

**Entra:**
- `/r <descrição>` estima com o Gemini, grava `alimentos`, `refeicoes` e `refeicao_itens` e responde com o total do dia;
- saída do papagaio;
- resposta para banco fora do ar, também no `/peso`;
- `CHECK`s no `banco.dbml`, só como documentação;
- testes com Postgres real.

**Fica de fora:**
- `parser.py`, `alimentos.py` e busca prévia na base (etapa 4);
- porção × unidades e o "(2 un.)" na resposta (etapa 4);
- botões e `message_id`, que fica nulo (etapa 5);
- `/retro`, `/dia`, `/semana` e `/exportar`;
- migração nova: a `001` já tem as tabelas e **não** deve ser editada;
- mudanças em `Dockerfile`, `docker-compose.yml` e `.env.example`;
- conferência do trecho devolvido pelo Gemini (D10).

## 5. Direção técnica

### Arquivos

| Arquivo | Mudança |
|---|---|
| `requirements.txt` | `google-genai==2.34.0` e `pydantic==2.14.2` (usada direto no schema) |
| `app/gemini.py` (novo) | Schema, prompt, `FalhaGemini`, `criar_cliente`, `normalizar_nome`, `validar_item`, `estimar` |
| `app/db.py` | `salvar_alimentos` e `registrar_refeicao` |
| `app/handlers.py` | `comando_r`, tratamento do texto, cálculo, formatação, `eh_erro_de_banco`, `tratar_erro`; remove `ecoar` |
| `app/main.py` | Exige `GEMINI_API_KEY` e `GEMINI_MODEL`, registra o `/r`, remove o eco, silencia o log do SDK |
| `tests/` | `conftest.py`, `test_gemini.py`, `test_refeicao.py`, `test_banco_refeicao.py`; `test_handlers.py` perde o teste do eco |

### Fluxo do `/r`

1. `filtrar_chats` barra chat não autorizado (RN-002), antes de qualquer chamada ao Gemini.
2. `salvar_usuario`.
3. Tratamento do texto (seção 2).
4. `gemini.estimar`: falha responde o texto da RN-017; lista vazia responde "Não identifiquei nenhum alimento...". Nada é gravado nos dois casos.
5. Data e hora vêm de `message.date`, em `America/Sao_Paulo` (RN-001, RN-007).
6. `salvar_alimentos`, com a transação própria.
7. Cálculo dos itens.
8. `registrar_refeicao`: refeição, itens e total do dia na mesma transação.
9. Resposta sem botões.

### Gemini

- Usar a API assíncrona (`cliente.aio`). Chamada síncrona trava o bot, e o timeout não a corta.
- Timeout total com `asyncio.timeout(15)`: o timeout do SDK **não** limita o tempo total.
- `HttpOptions(retry_options=HttpRetryOptions(attempts=1))`, sem nova tentativa (D-023).
- Usar `temperature=0` e `system_instruction` separada da descrição.
- `response.parsed is None` (JSON truncado, fora do schema ou sem candidatos) conta como falha: o SDK não lança exceção nesses casos.
- `response_schema` garante o formato, não os valores. Validar kcal de 0 a 900, macros de 0 a 100, `gramas` e `porcao_g` maiores que 0 e até 10.000, `porcao_nome`, nome e `texto` não vazios e sem NUL, e coerência de macros.
- Um item inválido cancela tudo.
- Registrar cada chamada no log com a duração, sem o texto da pessoa nem a chave.
- Conferir que `aiohttp` não está instalado (`pip show aiohttp`), pois ele teria retry implícito em erro de conexão.

Medido em `google-genai` 2.34.0 contra um servidor falso, **não** contra o Gemini real. A primeira chamada real é no teste manual: se o schema for recusado ou o modelo passar de 15 s, ajustar antes de aprovar.

### Preparação para a etapa 4

- `estimar` recebe um texto, sem saber que é a descrição inteira. A etapa 4 passa só o que a base não conhece.
- A etapa 4 acrescenta `buscar_alimentos` antes do `estimar`. Essa função não entra agora.
- Quando o `parser.py` existir, testar a regra de singular dele contra os nomes já gravados, para não duplicar alimentos.

### Banco de teste

- Banco `kally_teste`, nome fixo no código, no mesmo servidor do Compose. Roda com `docker compose run --rm bot pytest`.
- Por teste: recusar rodar se `POSTGRES_DB == "kally_teste"`, conectar ao banco de manutenção `postgres`, nunca ao `POSTGRES_DB`, recriar `kally_teste` (`DROP` e `CREATE` em `execute` separados), criar o pool direto com `asyncpg.create_pool`, conferir `current_database()`, aplicar as migrações reais e apagar o banco ao final.
- Banco inacessível faz o teste **falhar**, nunca pular.

### Limites aceitos

- Alimentos são gravados antes da transação da refeição. Se o banco cair entre as duas, o alimento fica na base sem refeição, o que é inofensivo e não fere D-029.
- Com updates em série, um `/r` lento segura os outros por até 15 s. Aceitável para 2 pessoas.
- A confirmação do commit pode se perder com a refeição gravada. Por isso o texto de P8 não afirma que nada foi registrado; a pessoa pode acabar repetindo o registro.
- `eh_erro_de_banco` inclui `OSError`. Revisar o filtro quando o `/exportar` trouxer I/O de arquivo (etapa 8).

## 6. Critérios de aceite

1. `/r` registra e responde no formato de `exemplos.md`, seção 7, sem o "(2 un.)".
2. Todo `/r` válido chama o Gemini uma única vez.
3. Timeout, erro e resposta inválida respondem o texto da RN-017 e não gravam nada.
4. `/r` vazio, `/r kkkkk` e texto acima de 500 caracteres dão a resposta prevista, e os casos vazio e longo não chamam o Gemini.
5. Espaços repetidos são limpos no envio, as quebras de linha são preservadas e `descricao` guarda o texto original.
6. Mensagem sem comando não gera resposta, e o papagaio não existe mais.
7. `/r` em chat não autorizado não chama o Gemini.
8. Item inválido entre válidos cancela tudo, com teste.
9. Banco fora do ar durante `/r` e `/peso` gera o texto de P8. Erro inesperado fora de banco gera o texto de D12, e P8 fica só para erro de banco.
10. Refeição e itens são gravados na mesma transação, com rollback testado em Postgres real.
11. Refeições às 23:59 e 00:01 caem em dias diferentes, testado em Postgres real, sem depender do relógio.
12. Rodar os testes não muda as contagens do banco real, e `kally_teste` não fica ao final.
13. O bot não sobe sem `GEMINI_API_KEY` ou `GEMINI_MODEL`, com teste.
14. `/peso` e `/id` continuam funcionando.
15. Nenhuma migração nova, e `banco.dbml` com os `CHECK`s.
16. Todos os testes passam com `docker compose run --rm bot pytest`.
17. Docs da seção 7 atualizados e premissas resolvidas.

## 7. Docs a ajustar na etapa

| Documento | Mudança |
|---|---|
| `regras-de-negocio.md` | RN-013: linha 149 (formato) e linha 156 (silêncio, status decidida). Limite de 500 caracteres. RN-016, conforme P1, P3 e P6 |
| `decisoes.md` | Novas decisões: silêncio em mensagem sem comando e limite da descrição; P3 e P6, se confirmadas |
| `exemplos.md` | Linhas 68-74 (silêncio). Novos exemplos de banco fora do ar, limite e item ignorado. Nomes nas linhas 20, 29, 39, 49 e 427 (P1) |
| `bot-dieta-planejamento.md` | Linha 68 (P9). Seção 5, junto com o `banco.dbml`. Seção 6 (`tests/`, `gemini.py`). Seção 7 (banco de teste) |
| `banco.dbml` | `CHECK`s de macros em `alimentos`, kcal e macros em `refeicoes`, `origem IN ('ia','manual')` |
| `README.md` | Linha 5 (status sem papagaio), nota do banco de teste, roadmap na aprovação |
| `andamento.md` | No início: 🔧 e link do plano. Na aprovação: ✅, "O que funciona hoje" e remoção das pendências resolvidas |

## 8. Próximos passos

1. ~~O usuário confirma P1 a P11 e o texto de limite.~~ Feito em 04/11/2026.
2. ~~`kally-python` escreve o plano final em `Docs/etapas/`.~~ Feito: [etapa-3-r-gemini.md](etapa-3-r-gemini.md).
3. ~~O usuário pede a implementação.~~ Feito em 04/11/2026.
4. `kally-python` implementa, `kally-revisor` revisa, o usuário testa e faz o commit.
