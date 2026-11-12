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
- `/peso` sem número → responde com a última pesagem: "João: 82,4 kg em dom 01/11".
- Aceita vírgula ou ponto. Rejeita valores fora de 30 a 300 kg.
- A data da pesagem é a do envio da mensagem (como na RN-007).
- Mais de uma pesagem no mesmo dia: todas são guardadas; `/peso` mostra a mais recente.
- Não existe registro retroativo de peso (D-021). Uma pesagem errada é apagada pelo botão ❌ e registrada de novo.

### RN-013 — Comando `/r`
**Status:** decidida

A refeição só é registrada com o comando `/r <descrição>` (D-017, D-021). Todo `/r` válido chama o Gemini, que separa os itens e converte as quantidades em gramas; as calorias saem dos valores por 100 g da base de alimentos (RN-016, D-041). Depois o bot grava e responde com as calorias e o total do dia.

```
João: /r arroz, feijão, 1 bife e salada
KALLY: João: +650 kcal · total hoje: 1.420 kcal
       arroz 200 g · 260 kcal · feijão 100 g · 75 kcal · bife 120 g · 250 kcal · salada 100 g · 65 kcal
       [✏️ Corrigir] [❌ Apagar]
```

- `/r` sem descrição → "Descreva o que comeu, ex.: /r 150 g de arroz e 1 filé de frango".
- A descrição tem **limite de 500 caracteres** (D-037), contados depois de reduzir os espaços repetidos e remover as linhas vazias. Acima disso, nada é registrado e o Gemini não é chamado: "Descrição muito longa. Use até 500 caracteres."
- A descrição é guardada como a pessoa escreveu, sem essa limpeza.
- **Cada `/r` é um registro só** (D-022), mesmo que descreva várias coisas ou várias refeições. O bot não pergunta nem guarda se foi café, almoço ou jantar.
- Se o Gemini não reconhecer nenhum alimento, o bot não registra e pede para descrever melhor.
- **Mensagem sem comando** → o bot fica em silêncio, para o grupo poder conversar (D-036).
- Quando a mensagem é de outro dia (enviada antes da meia-noite e processada depois), a resposta mostra `total de 31/10` no lugar de `total hoje` (RN-007).
- **Banco fora do ar** durante `/r` ou `/peso` → "Não consegui confirmar o registro agora. Tente de novo em instantes." O texto não afirma que nada foi registrado, porque a confirmação da gravação pode se perder com a refeição já gravada.
- **Erro inesperado** fora de banco durante `/r` ou `/peso` → "Algo deu errado. Tente de novo em instantes." O erro vai para o log (D-040).

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
**Status:** decidida (D-041 a D-044)

O bot guarda as calorias e os macros **por 100 g** de cada alimento que já viu. Todo `/r` chama o Gemini, que separa os itens e converte as quantidades em gramas; quando o alimento já está na base, os valores por 100 g vêm dela, não do Gemini (D-041). Assim, o mesmo alimento tem sempre as mesmas calorias por 100 g. A base começa vazia (D-027) e não tem comando para ser consultada ou corrigida; correções são feitas direto no banco (D-028).

**O que a base guarda, por alimento:**

| Campo | Exemplo |
|---|---|
| nome | arroz |
| kcal por 100 g | 130 |
| proteína, carbo e gordura por 100 g | 2,5 · 28 · 0,3 |
| porção padrão (só referência, D-044) | 1 colher de servir = 45 g |
| origem | ia |

**Como um registro é calculado:**

1. A descrição limpa (RN-013) vai inteira ao Gemini, numa chamada.
2. O Gemini separa a descrição em itens e devolve, para cada um:
   - **nome:** o que o Gemini devolve seguindo o prompt atual (as palavras da pessoa, no singular, sem quantidade). Quando ele corrige a grafia ou tira o tamanho mesmo assim (`pichanha` → `picanha assada`; `goiabas grandes` → `goiaba`), o resultado é aceito (D-043);
   - **gramas:** a quantidade convertida em gramas, seja qual for a medida: `150 g`, `0,2 kg`, `300 ml` (ml conta como g), `2 ovos`, `2 colheres de arroz`, `1 concha de feijão`, `2 fatias`, `meia pizza`, `banana grande`. Sem quantidade (`salada`), ele estima uma porção típica. A quantidade escrita pela pessoa sempre vale;
   - **valores por 100 g** e a **porção padrão**, considerando o alimento já preparado, na forma em que é comido: "arroz" é arroz cozido (D-031).
