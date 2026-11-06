# Etapa 3 — `/r` com o Gemini

Instruções para implementar a etapa 3 do roteiro. Escrito para os agentes `kally-python` (implementa) e `kally-revisor` (revisa), e para o usuário acompanhar.

**Status:** implementada, aguardando revisão e o teste do usuário · **Etapa anterior:** 2 (concluída) · **Fonte principal:** [etapa-3-decisoes.md](etapa-3-decisoes.md), com D1 a D11, P1 a P11, direção técnica e critérios de aceite. Este plano não repete o que está lá.

---

## 1. Objetivo

Ao fim desta etapa:
- `/r <descrição>` estima com o Gemini, grava `alimentos`, `refeicoes` e `refeicao_itens` e responde com o total do dia;
- o papagaio sai, e mensagem sem comando recebe silêncio;
- banco fora do ar durante `/r` ou `/peso` gera uma resposta ao usuário;
- o banco é testado de verdade, em `kally_teste`.

## 2. Escopo

Seções 1 e 4 do [doc de decisões](etapa-3-decisoes.md). Fora do escopo, principalmente: `parser.py`, `alimentos.py`, busca prévia na base, "(2 un.)", botões, conferência do trecho devolvido (D10), regra por alimento (D11), migração nova e mudanças em `Dockerfile`, `docker-compose.yml` e `.env.example`.

## 3. Leitura obrigatória

| Documento | Por quê |
|---|---|
| [`etapa-3-decisoes.md`](etapa-3-decisoes.md) | Tudo o que foi decidido para esta etapa |
| [`regras-de-negocio.md`](../regras-de-negocio.md) | RN-001, RN-002, RN-007, RN-013, RN-016 e RN-017 |
| [`exemplos.md`](../exemplos.md), seções 1 e 7 | Textos das respostas |
| [`decisoes.md`](../decisoes.md) | D-022, D-023, D-026, D-029, D-031 e D-034 |

## 4. Regras que valem em toda a etapa

As mesmas da etapa 2: nunca ler o `.env`, nunca fazer commit, tudo em Docker, SQL parametrizado, fuso explícito, `message.date`. E mais:
- os testes nunca chamam o Gemini nem o Telegram reais;
- os testes nunca tocam no banco de `POSTGRES_DB`.

---

## 5. Entregas, arquivo por arquivo

### 5.1 `requirements.txt`
Acrescentar `google-genai==2.34.0` e `pydantic==2.14.2`. `aiohttp` não pode estar instalado.

### 5.2 `app/gemini.py` (novo)
- `ItemEstimado` e `RespostaGemini`: schema pydantic. Item: `nome`, `texto`, `gramas`, `kcal_100g`, `proteina_100g`, `carbo_100g`, `gordura_100g`, `porcao_g`, `porcao_nome`, `alcoolico`. Resposta: `itens` e `ignorados`.
- `PROMPT`: instrução de sistema (P1, P6, P7, D-031).
- `FalhaGemini`: qualquer falha da chamada ou resposta inválida (RN-017).
- `criar_cliente(chave)`: cliente com `attempts=1`.
- `normalizar_nome(nome)`: minúsculas, sem acento, sem espaços nas pontas (P7).
- `validar_item(item)`: valores, além do formato garantido pelo schema, com os tetos de D-040 (`gramas` e `porcao_g` até 10.000 g, macros até 100 g por 100 g) e sem NUL em `nome`, `texto` e `porcao_nome`. `alcoolico` só dispensa a coerência de macros (P3).
- `estimar(cliente, modelo, texto)`: uma chamada, com `asyncio.timeout(15)`, e registro da duração no log.

`refeicao_itens.texto` é obrigatório, por isso o schema tem `texto`, além do `nome`. Só é conferido que não vem vazio (D10).

### 5.3 `app/db.py`
- `salvar_alimentos(pool, alimentos)`: `ON CONFLICT (nome) DO NOTHING` e leitura dos valores da base, em transação própria. Devolve `{nome: linha}` (P2).
- `registrar_refeicao(...)`: refeição, itens e total do dia na mesma transação. Devolve o total do dia.

### 5.4 `app/handlers.py`
- Sai `ecoar`. Entram os textos, `extrair_descricao`, `limpar_descricao`, `calcular_itens`, `formatar_kcal`, `resposta_refeicao`, `comando_r` e `eh_erro_de_banco`.
- `tratar_erro` responde o texto de P8 quando o erro é de banco e o texto de erro inesperado nos demais casos (D-040). Sem mensagem para responder, só registra no log; se a resposta falhar, também.

