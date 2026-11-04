# KALLY — Exemplos de uso

Como seria a conversa com o bot em cada situação. As regras completas estão em [`regras-de-negocio.md`](regras-de-negocio.md); cada exemplo indica a regra que ilustra.

**Cenário:** o grupo tem João e Maria. "Hoje" é domingo, 01/11/2026. As calorias são ilustrativas.

Botões aparecem entre colchetes: `[✏️ Corrigir] [❌ Apagar]`.

Para simplificar, as seções 1 a 3 mostram só as calorias de cada item. O bot real também mostra os gramas usados em cada um, como na seção 7.

---

## 1. Registrar refeições (`/r`)

### Registro simples · RN-013
```
João (08:12): /r pão com ovo e café com leite

KALLY: João: +320 kcal · total hoje: 320 kcal
       pão francês 150 · ovo mexido 90 · café com leite 80
       [✏️ Corrigir] [❌ Apagar]
```

### Com quantidades (estimativa melhor) · RN-013
```
Maria (12:30): /r 150 g de arroz, 100 g de feijão, 120 g de frango grelhado e salada

KALLY: Maria: +540 kcal · total hoje: 860 kcal
       arroz 195 · feijão 75 · frango 200 · salada 70
       [✏️ Corrigir] [❌ Apagar]
```

### Várias coisas numa mensagem só · RN-013, D-022
Não importa se foi café, almoço ou lanche: cada `/r` é **um registro**, com o total de tudo o que foi descrito.
```
João (16:05): /r banana, 1 iogurte e um punhado de castanhas

KALLY: João: +330 kcal · total hoje: 1.300 kcal
       banana 90 · iogurte natural 120 · castanhas (30 g) 120
       [✏️ Corrigir] [❌ Apagar]
```

### Duas refeições de uma vez · D-022
Também vira um registro só, no horário da mensagem.
```
Maria (21:40): /r esqueci de mandar: lanche da tarde pão de queijo, e jantei sopa de legumes

KALLY: Maria: +420 kcal · total hoje: 1.890 kcal
       pão de queijo (2 un.) 180 · sopa de legumes 240
       [✏️ Corrigir] [❌ Apagar]
```

### `/r` sem descrição · RN-013
```
João: /r

KALLY: Descreva o que comeu, ex.: /r 150 g de arroz e 1 filé de frango
```

### Nenhum alimento reconhecido · RN-013
Nada é registrado.
```
João: /r kkkkk

KALLY: Não identifiquei nenhum alimento. Descreva o que comeu, ex.: /r 150 g de arroz e 1 filé de frango
```

### Mensagem esquecendo o comando · RN-013
Nada é registrado; o bot avisa para ninguém achar que registrou.
```
João: almocei arroz, feijão e bife

KALLY: Para registrar, use /r seguido do que comeu. Ex.: /r arroz, feijão e bife
```

---

## 2. Registrar no passado (`/retro`)

### Ontem · RN-014
```
Maria: /retro ontem jantei 2 fatias de pizza de calabresa

KALLY: Maria: +540 kcal em sáb 31/10 (retroativo) · total de 31/10: 2.130 kcal
       pizza de calabresa (2 fatias) 540
       [✏️ Corrigir] [❌ Apagar]
```

### Data e hora · RN-014
```
João: /retro 28/10 20:00 hambúrguer artesanal e batata frita

KALLY: João: +1.150 kcal em qua 28/10 às 20:00 (retroativo) · total de 28/10: 2.310 kcal
       hambúrguer 750 · batata frita (porção média) 400
       [✏️ Corrigir] [❌ Apagar]
```

### Sem hora · RN-014
A refeição fica sem horário: aparece como `--:--` e com a hora vazia no CSV.
```
Maria: /retro anteontem açaí 500 ml com granola

KALLY: Maria: +620 kcal em sex 30/10 (retroativo) · total de 30/10: 2.010 kcal
       açaí 500 ml 490 · granola 130
       [✏️ Corrigir] [❌ Apagar]
```

