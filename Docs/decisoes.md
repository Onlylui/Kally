# KALLY — Registro de decisões

Diário de bordo do projeto: cada decisão importante, quando foi tomada, por quê, e o que ficou de fora. Serve para ninguém precisar re-discutir o que já foi resolvido, e para saber o que revisar quando o contexto mudar.

- Regras de comportamento do bot: [`regras-de-negocio.md`](regras-de-negocio.md)
- Arquitetura e stack: [`bot-dieta-planejamento.md`](bot-dieta-planejamento.md)

**Como usar:** decisões nunca são apagadas. Se uma mudar, a antiga vira `substituída por D-XXX` e entra uma nova.

---

## Resumo

| ID | Data | Decisão | Tipo | Status |
|---|---|---|---|---|
| D-001 | 2026-11-01 | Telegram como plataforma (WhatsApp descartado) | Produto | vigente |
| D-002 | 2026-11-01 | Python + `python-telegram-bot` | Técnica | vigente |
| D-003 | 2026-11-01 | Gemini via `google-genai`, modelo configurável no `.env` | Técnica | vigente |
| D-004 | 2026-11-01 | PostgreSQL 16 | Técnica | vigente |
| D-005 | 2026-11-01 | Polling em vez de webhook | Técnica | vigente |
| D-006 | 2026-11-01 | Sem Django por enquanto | Técnica | vigente |
| D-007 | 2026-11-01 | Deploy com Docker Compose | Técnica | vigente |
| D-008 | 2026-11-01 | Dia contado no fuso de São Paulo (RN-001) | Negócio | vigente |
| D-009 | 2026-11-01 | Bot restrito a grupos autorizados (RN-002) | Negócio | vigente |
| D-010 | 2026-11-01 | Objetivo: descobrir o gasto calórico real de cada um a partir dos dados | Produto | substituída por D-012 |
| D-011 | 2026-11-01 | Calorias diárias e semanais são a métrica principal; macros são secundários | Produto | vigente |
| D-012 | 2026-11-01 | Escopo: o KALLY só conta calorias; o cálculo do gasto fica com os usuários | Produto | vigente (peso: ver D-013) |
| D-013 | 2026-11-01 | Peso entra como registro simples, sem cruzar com as calorias | Produto | vigente |
| D-014 | 2026-11-01 | O grupo é exclusivo do bot e funciona como vigilância mútua | Produto | vigente |
| D-015 | 2026-11-01 | Nada de marcação manual: a refeição vale pelo horário da mensagem | Negócio | vigente |
| D-016 | 2026-11-01 | Consulta rápida por `/dia` e `/semana`; análise detalhada por CSV | Produto | vigente |
| D-017 | 2026-11-01 | Refeição só é registrada por comando, não por mensagem livre | Negócio | vigente |
| D-018 | 2026-11-01 | Registro retroativo de refeições por comando próprio | Negócio | vigente |
| D-019 | 2026-11-01 | Correção e exclusão por botões embaixo da resposta do bot | Produto | vigente |
| D-020 | 2026-11-01 | `/dia` só de hoje; semana de segunda a domingo; CSV com os dois, uma linha por refeição | Produto | vigente |
| D-021 | 2026-11-01 | Comando `/r`; retroativo até 7 dias e só para refeições; `/exportar` aceita período | Produto | vigente |
| D-022 | 2026-11-01 | Sem tipo de refeição: uma mensagem é um registro, só as calorias importam | Negócio | vigente |
| D-023 | 2026-11-01 | Falha do Gemini: só mensagem de erro, sem nova tentativa e sem registro | Negócio | substituída por D-045 |
| D-024 | 2026-11-01 | `/exportar` manda um segundo CSV só com as pesagens | Produto | vigente |
| D-025 | 2026-11-01 | Exclusão de todos os dados de uma pessoa fica fora do MVP | Produto | vigente |
| D-026 | 2026-11-01 | Base própria de alimentos (kcal/100 g); a IA só é chamada para o que não está na base | Técnica | substituída por D-041 |
| D-027 | 2026-11-01 | A base de alimentos começa vazia e aprende com o Gemini | Técnica | vigente (consequência revista em D-041) |
| D-028 | 2026-11-01 | Sem comando para ver ou corrigir a base no MVP | Produto | vigente |
| D-029 | 2026-11-01 | Itens da refeição numa tabela própria (`refeicao_itens`), não em JSONB | Técnica | vigente |
| D-030 | 2026-11-01 | Sem apelidos de alimentos no MVP: a busca é só pelo nome | Técnica | vigente (consequência revista em D-041) |
| D-031 | 2026-11-01 | O Gemini considera os alimentos já preparados (cozido, grelhado, assado) | Técnica | vigente |
| D-032 | 2026-11-01 | Limitações aceitas no MVP: base compartilhada, total da refeição prevalece, sem histórico de correção | Técnica | vigente |
| D-033 | 2026-11-01 | Apagar remove o registro de verdade (`DELETE`), depois de confirmação | Técnica | vigente |
| D-034 | 2026-11-01 | O nome do alimento na base é o texto que a pessoa escreveu, não o nome dado pelo Gemini | Técnica | substituída por D-043 |
| D-035 | 2026-11-02 | Tudo roda em Docker, também no desenvolvimento; sem execução local | Técnica | vigente |
| D-036 | 2026-11-04 | Mensagem sem comando recebe silêncio, sem aviso | Produto | vigente |
| D-037 | 2026-11-04 | Descrição do `/r` limitada a 500 caracteres | Negócio | vigente |
| D-038 | 2026-11-04 | Coerência de macros com margem de 20% (mínimo de 10 kcal); bebida alcoólica dispensa | Técnica | vigente |
| D-039 | 2026-11-04 | Lixo misturado aos alimentos é ignorado com aviso, sem cancelar o registro | Negócio | vigente |
| D-040 | 2026-11-05 | Tetos de 10.000 g e de 100 g de macro por 100 g na resposta do Gemini; resposta para erro inesperado | Negócio | vigente |
| D-041 | 2026-11-10 | Sem parser local: o Gemini sempre separa os itens e converte as medidas em gramas; a base fornece os valores por 100 g | Técnica | vigente |
| D-042 | 2026-11-10 | Sem cache de resposta por linha e sem os nomes da base no prompt | Técnica | vigente |
| D-043 | 2026-11-10 | O nome do alimento é o que o Gemini devolve com o prompt atual; correções de grafia são aceitas | Técnica | vigente |
| D-044 | 2026-11-10 | A porção padrão continua sendo pedida, validada e gravada, só como referência | Técnica | vigente |
| D-045 | 2026-11-10 | Falha passageira do Gemini: nova tentativa automática e botão "Tentar de novo" | Negócio | vigente |
| D-046 | 2026-11-10 | Novo roteiro: etapa 4 vira resiliência do Gemini; `/dia` e `/semana` se separam | Produto | vigente |
| D-047 | 2026-11-10 | Os updates continuam em fila (um por vez); chamadas paralelas ficam para o futuro | Técnica | vigente |
| D-048 | 2026-11-10 | Detalhes da resiliência do Gemini: 3 tentativas, 15 s cada, 40 s no total, botão só do dono, 7 dias | Negócio | vigente |