3. O bot valida a resposta (abaixo). Um item inválido cancela tudo (RN-017).
4. O bot normaliza o nome para a base (minúsculo, sem acento, sem espaços nas pontas) e procura por ele. Não há apelidos (D-030): "arroz" e "arroz branco" são alimentos diferentes.
5. **Alimento já na base:** a base vence. Ela nunca é sobrescrita, e o item usa os valores por 100 g dela com os gramas do Gemini.
6. **Alimento novo:** entra na base com os valores do Gemini, e a conta segue igual.
7. **Conta de cada item:** `kcal = kcal por 100 g × gramas ÷ 100`, arredondada para inteiro; macros com 1 casa. O total da refeição é a soma dos itens.
8. **Trecho que não é comida no meio da descrição:** o Gemini o devolve à parte, os alimentos reconhecidos são registrados e a resposta avisa: `Ignorei: kkkk` (D-039).

**A porção padrão não entra na conta** (D-044). Ela é pedida, validada e gravada só como referência.

**Na resposta**, cada item mostra o nome e os gramas usados (`bife 120 g · 250 kcal`), para que a pessoa veja na hora se a conversão não bate com o que comeu e corrija. Não há indicação de unidades, como "(2 un.)".

**Casos de borda:**
- O mesmo texto pode dar gramas um pouco diferentes em dias diferentes, porque os gramas sempre vêm do Gemini. As calorias por 100 g do alimento já conhecido não mudam.
- O Gemini pode dar nomes diferentes para o mesmo alimento em dias diferentes ("picanha" e "picanha assada"), o que cria duplicatas na base. Risco aceito (D-030, D-043).
- O Gemini pode completar o nome ("pão" → "pão francês"), e isso entra na base. Risco aceito; a resposta mostra o nome, e a correção da base é direto no banco (D-028, D-043).
- Gemini fora do ar impede qualquer `/r`, mesmo de alimentos já conhecidos (RN-017).

**Validação do que vem do Gemini**, antes de entrar na base:
- kcal por 100 g entre 0 e 900 (nenhum alimento passa disso; óleo puro tem ~880);
- os macros precisam bater com as calorias: a diferença entre 4 × proteína + 4 × carbo + 9 × gordura e as kcal pode ser de até 20% das kcal, com mínimo de 10 kcal. Bebidas alcoólicas dispensam essa conta, porque o álcool tem calorias fora dos macros (D-038);
- cada macro entre 0 e 100 g por 100 g, em todo alimento, inclusive bebidas alcoólicas (D-040);
- gramas do item e porção padrão maiores que zero e de até 10.000 g, com o limite exato aceito (D-040);
- nome, trecho e porção preenchidos, sem o caractere NUL.

Se um item não passar, a resposta inteira conta como inválida (RN-017). Isso vale também para a porção padrão, mesmo ela não entrando na conta: é uma desvantagem aceita (D-044).

### RN-017 — Falha do Gemini
**Status:** decidida (D-045, D-047, D-048; premissas da [etapa 4](etapas/etapa-4-decisoes.md) confirmadas em 10/11/2026)

**Decidido:**
- Se o Gemini der erro, demorar demais ou devolver algo inválido (RN-016), o bot **não registra nada**.
- Nas **falhas passageiras**, o bot tenta de novo sozinho antes de responder (D-045).
- Se ainda assim falhar, a mensagem de falha traz o botão **🔄 Tentar de novo**, que repete o pedido sem a pessoa precisar reenviar o texto (D-045).
- Não há modelo reserva (D-045).

