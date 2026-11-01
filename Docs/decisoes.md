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
| D-023 | 2026-11-01 | Falha do Gemini: só mensagem de erro, sem nova tentativa e sem registro | Negócio | vigente |
| D-024 | 2026-11-01 | `/exportar` manda um segundo CSV só com as pesagens | Produto | vigente |
| D-025 | 2026-11-01 | Exclusão de todos os dados de uma pessoa fica fora do MVP | Produto | vigente |
| D-026 | 2026-11-01 | Base própria de alimentos (kcal/100 g); a IA só é chamada para o que não está na base | Técnica | vigente |
| D-027 | 2026-11-01 | A base de alimentos começa vazia e aprende com o Gemini | Técnica | vigente |
| D-028 | 2026-11-01 | Sem comando para ver ou corrigir a base no MVP | Produto | vigente |
| D-029 | 2026-11-01 | Itens da refeição numa tabela própria (`refeicao_itens`), não em JSONB | Técnica | vigente |
| D-030 | 2026-11-01 | Sem apelidos de alimentos no MVP: a busca é só pelo nome | Técnica | vigente |
| D-031 | 2026-11-01 | O Gemini considera os alimentos já preparados (cozido, grelhado, assado) | Técnica | vigente |
| D-032 | 2026-11-01 | Limitações aceitas no MVP: base compartilhada, total da refeição prevalece, sem histórico de correção | Técnica | vigente |
| D-033 | 2026-11-01 | Apagar remove o registro de verdade (`DELETE`), depois de confirmação | Técnica | vigente |
| D-034 | 2026-11-01 | O nome do alimento na base é o texto que a pessoa escreveu, não o nome dado pelo Gemini | Técnica | vigente |

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
- **Decisão:** se o Gemini falhar, demorar demais ou devolver uma resposta inválida, o bot responde com uma mensagem de erro e não registra nada (RN-017). Não há nova tentativa automática.
- **Alternativas descartadas:** tentar de novo sozinho depois de alguns segundos.
- **Motivo:** simples, e a pessoa sabe na hora que precisa mandar de novo.

### D-024 — Pesagens na exportação
- **Decisão:** `/exportar` manda dois arquivos: o de refeições e um só com as pesagens (RN-011).

### D-025 — Exclusão de dados fora do MVP
- **Decisão:** não há comando para apagar todos os dados de uma pessoa no MVP (Q-006). Registros individuais continuam podendo ser apagados pelos botões.
- **Revisar se:** o bot passar a ser usado por pessoas de fora do grupo original.

### D-026 — Base própria de alimentos
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

### D-028 — Sem comando para a base
- **Decisão:** o MVP não tem comando para ver ou corrigir os valores e as porções da base (Q-018). Se um valor estiver errado, a correção é feita direto no banco.
- **Alternativas descartadas:** `/alimento <nome>` e `/alimento <nome> <kcal>`.
- **Mitigação:** a validação do que vem do Gemini (RN-016) barra os erros grosseiros, e os gramas na resposta mostram na hora quando uma porção padrão não bate.
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
- **Contexto:** sem apelidos (D-030), se o nome viesse do Gemini, o mesmo alimento poderia entrar duas vezes na base ("arroz cozido" e "arroz branco cozido").
- **Decisão:** o nome do alimento na base é o trecho que a pessoa escreveu, normalizado (minúsculo, sem acento, singular, sem quantidade): `150 g de arroz` → `arroz`. O Gemini só fornece os valores por 100 g e a porção padrão.
- **Motivo:** quem escreve sempre do mesmo jeito sempre encontra o mesmo alimento, sem duplicatas e sem nova chamada à IA.
- **Consequência:** "arroz" e "arroz integral" continuam sendo alimentos diferentes, como deve ser.
- **Aceito pelos usuários:** formas diferentes de escrever a mesma coisa ("arroz", "arroz branco") viram alimentos repetidos na base. Isso não é problema: a base reflete o que cada um digita.