---

## Detalhes

### D-001 — Telegram como plataforma
- **Contexto:** o bot precisa ler mensagens de um grupo com duas pessoas.
- **Decisão:** Telegram.
- **Alternativas descartadas:** WhatsApp. A API oficial de grupos exige conta Business verificada e limita a 8 participantes; bibliotecas não oficiais violam os termos e arriscam banimento do número.
- **Revisar se:** o grupo precisar incluir alguém que não usa Telegram.

### D-002 — Python + `python-telegram-bot`
- **Decisão:** Python 3.12 com `python-telegram-bot` v20+ (assíncrono).
- **Motivo:** linguagem que o time quer usar; biblioteca madura e com boa documentação.

### D-003 — Gemini via `google-genai`
- **Decisão:** estimativa de calorias e macros com o Gemini, pelo SDK `google-genai`. O nome do modelo fica no `.env` (`GEMINI_MODEL`).
- **Motivo:** o SDK antigo (`google-generativeai`) foi descontinuado; o Google troca versões de modelo com frequência, então trocar não pode exigir mudar código.
- **Ponto de atenção:** no plano gratuito, os dados enviados podem ser usados pelo Google. São dados de saúde (leves).

### D-004 — PostgreSQL 16
- **Decisão:** PostgreSQL, com tabelas `usuarios` e `refeicoes` (ver planejamento).

### D-005 — Polling em vez de webhook
- **Decisão:** o bot pergunta ao Telegram por mensagens novas.
- **Motivo:** dispensa porta aberta, IP fixo, domínio e HTTPS; roda até em servidor caseiro.
- **Revisar se:** o volume de mensagens crescer muito ou o bot for para uma hospedagem serverless.

### D-006 — Sem Django por enquanto
- **Motivo:** evitar aprender muita coisa ao mesmo tempo.
- **Revisar se:** surgir a necessidade de painel ou site.

### D-007 — Docker Compose
- **Decisão:** dois serviços (`db` e `bot`), com `restart: unless-stopped` e healthcheck no Postgres.
- **Motivo:** roda igual na VPS e no servidor caseiro.