### Mais de 7 dias atrás · RN-014
```
João: /retro 20/10 feijoada

KALLY: Só dá para registrar até 7 dias atrás (a partir de 25/10).
```

### Hoje ou data futura · RN-014
```
João: /retro 02/11 pizza

KALLY: Não dá para registrar no futuro. Para hoje, use /r.
```

### Data em formato inválido · RN-014
```
João: /retro semana passada pizza

KALLY: Não entendi a data. Use ontem, anteontem ou DD/MM. Ex.: /retro 28/10 20:00 pizza
```

---

## 3. Corrigir e apagar (botões)

### Corrigir com nova descrição · RN-015
O Gemini estima de novo com a descrição nova. A mensagem original do bot é atualizada.
```
KALLY: João: +650 kcal · total hoje: 1.950 kcal
       arroz 200 · feijão 140 · bife 250 · salada 60
       [✏️ Corrigir] [❌ Apagar]

(João aperta ✏️ Corrigir)

KALLY: João, responda a esta mensagem com a descrição correta,
       ou só com as calorias (ex.: 450).

João (respondendo): arroz, feijão, 2 bifes e salada

KALLY: ✏️ João: corrigido de 650 para 900 kcal · total hoje: 2.200 kcal
       arroz 200 · feijão 140 · bife (2 un.) 500 · salada 60
```

### Corrigir só as calorias (valor da embalagem) · RN-015
Sem chamar o Gemini. Os macros são ajustados na mesma proporção.
```
KALLY: Maria: +280 kcal · total hoje: 1.140 kcal
       barra de proteína 280
       [✏️ Corrigir] [❌ Apagar]

(Maria aperta ✏️ Corrigir)

KALLY: Maria, responda a esta mensagem com a descrição correta,
       ou só com as calorias (ex.: 450).

Maria (respondendo): 190

KALLY: ✏️ Maria: corrigido de 280 para 190 kcal (valor informado) · total hoje: 1.050 kcal
```

### Apagar · RN-015
```
KALLY: João: +90 kcal · total hoje: 1.390 kcal
       banana 90
       [✏️ Corrigir] [❌ Apagar]

(João aperta ❌ Apagar)

KALLY: Apagar "banana" (90 kcal)? Não dá para desfazer.
       [Sim, apagar] [Cancelar]

(João aperta Sim, apagar)

KALLY: ❌ João: apagado "banana" (90 kcal) · total hoje: 1.300 kcal
```

### Corrigir um registro retroativo · RN-015
Funciona igual, e o total mostrado é o do dia da refeição.
```
(João aperta ✏️ no registro do hambúrguer de 28/10 e responde: 950)

KALLY: ✏️ João: corrigido de 1.150 para 950 kcal (valor informado) · total de 28/10: 2.110 kcal
```

### Outra pessoa aperta o botão · RN-015
Aparece só um aviso para quem apertou (um pop-up do Telegram). Nada muda e nada é enviado ao grupo.
```
(Maria aperta ❌ no registro do João)

[aviso para Maria] Só João pode alterar este registro.
```

### Botão de registro com mais de 7 dias · RN-015
```
(João aperta ✏️ num registro de 20/10)

[aviso para João] Este registro tem mais de 7 dias e não pode mais ser alterado.
```

---

## 4. Consultas

### `/dia` · RN-009
Só o dia de hoje, só de quem pediu.
```
João: /dia

KALLY: João · hoje, dom 01/11
       08:12  pão com ovo e café com leite         320 kcal
       12:40  arroz, feijão, 2 bifes e salada      900 kcal
       16:05  banana, iogurte e castanhas          330 kcal
       Total: 1.550 kcal · P 98 g · C 162 g · G 52 g
```

### `/dia` sem registros · RN-009
```
Maria: /dia

KALLY: Maria · hoje, dom 01/11
       Nenhum registro ainda. Use /r para registrar.
```

