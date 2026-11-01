# KALLY — Regras de negócio

Fonte da verdade para o comportamento do bot. Decisões técnicas e arquitetura ficam em [`bot-dieta-planejamento.md`](bot-dieta-planejamento.md); o histórico de todas as decisões, em [`decisoes.md`](decisoes.md).

**Status:** `decidida` (confirmada pelo time) · `proposta` (sugerida, aguardando decisão) · `descartada`

**Escopo (D-012, D-013, D-022):** o KALLY coleta dados. Registra refeições com calorias e macros estimados, registra o peso, e entrega os dados para que os usuários façam suas próprias análises. Ele não calcula gasto calórico, não sugere metas e não distingue tipo de refeição (café, almoço, jantar): só as calorias importam.

Exemplos de conversa com o bot, cobrindo cada regra: [`exemplos.md`](exemplos.md).

## Comandos

| Comando | Função | Regra |
|---|---|---|
| `/r <descrição>` | Registra uma refeição agora | RN-013 |
| `/retro <data> [hora] <descrição>` | Registra uma refeição no passado | RN-014 |
| `/dia` | Refeições e total de hoje | RN-009 |
| `/semana` | Total de cada dia da semana | RN-010 |
| `/peso [kg]` | Registra ou consulta o peso | RN-012 |
| `/exportar [dias]` | CSV com o histórico (ou os últimos N dias) | RN-011 |
| `/id` | ID do chat (configuração) | RN-002 |

---

## Regras

### RN-001 — Fuso horário do dia
**Status:** decidida

O "dia" de cada participante vai de 00:00 a 23:59:59 no horário de `America/Sao_Paulo`. Os totais diários sempre usam esse intervalo.

- Exemplo: refeição registrada às 22h de segunda → conta no total de segunda (não de terça, como seria em UTC).

### RN-002 — Grupos autorizados
**Status:** decidida

O bot só responde em chats listados em `ALLOWED_CHAT_IDS`. Em qualquer outro chat, ignora as mensagens (exceto `/id`, para descobrir o ID).

### RN-003 — Registro de peso (versão com tendência)
**Status:** descartada (substituída por RN-012)

### RN-004 — Peso de tendência
**Status:** descartada (D-012)

### RN-005 — Dia completo
**Status:** descartada (D-015: nada de marcação manual)

### RN-006 — Gasto calórico estimado
**Status:** descartada (D-012: o cálculo é feito pelos usuários, fora do bot)

> Nota para quem for calcular: um erro do Gemini que seja sempre na mesma direção se cancela nesse tipo de conta. Se ele superestima tudo em 10%, o gasto calculado sai 10% maior também, e o déficit continua correto. Por isso, **consistência importa mais que precisão** (ver Q-007).

### RN-007 — Horário da refeição
**Status:** decidida

A refeição registrada com `/r` vale pelo horário em que a mensagem foi **enviada** no Telegram (não o horário em que o bot processou). É esse horário que define em qual dia ela conta (RN-001). A única exceção é o registro retroativo (RN-014).

- Exemplo: mensagem enviada às 23:58 e processada às 00:02 (bot reiniciando) → conta no dia anterior.

### RN-008 — Toda mensagem de texto é uma refeição
**Status:** descartada (D-017: registro só por comando)

### RN-009 — Comando `/dia`
**Status:** decidida

Mostra as refeições de hoje de quem pediu, com horário e calorias, e o total do dia. Só o dia de hoje (D-020).

```
João · hoje (01/11)
08:12  pão com ovo e café           320 kcal
12:40  arroz, feijão, bife, salada  650 kcal
16:05  banana                       90 kcal
Total: 1.060 kcal · P 62 g · C 128 g · G 31 g
```

### RN-010 — Comando `/semana`
**Status:** decidida

Mostra o total de calorias de cada dia da semana de quem pediu, de **segunda a domingo** (D-020), com o total e a média.

```
João · semana 26/10 a 01/11
Seg 26  2.140 kcal
Ter 27  1.980 kcal
Qua 28  2.310 kcal
Qui 29  —
Sex 30  2.050 kcal
Sáb 31  2.240 kcal
Dom 01  1.060 kcal  (hoje)
Total: 11.780 kcal · média: 1.963 kcal/dia (6 dias com registro)
```

- Dias sem nenhum registro aparecem como "—" e ficam fora da média.
- No meio da semana, os dias que ainda não chegaram não aparecem.

### RN-011 — Comando `/exportar`
**Status:** decidida

Manda no chat um arquivo CSV com o histórico dos **dois participantes**, com **uma linha por refeição** (D-020).

- `/exportar` → todo o histórico.
- `/exportar 30` → os últimos 30 dias, contando hoje (D-021). Aceita de 1 a 3650.
- O nome do arquivo diz o período: `kally_2026-10-03_a_2026-11-01.csv`.