**Detalhes (D-048):**
- **Falhas passageiras** são: erro do servidor do Gemini (5xx, 503), limite de requisições (429), tempo esgotado e falha de conexão. Resposta fora do schema e item inválido **não** são repetidos automaticamente, porque tendem a dar o mesmo erro (com `temperature=0`); para eles, só o botão.
- Até **3 tentativas** no total, com esperas de 2 s e 5 s entre elas, cada uma com **15 s** de limite e todas dentro de **40 s** no total. Se sobrarem menos de 5 s, o bot não começa outra tentativa.
- Enquanto tenta, o bot mostra "digitando…" no grupo.
- Os outros comandos (`/peso`, o `/r` da outra pessoa) esperam na fila até o `/r` em andamento terminar (D-047).
- A mensagem de falha:

  > Não consegui estimar agora. Nada foi registrado.
  > [🔄 Tentar de novo]

- O botão só aparece na falha do Gemini. Não aparece em banco fora do ar, descrição vazia, descrição longa demais ou "nenhum alimento".
- Ao apertar, a mensagem vira "Tentando de novo…", sem o botão, e o bot faz o mesmo processo do `/r`, inclusive as novas tentativas automáticas.
- **Deu certo:** a mensagem de falha é editada e vira a resposta normal do registro.
- **Falhou de novo:** a mensagem volta a ser a de falha, com o botão.
- **Data da refeição:** vale o horário de envio do `/r` original (RN-007), não o do clique. Se for de outro dia, a resposta mostra `total de 09/11`, como hoje.
- **Só quem mandou o `/r`** pode apertar. Para outra pessoa, o bot avisa só para ela, sem mensagem nova no grupo: "Só João pode tentar de novo."
- O pedido pendente fica **em memória**. Se o bot reiniciar, ou se passarem 7 dias do `/r` original, o botão responde "Esse pedido expirou. Mande o /r de novo." e some.
- Apertar duas vezes seguidas registra uma vez só.

**Casos de borda:**
- O banco cai depois de o Gemini responder, durante um clique no botão: vale a resposta de banco fora do ar (RN-013), e o pedido pendente não volta, para não arriscar registro em dobro.
- Pelo botão, o Gemini responde que não há alimento: vale a resposta "Não identifiquei nenhum alimento...", sem botão.
- A pessoa reenvia o `/r` em vez de apertar o botão: são dois pedidos independentes; o botão antigo continua valendo e, se usado, registra de novo. Aceito: a resposta mostra o registro, e a exclusão vem com os botões (RN-015).

---

## Em aberto

- **Detalhes da RN-017** (novas tentativas e botão "Tentar de novo"): premissas P1 a P13 da [etapa 4](etapas/etapa-4-decisoes.md#2-premissas-a-confirmar), com a recomendação em cada uma.

### Resolvidas ou descartadas
- **Q-001** (como saber se a mensagem é refeição): resolvida por D-017 (registro por comando).
- **Q-002** (refeição registrada depois do horário): resolvida por RN-007 e RN-014.
- **Q-003** (como corrigir ou desfazer): resolvida por D-019 e RN-015.
- **Q-008**, **Q-009**, **Q-010** (peso de tendência, recomposição, metas): fora do escopo por D-012.
- **Q-011** (como os dados saem do bot): resolvida por D-016.
- **Q-012**, **Q-013** (`/dia` e semana): resolvidas por D-020.
- **Q-005** (várias refeições numa mensagem): resolvida por D-022 (um registro só).
- **Q-015**, **Q-016** (nome do comando e limites do retroativo): resolvidas por D-021.
- **Q-004** (falha do Gemini): resolvida por D-023 e RN-017; revista por D-045 (nova tentativa automática e botão).
- **Q-006** (exclusão de dados): fora do MVP por D-025.
- **Q-007** (consistência do Gemini): os usuários já testaram e acharam consistente; a base de alimentos reforça isso, fixando os valores por 100 g de cada alimento (D-041).
- **Q-014** (pesagens no CSV): resolvida por D-024.
- **Q-017** (base inicial): começa vazia, por D-027.
- **Q-018** (corrigir a base): sem comando no MVP, por D-028.