### D-008 — Dia no fuso de São Paulo
- **Decisão:** ver [RN-001](regras-de-negocio.md#rn-001--fuso-horário-do-dia).
- **Motivo:** em UTC, uma refeição das 22h cairia no dia seguinte.

### D-009 — Grupos autorizados
- **Decisão:** ver [RN-002](regras-de-negocio.md#rn-002--grupos-autorizados).
- **Motivo:** impedir que o bot seja usado em outros grupos e gaste a cota do Gemini.

### D-010 — Objetivo do produto
> **Substituída por D-012.** O objetivo das pessoas continua o mesmo, mas o cálculo do gasto saiu do bot.

- **Contexto:** os participantes querem saber se estão emagrecendo ou fazendo recomposição corporal, mas não registram nada hoje. Sabem as gramas do que comem, mas não sabem como ajustar a dieta conforme os resultados aparecem.
- **Decisão:** o KALLY existe para **descobrir o gasto calórico real de cada pessoa** cruzando o que ela come com a evolução do corpo, e para manter um **histórico diário** que permita analisar a jornada com dados.
- **Critério de sucesso:** o gasto calórico calculado bate com a realidade. Se o bot diz que a pessoa ficou em déficit, ela de fato emagreceu.
- **Restrição:** o registro precisa ter o mínimo de esforço manual.
- **Consequência:** só registrar refeições não basta. Sem o peso, não há como medir o resultado nem calcular o gasto (ver RN-003 a RN-005).

### D-011 — Calorias como métrica principal
- **Decisão:** o total de calorias por dia e por semana é o número central do produto. Proteína, carboidrato e gordura são registrados e exibidos, mas ficam em segundo plano.
- **Consequência:** consistência no registro das calorias vale mais do que precisão nos macros.

### D-012 — Escopo: só contagem de calorias
- **Contexto:** depois de D-010, o bot foi pensado para registrar peso e calcular o gasto calórico (RN-003, RN-004, RN-006). Os usuários preferem fazer esse cálculo por conta própria.
- **Decisão:** o KALLY é uma **ferramenta de coleta de dados**: registra refeições, estima calorias (e macros) e mantém o histórico diário e semanal confiável. Peso, gasto calórico e metas ficam fora do bot.
- **Alternativas descartadas:** registro de peso, peso de tendência e cálculo do gasto dentro do bot.
- **Consequência:** a qualidade e a disponibilidade dos dados passam a ser o centro do produto. Os usuários precisam conseguir tirar os dados do bot para analisar (ver Q-011), e dias com registro incompleto precisam ser identificáveis (RN-005).
- **Revisar se:** o cálculo manual ficar trabalhoso a ponto de valer automatizar.

### D-013 — Registro de peso
- **Contexto:** D-012 deixou o peso fora do bot. Os usuários querem guardar a evolução do peso mesmo assim.
- **Decisão:** o bot registra pesagens com `/peso` (RN-012). É só armazenamento: o bot não cruza peso com calorias, não calcula tendência nem gasto.
- **Alternativas descartadas:** peso de tendência e cálculo do gasto (RN-004 e RN-006, descartadas).

### D-014 — Grupo exclusivo e vigilância mútua
- **Decisão:** o grupo existe só para o bot. Todos veem os registros e totais de todos.
- **Motivo:** saber que o outro está registrando dá motivação. A visibilidade é uma funcionalidade, não um problema de privacidade.
- **Consequência:** ~~toda mensagem de texto pode ser tratada como refeição (RN-008)~~. Revisto em D-017: o registro passou a ser por comando.

### D-015 — Sem marcação manual do dia
- **Contexto:** foi proposto o bot perguntar às 22h se o dia estava completo (RN-005).
- **Decisão:** nada de pergunta nem marcação manual. Cada refeição vale pelo horário em que a mensagem foi enviada (RN-007).
- **Motivo:** o registro tem que ser automático, com o mínimo de esforço.
- **Consequência:** dias com registro incompleto não ficam marcados; quem analisa identifica pelo número e pelo horário das refeições no CSV.

### D-016 — Consulta rápida e exportação
- **Decisão:** `/dia` e `/semana` respondem no chat com os totais (RN-009, RN-010). `/exportar` manda um CSV para análises detalhadas (RN-011).
- **Alternativas descartadas no MVP:** acesso direto ao Postgres e sincronização com Google Sheets.

### D-017 — Registro só por comando
- **Contexto:** RN-008 tratava toda mensagem de texto como refeição.
- **Decisão:** a refeição só é registrada com um comando explícito (RN-013). Mensagem livre não gera registro.
- **Motivo:** evitar registros errados.
- **Alternativas descartadas:** toda mensagem é refeição (RN-008) e classificação pelo Gemini (Q-001, opção A).
- **Consequência:** nenhuma chamada ao Gemini é desperdiçada com conversa.

### D-018 — Registro retroativo
- **Contexto:** pela RN-007, a refeição conta no dia em que a mensagem foi enviada. Quem esquece de registrar não tinha como lançar no dia certo.
- **Decisão:** um comando próprio registra refeições em data passada (RN-014). É a única exceção à RN-007.
- **Consequência:** cada refeição guarda duas datas: quando foi comida e quando foi registrada. Assim a análise distingue o registro feito na hora do retroativo.

### D-019 — Correção por botões
- **Decisão:** cada registro tem botões embaixo da resposta do bot para corrigir e apagar (RN-015).
- **Alternativas descartadas:** comandos `/corrigir` e `/desfazer`.
- **Motivo:** permite corrigir qualquer registro, não só o último, sem decorar comandos.

### D-020 — Detalhes da consulta e da exportação
- **Decisão:** `/dia` mostra só o dia de hoje (Q-012). A semana do `/semana` vai de segunda a domingo (Q-013). O CSV traz os dois participantes, com uma linha por refeição (Q-014).

### D-021 — Nome do comando, limites do retroativo e período da exportação
- **Decisão:**
  - O comando de registro é `/r` (Q-015). Alternativas descartadas: `/comi` e `/refeicao`.
  - O retroativo aceita até 7 dias atrás e vale só para refeições; o peso não tem registro retroativo (Q-016).
  - `/exportar` aceita um período em dias (`/exportar 30`) (Q-014).
- **Motivo:** `/r` é o mais rápido de digitar, e o registro precisa ter o mínimo de atrito.

### D-022 — Sem tipo de refeição
- **Decisão:** o bot não distingue café, almoço, jantar ou lanche. Cada `/r` vira **um registro**, mesmo que descreva várias coisas ou várias refeições (Q-005). O que importa é o total de calorias.
- **Alternativas descartadas:** separar uma mensagem em vários registros; classificar o tipo de refeição.
- **Consequência:** o Gemini não precisa identificar refeições, só os alimentos e as quantidades. O horário do registro continua no CSV para quem quiser analisar.

### D-023 — Falha do Gemini
> **Substituída por D-045.** Nos testes reais, metade das chamadas falhou por instabilidade passageira do Gemini, e reenviar a mensagem à mão virou rotina.

- **Decisão:** se o Gemini falhar, demorar demais ou devolver uma resposta inválida, o bot responde com uma mensagem de erro e não registra nada (RN-017). Não há nova tentativa automática.
- **Alternativas descartadas:** tentar de novo sozinho depois de alguns segundos.
- **Motivo:** simples, e a pessoa sabe na hora que precisa mandar de novo.

### D-024 — Pesagens na exportação
- **Decisão:** `/exportar` manda dois arquivos: o de refeições e um só com as pesagens (RN-011).

### D-025 — Exclusão de dados fora do MVP
- **Decisão:** não há comando para apagar todos os dados de uma pessoa no MVP (Q-006). Registros individuais continuam podendo ser apagados pelos botões.
- **Revisar se:** o bot passar a ser usado por pessoas de fora do grupo original.

### D-026 — Base própria de alimentos
> **Substituída por D-041.** A base continua existindo e fornecendo os valores por 100 g, mas o parser local e a conta sem IA saíram: todo `/r` chama o Gemini.

- **Contexto:** pela experiência dos usuários, o Gemini é consistente nas estimativas (Q-007). O problema é o consumo de tokens a cada registro.
- **Decisão:** o bot mantém uma base própria com as calorias e os macros **por 100 g** de cada alimento. Quando todos os alimentos de um registro estão na base, a conta é feita localmente, sem IA. O Gemini só é chamado para alimentos que a base ainda não conhece, e o que ele responde é guardado na base (RN-016).
- **Motivo:** as pessoas comem quase sempre as mesmas coisas. Com o tempo, a maioria dos registros passa a não gastar nenhum token.
- **Consequências:**
  - Mesma comida, mesmas calorias: a base também deixa o registro mais consistente que a IA.
  - O bot precisa de um separador local de itens e quantidades ("150 g de arroz", "1 bife", "2 ovos"). Quando ele não consegue entender a descrição, a mensagem inteira vai para o Gemini.
  - Cada alimento precisa de uma porção padrão em gramas, para descrições sem peso ("1 bife" = 120 g).
  - Um valor errado na base se repete em todos os registros futuros (ver D-028).

### D-027 — Base começa vazia
- **Decisão:** a base de alimentos começa sem nenhum alimento e é preenchida pelo Gemini conforme os registros chegam (Q-017).
- **Alternativas descartadas:** carregar a tabela TACO. Seria mais precisa desde o início, mas os nomes técnicos exigiriam um trabalho de apelidos.
- **Consequência:** nas primeiras semanas, quase todo registro chama o Gemini; o consumo de tokens cai conforme a base cresce.
- **Revisar se:** a base demorar a cobrir o que os usuários comem, ou se a precisão dos valores do Gemini incomodar.
- **Nota (10/11/2026, D-041):** a decisão continua valendo, mas a consequência sobre os tokens não: todo `/r` chama o Gemini, com ou sem o alimento na base. O que a base acumula agora é consistência dos valores por 100 g, não economia.

### D-028 — Sem comando para a base
- **Decisão:** o MVP não tem comando para ver ou corrigir os valores e as porções da base (Q-018). Se um valor estiver errado, a correção é feita direto no banco.
- **Alternativas descartadas:** `/alimento <nome>` e `/alimento <nome> <kcal>`.
- **Mitigação:** a validação do que vem do Gemini (RN-016) barra os erros grosseiros, e os gramas na resposta mostram na hora quando uma porção padrão não bate. (Desde D-044 a porção padrão não entra mais na conta; os gramas na resposta mostram a conversão feita pelo Gemini.)
- **Revisar se:** corrigir no banco ficar frequente.

### D-029 — Tabela de itens da refeição
- **Contexto:** os itens de cada refeição ficavam num campo JSONB (`refeicoes.itens`). O Postgres não cria chave estrangeira para dentro de JSONB, então a tabela `alimentos` ficava sem nenhuma ligação com as refeições.
- **Decisão:** cada item vira uma linha em `refeicao_itens`, com chave estrangeira para `refeicoes` e para `alimentos`. Os valores (gramas, kcal e macros) são **copiados** da base no momento do registro.
- **Alternativas descartadas:** JSONB em `refeicoes`, que é mais simples de gravar mas não garante que o alimento existe e dificulta a análise por alimento.
- **Motivo:** integridade garantida pelo banco e consultas simples como "quanto arroz comi no mês".
- **Consequências:**
  - Gravar uma refeição vira um `INSERT` na refeição e um por item, numa transação.
  - Como os valores são copiados, corrigir a base não muda refeições antigas (coerente com D-028).
  - O total continua gravado em `refeicoes`, porque a correção por número (RN-015) muda só o total.

### D-030 — Sem apelidos de alimentos
- **Contexto:** a base guardava uma lista de apelidos por alimento ("arroz", "arroz branco"), e foi proposta uma tabela própria para impedir apelidos ambíguos.
- **Decisão:** não haverá apelidos no MVP, nem em lista nem em tabela. O alimento é encontrado só pelo nome normalizado.
- **Motivo:** os usuários não veem necessidade por ora.
- **Consequência:** formas diferentes de escrever o mesmo alimento viram alimentos diferentes na base, cada uma com uma chamada ao Gemini na primeira vez.
- **Revisar se:** a base acumular duplicatas ou o consumo de tokens não cair como esperado.
- **Nota (10/11/2026, D-041 e D-043):** a busca continua só pelo nome. Como todo `/r` chama o Gemini, duplicatas não custam chamadas a mais; e como o nome passou a ser o nome curto e corrigido do Gemini, parte das variações de escrita já chega igual. O critério de revisão passa a ser só o acúmulo de duplicatas.

### D-031 — Alimentos considerados preparados
- **Decisão:** o prompt do Gemini instrui a considerar os alimentos na forma em que são comidos: "arroz" é arroz cozido, "frango" é frango preparado, e assim por diante. Valores de alimento cru só quando a pessoa escrever "cru".
- **Motivo:** cru e cozido têm calorias por 100 g muito diferentes (arroz cru tem cerca de 2,7 vezes as de cozido). Fixar a forma preparada evita que o mesmo alimento receba valores incoerentes.

### D-032 — Limitações aceitas no MVP
- **Contexto:** revisão das limitações da estrutura do banco.
- **Decisão:** as limitações abaixo são conhecidas e aceitas no MVP:
  - **Base compartilhada:** os participantes usam a mesma base e as mesmas porções padrão. Quem quiser diferenciar escreve de forma mais específica ("pão francês", "pão de forma").
  - **Total da refeição prevalece:** depois de uma correção por número (RN-015), o total em `refeicoes` difere da soma dos itens. O **total da refeição é o valor oficial**; os itens guardam a estimativa original.
  - **Sem histórico de correção:** corrigir pela descrição substitui os itens, sem guardar os valores anteriores.
- **Revisar se:** as análises por alimento ficarem distorcidas pelas correções manuais.

### D-033 — Exclusão física com confirmação
- **Contexto:** o botão ❌ Apagar marcaria o registro como apagado (`apagado_em`), mantendo-o no banco para recuperação.
- **Decisão:** apagar remove o registro com `DELETE` (os itens da refeição vão junto, em cascata). Para evitar engano, o bot pede confirmação antes (RN-015).
- **Alternativas descartadas:** exclusão lógica com `apagado_em`.
- **Motivo:** sem botão de desfazer, a exclusão lógica só servia para recuperar algo direto no banco, e obrigava toda consulta a lembrar do filtro. Esquecer o filtro faria registros apagados voltarem a contar sem aviso.
- **Consequência:** um registro apagado não tem volta; a proteção é a confirmação.

### D-034 — Nome do alimento vem do texto da pessoa
> **Substituída por D-043.** Na prática, o Gemini devolve um nome curto e corrigido (`pichanha` → `picanha assada`), e os usuários preferiram manter isso.

- **Contexto:** sem apelidos (D-030), se o nome viesse do Gemini, o mesmo alimento poderia entrar duas vezes na base ("arroz cozido" e "arroz branco cozido").
- **Decisão:** o nome do alimento na base é o trecho que a pessoa escreveu, normalizado (minúsculo, sem acento, singular, sem quantidade): `150 g de arroz` → `arroz`. O Gemini só fornece os valores por 100 g e a porção padrão.
- **Motivo:** quem escreve sempre do mesmo jeito sempre encontra o mesmo alimento, sem duplicatas e sem nova chamada à IA.
- **Consequência:** "arroz" e "arroz integral" continuam sendo alimentos diferentes, como deve ser.
- **Quando a mensagem inteira vai ao Gemini:** ele devolve o trecho escrito pela pessoa, no singular, e o código só tira maiúsculas, acentos e espaços nas pontas. O nome depende do prompt, sem conferência em código: o Gemini pode devolver "pão francês" para "pão", e isso pode entrar na base. É um risco aceito na etapa 3; a resposta mostra nome e gramas, e a correção é direto no banco (D-028).
- **Aceito pelos usuários:** formas diferentes de escrever a mesma coisa ("arroz", "arroz branco") viram alimentos repetidos na base. Isso não é problema: a base reflete o que cada um digita.

### D-035 — Só Docker, também no desenvolvimento
- **Contexto:** o roteiro deixava o Docker para a etapa 9, com o bot rodando direto com Python no desenvolvimento. Na máquina de desenvolvimento já existe um Postgres local usando a porta 5432.
- **Decisão:** a partir da etapa 2, o bot e o banco rodam sempre em Docker Compose, no desenvolvimento e no servidor. Os testes também rodam no container.
- **Alternativas descartadas:** rodar o bot com Python local e só o banco no Docker; usar o Postgres já instalado na máquina.
- **Motivo:** o ambiente de desenvolvimento fica igual ao de produção, e o banco do KALLY fica isolado dos outros.
- **Consequências:**
  - O bot encontra o banco sempre em `db:5432`, dentro da rede do Compose.
  - O código é montado no container (bind mount): mudou o código, basta reiniciar o bot, sem reconstruir a imagem.
  - O banco fica acessível na máquina só em `127.0.0.1:5433`, para consulta com ferramentas como DBeaver. Não conflita com o Postgres local.
  - O Docker sai da etapa 9 e entra na etapa 2 do roteiro.

### D-036 — Silêncio em mensagem sem comando
- **Contexto:** a RN-013 propunha avisar quem esquecesse o `/r`, e o papagaio respondia a toda mensagem.
- **Decisão:** mensagem sem comando não gera resposta. O papagaio sai e nada o substitui.
- **Motivo:** o grupo precisa poder conversar sem o bot responder a cada mensagem.
- **Consequências:** o bot não precisa ler a conversa, então a privacidade no BotFather volta para `Enable`. Quem esquecer o `/r` não recebe aviso.

### D-037 — Limite da descrição
- **Decisão:** a descrição do `/r` tem até 500 caracteres, contados no texto limpo (espaços repetidos reduzidos e linhas vazias removidas). Acima disso, o bot avisa e não chama o Gemini.
- **Motivo:** limita o gasto de tokens por mensagem; uma refeição cabe com folga nesse tamanho.

### D-038 — Coerência de macros
- **Decisão:** a resposta do Gemini é aceita se `abs(4P + 4C + 9G - kcal) <= max(20% de kcal, 10)`. O campo `alcoolico`, que existe só na resposta e não é guardado, dispensa essa conta.
- **Motivo:** o álcool tem cerca de 7 kcal/g fora dos macros, então cerveja e vinho sempre falhariam. O mínimo de 10 kcal evita recusar alimentos com poucas calorias por diferenças pequenas.

### D-039 — Item misturado com lixo
- **Decisão:** se a descrição mistura alimentos com algo que não é comida, os alimentos são registrados e a resposta avisa: `Ignorei: kkkk`. Só quando não sobra nenhum alimento o bot não registra (RN-013).
- **Motivo:** cancelar tudo por causa de um "kkkk" obrigaria a reenviar a mensagem, e o aviso mostra o que ficou de fora.

### D-040 — Tetos na resposta do Gemini e erro inesperado
- **Contexto:** a revisão da etapa 3 mostrou que valores absurdos do Gemini passavam pela validação. Gramas gigantes estouravam o cálculo, e o erro fora de banco ficava só no log, sem resposta à pessoa.
- **Decisão:**
  - `gramas` e `porcao_g` vão até 10.000 g por item, com o limite exato aceito.
  - Proteína, carbo e gordura vão até 100 g por 100 g, em todo alimento, inclusive com `alcoolico`, que só dispensa a coerência de macros (D-038).
  - Acima disso, a resposta inteira é inválida: vale o texto da RN-017 e nada é gravado.
  - Erro inesperado fora de banco no `/r` e no `/peso` responde "Algo deu errado. Tente de novo em instantes." e vai para o log. O texto de banco fora do ar continua só para erro de banco.
- **Motivo:** 100 g de alimento não têm mais de 100 g de um macro, e 10 kg por item já cobre qualquer refeição real. A pessoa não deve ficar sem resposta quando o bot falha.
- **Revisar se:** o aviso de erro inesperado levar a registros repetidos, porque ele também aparece quando só o envio da confirmação falhou.

### D-041 — Sem parser local: o Gemini separa e converte, a base fornece os valores
- **Contexto:** a etapa 4 do roteiro original ia criar `parser.py` e `alimentos.py` para separar a descrição em código e só chamar o Gemini para alimentos novos (D-026). Depois da etapa 3, três fatos mudaram a conta: (1) o grupo usa muitas medidas caseiras no `/r` (colher, concha, fatia, "meio", "pequeno", "grande") e vinha convertendo para gramas antes de mandar; um parser local não entende essas medidas sem uma tabela própria, e erraria em silêncio; (2) a cota do Gemini nunca foi problema, o uso nem saiu do nível gratuito; (3) a consistência por 100 g, principal ganho da base, já existe desde a etapa 3: alimento conhecido usa os valores da base, nunca os novos do Gemini (P2 da etapa 3).
- **Decisão:** o modelo da etapa 3 passa a ser o definitivo.
  - Todo `/r` válido chama o Gemini uma vez, com a descrição inteira.
  - O Gemini separa os itens e converte **qualquer** medida em gramas: peso, volume, unidades e medidas caseiras (colher, concha, fatia, fração, tamanho). Sem quantidade, ele estima uma porção típica.
  - A base fornece os valores por 100 g quando o alimento já existe pelo nome, e aprende os alimentos novos (D-027).
  - `parser.py` fica só para as datas do `/retro`. `alimentos.py` deixa de existir. O "(2 un.)" na resposta cai.
- **Alternativas descartadas:**
  - Parser local completo com consulta prévia na base (etapa 4 original, D-026): não entende medidas caseiras, e o erro seria silencioso (gramas errados com cara de certos).
  - Parser local só para gramas e ml, com o Gemini para o resto (híbrido): duas formas de interpretar a mesma descrição, mais código e mais testes, para economizar uma cota que não é gasta.
  - Tabela de medidas caseiras em código ("1 concha = 140 g"): vira uma regra por alimento, o que a etapa 3 evitou (D11), e só cobriria o que alguém cadastrasse.
- **Consequências:**
  - O Gemini fora do ar impede qualquer `/r`, mesmo de alimentos já conhecidos. Por isso a resiliência virou a nova etapa 4 (D-045, D-046).
  - Os gramas de um mesmo texto podem variar entre chamadas, porque vêm sempre do Gemini; os valores por 100 g, não.
  - Toda a etapa 4 antiga sai do roteiro.
- **Revisar se:** o uso sair do nível gratuito ou a cota passar a faltar; ou se os gramas do Gemini para medidas caseiras se mostrarem inconsistentes.

### D-042 — Sem cache por linha e sem os nomes da base no prompt
- **Contexto:** junto com D-041, foram avaliadas duas formas de reduzir chamadas ou duplicatas.
- **Decisão:** nenhuma das duas entra.
  - **Cache por linha:** guardar a resposta do Gemini para cada linha de descrição já vista e reaproveitar sem chamar a IA. Descartado: economiza uma cota que não falta, cria uma tabela nova e uma regra de invalidação, e congelaria gramas errados.
  - **Nomes da base no prompt:** mandar a lista de alimentos já cadastrados para o Gemini escolher entre eles. Descartado: o prompt cresce com a base (tokens em toda chamada), e o Gemini pode encaixar um alimento novo num nome existente parecido, o que é pior que uma duplicata.
- **Revisar se:** as duplicatas na base atrapalharem as análises por alimento.

### D-043 — Nome do alimento: o que o Gemini devolve, com o prompt atual
- **Contexto:** D-034 mandava usar o trecho escrito pela pessoa. Na prática, o Gemini devolve um nome curto e corrigido (`pichanha` → `picanha assada`, `goiabas grandes` → `goiaba`), e os usuários gostaram do resultado.
- **Decisão:** o nome do alimento é o que o Gemini devolve, e **o prompt atual não muda** (confirmado pelo usuário em 10/11/2026). O prompt pede as palavras da pessoa, no singular, sem quantidade; quando o Gemini corrige a grafia ou tira o tamanho mesmo assim, o resultado é aceito, sem conferência em código. O código só normaliza para a base: minúsculo, sem acento, sem espaços nas pontas. A resposta mostra o nome como veio do Gemini (P10 da etapa 3).
- **Alternativas descartadas:** manter D-034 (trecho literal da pessoa, que preserva erros de digitação e gera duplicatas como `pichanha`); conferir em código se o nome devolvido está contido no texto da pessoa (D10 da etapa 3).
- **Consequências:**
  - O risco D10 da etapa 3 vira **risco aceito permanente**: o Gemini pode completar o nome ("pão" → "pão francês"), e isso entra na base. A resposta mostra nome e gramas; a correção da base é direto no banco (D-028).
  - O mesmo texto pode gerar nomes diferentes em dias diferentes ("picanha" e "picanha assada"), o que cria duplicatas. Aceito, como em D-030.
  - O prompt continua dizendo "não troque, não complete e não melhore o nome". Isso reduz as correções, mas não as impede; as que acontecerem são aceitas. Também não muda a regra dos gramas: as medidas caseiras já são convertidas com o prompt atual (ex.: `1/4 de unidade Mamão grande` → 150 g), como D-041 espera.
- **Revisar se:** o Gemini passar a trocar alimentos por outros diferentes (não só corrigir a grafia).

### D-044 — Porção padrão só como referência
- **Contexto:** a porção padrão (`porcao_g`, `porcao_nome`) existia para o parser converter unidades em gramas (D-026). Sem parser (D-041), ela não entra mais em nenhuma conta.
- **Decisão:** o Gemini continua devolvendo a porção padrão, ela continua sendo validada (maior que zero, até 10.000 g, nome preenchido) e gravada em `alimentos`, como referência para consultas e para uma eventual volta do cálculo local. Ela não entra no cálculo das calorias.
- **Alternativas descartadas:** tirar a porção do schema e da validação (exigiria migração para tornar as colunas opcionais e perderia o dado); manter no schema mas sem validar (gravaria lixo).
- **Desvantagem aceita:** uma porção padrão inválida derruba a resposta inteira (RN-016, RN-017), mesmo sem ser usada na conta. É raro, e a resiliência (D-045) dá a chance de tentar de novo.
- **Revisar se:** porção inválida aparecer nos logs como causa de falha.

### D-045 — Resiliência do Gemini: nova tentativa automática e botão
- **Contexto:** em 10/11/2026, os logs mostraram cerca de 6 falhas em 12 chamadas: 5 `ServerError` (5xx, 503) e 1 `TimeoutError`. Uma nova tentativa segundos depois funcionou em todos os casos. Hoje a pessoa precisa copiar e reenviar a mensagem. Com D-041, todo `/r` depende do Gemini, então a instabilidade dele vira instabilidade do bot inteiro.
- **Decisão:** substitui D-023.
  - Nas falhas passageiras do Gemini, o bot tenta de novo sozinho, algumas vezes, dentro de um tempo máximo, antes de responder.
  - Se ainda assim falhar, nada é registrado, e a mensagem de falha traz o botão **🔄 Tentar de novo**, que repete o pedido sem a pessoa reenviar o texto.
  - Os detalhes (quais erros, quantas tentativas, esperas, tempo máximo, comportamento do botão) são as premissas da etapa 4, em [`etapas/etapa-4-decisoes.md`](etapas/etapa-4-decisoes.md), e entram na RN-017 como proposta até serem confirmados.
- **Alternativas descartadas:**
  - Manter D-023 (só mensagem de erro): metade dos `/r` exigiria reenvio manual.
  - Só o botão, sem nova tentativa automática: a maioria das falhas some em segundos, então a pessoa apertaria o botão quase sempre.
  - Só a nova tentativa automática, sem botão: quando o Gemini fica fora por mais tempo, a pessoa volta a ter que copiar e reenviar.
  - **Modelo reserva** (trocar para outro modelo do Gemini quando o principal falha): não entra agora. Exige uma segunda variável no `.env` e validar o schema em dois modelos.
- **Consequências:**
  - Um `/r` pode demorar mais para responder enquanto o bot tenta de novo; precisa de um tempo máximo. Enquanto isso, os outros comandos esperam na fila (D-047).
  - Cada nova tentativa pode gastar cota. Com até 3 chamadas por `/r` e o uso no nível gratuito, é aceitável.
  - O botão exige guardar o pedido pendente em memória; reiniciar o bot perde os pendentes.
- **Revisar se:** as falhas continuarem frequentes mesmo com as novas tentativas (aí entra o modelo reserva), ou se a cota passar a faltar.

### D-046 — Novo roteiro
- **Contexto:** com D-041, a etapa 4 antiga (base de alimentos com parser) saiu. A resiliência do Gemini (D-045) passou a ser a prioridade, porque afeta todo `/r`.
- **Decisão:** o roteiro passa a ser: 1 a 3 concluídas · **4. Resiliência do Gemini** · **5. `/dia`** · **6. Botões de corrigir e apagar** · **7. `/retro`** · **8. `/semana`** · **9. `/exportar`** · **10. Deploy**.
- **Motivo:** a ordem foi definida pelo usuário em 10/11/2026. `/dia` e `/semana` deixam de ser uma etapa só, para cada entrega ficar menor e testável no grupo.
- **Consequência:** as referências a números de etapa em documentos antigos (por exemplo, "etapa 5" para botões e "etapa 8" para `/exportar` nos planos das etapas 2 e 3 e em comentários do código) seguem a numeração antiga.

### D-047 — Updates em fila; paralelismo fica para o futuro
- **Contexto:** com as novas tentativas (D-045), um `/r` pode levar até 40 s quando o Gemini está instável. Como o bot processa um update por vez, o `/peso` e o `/r` da outra pessoa esperam esse tempo. A alternativa analisada era rodar o `/r` e o botão em paralelo (`block=False`), com uma trava por pessoa no banco (`pg_advisory_xact_lock`) para o total do dia não sair errado.
- **Decisão:** manter a fila nesta etapa (confirmado pelo usuário em 10/11/2026). Sem `block=False`, sem `concurrent_updates` e sem trava no banco.
- **Motivo:** a única demora vem do Gemini fora do ar, e nesse caso o `/r` da outra pessoa também ficaria esperando o Gemini; o ganho do paralelismo é pequeno perto da complexidade.
- **Consequência:** durante as novas tentativas, os outros comandos só respondem quando o `/r` em andamento termina (até ~40 s).
- **Para o futuro:** chamadas paralelas são desejadas. O código da etapa 4 não deve dificultar: o fluxo do `/r` fica numa função só, o pedido pendente é retirado da memória antes de qualquer `await`, e a gravação continua numa transação só. Quando o paralelismo entrar, vem junto a trava por pessoa no `registrar_refeicao`.
- **Revisar se:** o grupo crescer ou a espera atrapalhar o uso.

### D-048 — Detalhes da resiliência do Gemini
- **Contexto:** premissas P1 a P13 de [`etapas/etapa-4-decisoes.md`](etapas/etapa-4-decisoes.md), respondidas pelo usuário em 10/11/2026.
- **Decisão:** vale a RN-017 como está escrita: só falhas passageiras se repetem (5xx, 429, tempo esgotado, conexão); até 3 tentativas, esperas de 2 s e 5 s, 15 s por tentativa e 40 s no total; "digitando…" antes de cada tentativa; botão "🔄 Tentar de novo" só na falha do Gemini e só para quem mandou o `/r`; pedido em memória por 7 dias; vale o horário do `/r` original; clique bem-sucedido edita a mensagem de falha. O prompt não muda (D-043). As três pendências herdadas da etapa 2 entram na etapa 4.
- **Motivo dos 15 s / 40 s:** a resposta bem-sucedida mais lenta nos logs levou 9,5 s (9 itens); 12 s deixaria pouca margem.