### `/semana` · RN-010
De segunda a domingo. Dias sem registro aparecem como "—" e ficam fora da média.
```
João: /semana

KALLY: João · semana 26/10 a 01/11
       Seg 26  2.140 kcal
       Ter 27  1.980 kcal
       Qua 28  2.110 kcal
       Qui 29  —
       Sex 30  2.050 kcal
       Sáb 31  2.240 kcal
       Dom 01  1.550 kcal  (hoje)
       Total: 12.070 kcal · média: 2.012 kcal/dia (6 dias com registro)
```

---

## 5. Peso (`/peso`)

### Registrar · RN-012
```
João: /peso 82,4

KALLY: João: 82,4 kg registrado (anterior: 83,1 kg em 28/10)
       [✏️ Corrigir] [❌ Apagar]
```

### Primeira pesagem · RN-012
```
Maria: /peso 64.8

KALLY: Maria: 64,8 kg registrado (primeira pesagem)
       [✏️ Corrigir] [❌ Apagar]
```

### Consultar · RN-012
```
João: /peso

KALLY: João: 82,4 kg em dom 01/11
```

### Consultar sem nenhuma pesagem · RN-012
```
Maria: /peso

KALLY: Maria: nenhuma pesagem registrada ainda. Ex.: /peso 82,4
```

### Valor inválido · RN-012
```
João: /peso 824

KALLY: Peso fora do esperado (30 a 300 kg). Ex.: /peso 82,4
```

### Valor que não é número · RN-012
```
João: /peso abc

KALLY: Não entendi o peso. Ex.: /peso 82,4
```

### Corrigir uma pesagem · RN-012, RN-015
Não há peso retroativo; uma pesagem errada é corrigida pelo botão.
```
(João aperta ✏️ na pesagem de 82,4 kg e responde: 81,9)

KALLY: ✏️ João: peso corrigido de 82,4 para 81,9 kg
```

---

## 6. Exportar (`/exportar`)

### Todo o histórico · RN-011
```
João: /exportar

KALLY: 📎 kally_2026-09-15_a_2026-11-01.csv
       📎 kally_pesos_2026-09-15_a_2026-11-01.csv
       Histórico completo: 2 pessoas, 412 refeições, 58 pesagens.
```

### Últimos N dias · RN-011
```
Maria: /exportar 30

KALLY: 📎 kally_2026-10-03_a_2026-11-01.csv
       📎 kally_pesos_2026-10-03_a_2026-11-01.csv
       Últimos 30 dias: 2 pessoas, 186 refeições, 41 pesagens.
```

### Conteúdo do arquivo · RN-011
Separador `;` e vírgula decimal, para abrir direto no Excel.
```
data;hora;pessoa;descricao;kcal;proteina_g;carbo_g;gordura_g;retroativo;registrado_em
2026-10-28;20:00;João;hambúrguer artesanal e batata frita;950;38;82;51;sim;2026-11-01 10:22
2026-10-30;;Maria;açaí 500 ml com granola;620;7;104;21;sim;2026-11-01 09:05
2026-11-01;08:12;João;pão com ovo e café com leite;320;16;38;11;não;2026-11-01 08:12
2026-11-01;12:30;Maria;150 g de arroz, 100 g de feijão, 120 g de frango grelhado e salada;540;45;62;10;não;2026-11-01 12:30
```

### Arquivo de pesagens · RN-011, D-024
```
data;hora;pessoa;peso_kg
2026-10-28;07:20;João;83,1
2026-10-29;07:05;Maria;65,2
2026-11-01;07:15;João;81,9
2026-11-01;07:40;Maria;64,8
```

---

## 7. Base de alimentos · RN-016

Por trás, o bot só chama o Gemini para alimentos que ainda não conhece. Para quem usa, a conversa é igual; a diferença está no custo e na consistência.

### Primeira vez: alimento novo, usa a IA
A base ainda não conhece "tapioca" nem "queijo coalho". Os dois vão ao Gemini e entram na base.
```
Maria (09:00): /r 1 tapioca com queijo coalho

KALLY: Maria: +310 kcal · total hoje: 310 kcal
       tapioca 70 g · 170 kcal · queijo coalho 40 g · 140 kcal
       [✏️ Corrigir] [❌ Apagar]
```