| Situação | Resposta |
|---|---|
| Registrado, hoje | `João: +650 kcal · total hoje: 1.420 kcal` e, na linha seguinte, `arroz 200 g · 260 kcal · feijão 100 g · 75 kcal` |
| Registrado, `message.date` de outro dia (P5) | `João: +650 kcal · total de 31/10: 1.420 kcal` e a linha dos itens |
| Item misturado com lixo (P6) | Acrescenta a linha `Ignorei: kkkk` |
| `/r` vazio | `Descreva o que comeu, ex.: /r 150 g de arroz e 1 filé de frango` |
| Acima de 500 caracteres | `Descrição muito longa. Use até 500 caracteres.` |
| Nenhum alimento | `Não identifiquei nenhum alimento. Descreva o que comeu, ex.: /r 150 g de arroz e 1 filé de frango` |
| Falha do Gemini | `Não consegui estimar agora. Nada foi registrado, tente de novo em instantes.` |
| Banco fora do ar | `Não consegui confirmar o registro agora. Tente de novo em instantes.` |
| Erro inesperado, fora de banco (D-040) | `Algo deu errado. Tente de novo em instantes.` |

### 5.5 `app/main.py`
- `ler_config_gemini()`: exige `GEMINI_API_KEY` e `GEMINI_MODEL`, ou o bot não sobe.
- `registrar_handlers(app)`: filtro, `/id`, `/peso` e `/r`, sem o eco.
- `configurar_log()`: silencia o log do SDK.

### 5.6 Testes

| Arquivo | O que cobre |
|---|---|
| `tests/conftest.py` | Fixture `pool_teste`, com as salvaguardas de `kally_teste`; bot real do PTB com requisições falsas, sem rede |
| `tests/test_gemini.py` | `normalizar_nome`, `validar_item`, `estimar` com cliente falso e contra um servidor HTTP falso local |
| `tests/test_refeicao.py` | Texto, cálculo, formatação, `comando_r` com banco falso, erros de banco e handlers registrados |
| `tests/test_banco_refeicao.py` | Postgres real: `alimentos`, transação, rollback, dia no fuso e fluxo completo |

Banco inacessível faz o teste **falhar**, nunca pular.

---

## 6. Como o usuário testa no Telegram

1. **Privacidade (P9, manual):** no @BotFather, `/setprivacy` → **Enable**. Remova o bot do grupo e adicione de novo, senão a mudança não vale no grupo.
2. Confira que `GEMINI_MODEL` e `GEMINI_API_KEY` estão no `.env`.
3. `docker compose up -d --build` e `docker compose logs -f bot`: deve aparecer "KALLY iniciado" e nenhuma migração nova.
4. `/r 150 g de arroz, 2 ovos e salada`: confira nomes, gramas, `+N kcal` e `total hoje`. No log, a linha do Gemini mostra a duração, sem o texto.
5. `/r 1 banana`: o total soma com o registro anterior.
6. `/r`: exemplo de uso. `/r kkkkk`: "Não identifiquei nenhum alimento".
7. `/r banana kkkkk`: registra a banana e avisa `Ignorei: kkkkk`.
8. `/r` com mais de 500 caracteres: texto de limite, sem linha do Gemini no log.
9. `/r` com quebras de linha entre os alimentos: registra normalmente.
10. Mensagem sem comando (`almocei arroz`): silêncio.
11. A outra pessoa manda `/r 1 maçã`: o total dela não mistura com o seu.
12. `/peso 82,4` e `/id`: continuam funcionando.
13. **Gemini com falha:** troque `GEMINI_MODEL` por um nome inexistente, `docker compose up -d bot`, mande um `/r` e veja o texto da RN-017. Volte o modelo certo e rode `docker compose up -d bot` de novo.
14. **Banco fora do ar:** `docker compose stop db`, mande `/r 1 banana` e `/peso 82,4`: `Não consegui confirmar o registro agora. Tente de novo em instantes.` Depois, `docker compose start db` e confirme que o bot voltou a registrar.
15. No banco, confira a refeição e os itens:
    ```bash
    docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT * FROM refeicoes ORDER BY id DESC LIMIT 3" -c "SELECT * FROM refeicao_itens ORDER BY id DESC LIMIT 5" -c "SELECT * FROM alimentos ORDER BY id DESC LIMIT 5"'
    ```

**Primeira chamada real:** os testes usam um servidor falso. Se o Gemini recusar o schema ou passar de 15 s com o modelo escolhido, isso aparece nos passos 4 e 13 e deve ser ajustado antes de aprovar.

## 7. Critérios de aceite

Seção 6 do [doc de decisões](etapa-3-decisoes.md).

## 8. Docs a atualizar

Seção 7 do [doc de decisões](etapa-3-decisoes.md), mais a instrução de `/setprivacy` no `README.md`, que contradiz P9. O status ✅, "O que funciona hoje", a remoção das pendências e o roadmap do README ficam para a aprovação do usuário.

## 9. Fluxo de trabalho

1. **`kally-python`** implementa e roda os testes no container.
2. **`kally-revisor`** revisa contra este plano e o doc de decisões.
3. **O usuário** testa pelo roteiro da seção 6 e faz o commit.

## 10. Pontos de atenção para a revisão

- O filtro de chats continua antes de qualquer chamada ao Gemini?
- Algum caminho grava algo depois de falha do Gemini ou de lista vazia?
- O texto da pessoa ou a chave aparecem no log?
- O nome da base é só normalizado, sem regra por alimento (D10, D11)?
- Os testes de banco podem, em algum caminho, tocar no `POSTGRES_DB`?