| Coluna | Exemplo |
|---|---|
| data | 2026-10-28 |
| hora | 20:00 |
| pessoa | João |
| descricao | 2 fatias de pizza de calabresa |
| kcal | 540 |
| proteina_g | 22 |
| carbo_g | 58 |
| gordura_g | 24 |
| retroativo | sim |
| registrado_em | 2026-10-29 09:15 |

- Formato pensado para abrir direto no Excel em português: separador `;`, vírgula decimal, UTF-8 com BOM.
- Refeições apagadas (RN-015) não aparecem.
- Junto vai um **segundo arquivo só com as pesagens** (D-024), com o mesmo período e o mesmo formato: `kally_pesos_2026-10-03_a_2026-11-01.csv`.

| Coluna | Exemplo |
|---|---|
| data | 2026-11-01 |
| hora | 07:15 |
| pessoa | João |
| peso_kg | 82,4 |

### RN-012 — Comando `/peso`
**Status:** decidida

Registra e consulta o peso. É só armazenamento: não há cálculo nem relação com as calorias (D-013).

- `/peso 82,4` → registra e responde: "João: 82,4 kg registrado (anterior: 83,1 kg em 28/10)".
- `/peso` sem número → responde com a última pesagem: "João: 82,4 kg em 01/11".
- Aceita vírgula ou ponto. Rejeita valores fora de 30 a 300 kg.
- A data da pesagem é a do envio da mensagem (como na RN-007).
- Mais de uma pesagem no mesmo dia: todas são guardadas; `/peso` mostra a mais recente.
- Não existe registro retroativo de peso (D-021). Uma pesagem errada é apagada pelo botão ❌ e registrada de novo.

### RN-013 — Comando `/r`
**Status:** decidida

A refeição só é registrada com o comando `/r <descrição>` (D-017, D-021). O bot calcula as calorias pela base de alimentos e só chama o Gemini para o que a base não conhece (RN-016). Depois grava e responde com as calorias e o total do dia.

```
João: /r arroz, feijão, 1 bife e salada
KALLY: João: +650 kcal · total hoje: 1.420 kcal
       arroz 200 kcal · feijão 140 kcal · bife 250 kcal · salada 60 kcal
       [✏️ Corrigir] [❌ Apagar]
```

- `/r` sem descrição → "Descreva o que comeu, ex.: /r 150 g de arroz e 1 filé de frango".
- **Cada `/r` é um registro só** (D-022), mesmo que descreva várias coisas ou várias refeições. O bot não pergunta nem guarda se foi café, almoço ou jantar.
- Se o Gemini não reconhecer nenhum alimento, o bot não registra e pede para descrever melhor.
- **Mensagem sem comando** → o bot responde uma vez: "Para registrar, use /r seguido do que comeu". Assim ninguém acha que registrou quando esqueceu o comando (proposta).

### RN-014 — Registro retroativo
**Status:** decidida

O comando `/retro` registra uma refeição em data passada (D-018). É a única exceção à RN-007.

- `/retro ontem jantei pizza` → conta em ontem.
- `/retro 28/10 20:00 2 fatias de pizza` → conta em 28/10 às 20:00.
- Sem hora → a refeição fica sem horário (aparece como `--:--` no `/dia` e vazia no CSV).
- A data pode ser `ontem`, `anteontem` ou `DD/MM`.
- Limite: até **7 dias atrás** (D-021). Não aceita data futura nem o dia de hoje (para hoje, use `/r`).
- Só para refeições; peso não tem retroativo (D-021).
- A resposta deixa claro em qual dia entrou: "João: +540 kcal em 28/10 (retroativo) · total de 28/10: 2.590 kcal".
- O registro guarda a data em que foi feito, e o CSV marca a refeição como retroativa (RN-011).

### RN-015 — Correção e exclusão por botões
**Status:** decidida (o fluxo detalhado é proposta)

Toda resposta de registro (`/r`, `/retro`, `/peso`) traz botões (D-019):

- **✏️ Corrigir:** o bot pede uma nova descrição; a pessoa responde à mensagem do bot; o Gemini estima de novo e o registro é atualizado. Se a pessoa responder só com um número (ex.: `450`), as calorias são trocadas por esse valor sem chamar o Gemini, e os macros são ajustados na mesma proporção.
- **❌ Apagar:** remove o registro e responde com o novo total do dia.
- **Só quem fez o registro** pode usar os botões dele. Se outra pessoa apertar, o bot avisa: "Só João pode alterar este registro".
- Os botões ficam ativos por **7 dias** (o mesmo limite do retroativo).
- **❌ Apagar pede confirmação** antes: "Apagar "banana" (90 kcal)? [Sim, apagar] [Cancelar]". Confirmado, o registro é removido de vez do banco (D-033); não há como desfazer.
- Corrigir um registro **não altera a base de alimentos** (RN-016). Se a pessoa corrigir só as calorias, vale só para aquele registro. A base só é corrigida direto no banco (D-028).