### Da segunda vez em diante: sem IA
Os dois já estão na base. A conta é local, sem gastar tokens, e dá exatamente o mesmo valor.
```
Maria (dias depois): /r tapioca com queijo coalho

KALLY: Maria: +310 kcal · total hoje: 310 kcal
       tapioca 70 g · 170 kcal · queijo coalho 40 g · 140 kcal
       [✏️ Corrigir] [❌ Apagar]
```

### Mistura de conhecido e novo
Arroz e feijão saem da base. Só "moqueca de peixe" vai ao Gemini.
```
João: /r 150 g de arroz, feijão e moqueca de peixe

KALLY: João: +590 kcal · total hoje: 1.120 kcal
       arroz 150 g · 195 kcal · feijão 100 g · 75 kcal · moqueca de peixe 250 g · 320 kcal
       [✏️ Corrigir] [❌ Apagar]
```

### O peso informado vale mais que a porção padrão
A base sabe que "1 bife" são 120 g, mas o que a pessoa escreve tem prioridade.
```
João: /r 200 g de bife e 2 ovos

KALLY: João: +560 kcal · total hoje: 1.680 kcal
       bife 200 g · 420 kcal · ovo 100 g (2 un.) · 140 kcal
       [✏️ Corrigir] [❌ Apagar]
```

### Porção padrão não bate: corrigir pela descrição · RN-015
Os gramas na resposta mostram a porção que o bot supôs. Se não bate, basta corrigir com o peso.
```
KALLY: João: +250 kcal · total hoje: 1.370 kcal
       bife 120 g · 250 kcal
       [✏️ Corrigir] [❌ Apagar]

(João aperta ✏️ e responde: 180 g de bife)

KALLY: ✏️ João: corrigido de 250 para 375 kcal · total hoje: 1.495 kcal
       bife 180 g · 375 kcal
```

### Churrasco: descrever pelo que comeu, não pelo nome do evento · RN-016
"Churrasco" sozinho vira um alimento genérico, com uma porção chutada. Pior: fica salvo na base, e todo `/r churrasco` futuro recebe o mesmo valor, tenha a pessoa comido duas linguiças ou meio boi.
```
João: /r churrasco

KALLY: João: +750 kcal · total hoje: 1.230 kcal
       churrasco 300 g · 750 kcal
       [✏️ Corrigir] [❌ Apagar]
```

Contando os pedaços, cada carne entra na base com a sua porção padrão, e os gramas na resposta mostram o que foi suposto:
```
João: /r 3 pedaços de picanha, 2 linguiças toscanas e 1 coxa de frango

KALLY: João: +1.210 kcal · total hoje: 1.690 kcal
       picanha 180 g (3 pedaços) · 520 kcal · linguiça toscana 160 g (2 un.) · 480 kcal · coxa de frango 100 g (1 un.) · 210 kcal
       [✏️ Corrigir] [❌ Apagar]
```

Sem balança, a palma da mão (sem os dedos, na espessura dela) equivale a uns 100 g de carne:
```
Maria: /r picanha do tamanho de 2 palmas da mão e 1 linguiça

KALLY: Maria: +820 kcal · total hoje: 1.540 kcal
       picanha 200 g · 580 kcal · linguiça toscana 80 g (1 un.) · 240 kcal
       [✏️ Corrigir] [❌ Apagar]
```

### O Gemini falha · RN-017
Nada é registrado.
```
João: /r yakisoba de frango

KALLY: Não consegui estimar agora. Nada foi registrado, tente de novo em instantes.
```

### Gemini fora do ar, mas tudo está na base · RN-017
Funciona normalmente, porque não precisa da IA.
```
João: /r 150 g de arroz e feijão

KALLY: João: +270 kcal · total hoje: 1.765 kcal
       arroz 150 g · 195 kcal · feijão 100 g · 75 kcal
       [✏️ Corrigir] [❌ Apagar]
```