### RN-016 — Base de alimentos
**Status:** decidida (o funcionamento detalhado é proposta)

O bot guarda as calorias e os macros **por 100 g** de cada alimento que já viu, e só usa o Gemini para alimentos novos (D-026). A base começa vazia (D-027) e não tem comando para ser consultada ou corrigida; correções são feitas direto no banco (D-028).

**O que a base guarda, por alimento:**

| Campo | Exemplo |
|---|---|
| nome | arroz branco cozido |
| kcal por 100 g | 130 |
| proteína, carbo e gordura por 100 g | 2,5 · 28 · 0,3 |
| porção padrão | 1 colher de servir = 45 g |
| origem | ia |

**Como um registro é calculado:**

1. O bot separa a descrição em itens, por vírgula, "e", "+" ou quebra de linha: `150 g de arroz, 1 bife e salada` → `150 g de arroz` · `1 bife` · `salada`.
2. Em cada item, separa a quantidade do alimento:
   - com peso ou volume (`150 g`, `0,2 kg`, `300 ml`): usa esse valor (ml conta como g);
   - com número de unidades (`1 bife`, `2 ovos`): número × porção padrão;
   - sem quantidade (`salada`): 1 porção padrão.
3. Normaliza o nome do alimento como a pessoa escreveu (minúsculo, sem acento, singular): `2 Ovos` → `ovo`. Procura na base por esse nome. Não há apelidos (D-030): "arroz" e "arroz branco" são alimentos diferentes.
4. **Todos encontrados:** a conta é feita localmente, sem IA: `kcal = kcal por 100 g × gramas ÷ 100`.
5. **Algum não encontrado:** só esses itens vão ao Gemini, que devolve os valores por 100 g, a porção padrão e os gramas estimados. O alimento entra na base com o nome que a pessoa escreveu, não com um nome dado pelo Gemini (D-034). O Gemini considera o alimento já preparado, na forma em que é comido: "arroz" é arroz cozido (D-031). Os alimentos novos entram na base, e a conta segue igual.
6. **O bot não consegue separar a descrição:** a mensagem inteira vai ao Gemini, que devolve os itens já separados, e os alimentos novos entram na base.

**Na resposta**, cada item mostra os gramas usados (`bife 120 g · 250 kcal`), para que a pessoa veja na hora se a porção padrão não bate com o que comeu e corrija.

**Validação do que vem do Gemini**, antes de entrar na base:
- kcal por 100 g entre 0 e 900 (nenhum alimento passa disso; óleo puro tem ~880);
- os macros precisam bater com as calorias (4 × proteína + 4 × carbo + 9 × gordura, com margem de 20%).

Se não passar, conta como resposta inválida (RN-017).

### RN-017 — Falha do Gemini
**Status:** decidida

Se o Gemini não responder em **15 segundos**, der erro (cota, fora do ar) ou devolver algo inválido (RN-016), o bot **não registra nada** e responde:

> Não consegui estimar agora. Nada foi registrado, tente de novo em instantes.

- Não há nova tentativa automática (D-023).
- Registros calculados só pela base continuam funcionando com o Gemini fora do ar.

---

## Em aberto

Nenhuma questão em aberto: as regras do MVP estão fechadas.

### Resolvidas ou descartadas
- **Q-001** (como saber se a mensagem é refeição): resolvida por D-017 (registro por comando).
- **Q-002** (refeição registrada depois do horário): resolvida por RN-007 e RN-014.
- **Q-003** (como corrigir ou desfazer): resolvida por D-019 e RN-015.
- **Q-008**, **Q-009**, **Q-010** (peso de tendência, recomposição, metas): fora do escopo por D-012.
- **Q-011** (como os dados saem do bot): resolvida por D-016.
- **Q-012**, **Q-013** (`/dia` e semana): resolvidas por D-020.
- **Q-005** (várias refeições numa mensagem): resolvida por D-022 (um registro só).
- **Q-015**, **Q-016** (nome do comando e limites do retroativo): resolvidas por D-021.
- **Q-004** (falha do Gemini): resolvida por D-023 e RN-017.
- **Q-006** (exclusão de dados): fora do MVP por D-025.
- **Q-007** (consistência do Gemini): os usuários já testaram e acharam consistente; a base de alimentos (D-026) reforça isso.
- **Q-014** (pesagens no CSV): resolvida por D-024.
- **Q-017** (base inicial): começa vazia, por D-027.
- **Q-018** (corrigir a base): sem comando no MVP, por D-028.
