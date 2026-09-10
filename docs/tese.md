# A tese

## O problema

Quem opera um chatbot de atendimento mede satisfação de dois jeitos, e os dois
falham no mesmo ponto.

**Pesquisa declarada (NPS, CSAT).** Depende de resposta, e a taxa de resposta é
baixa e enviesada: responde quem ficou muito irritado ou muito satisfeito. O
cliente do meio — o que resolveu o problema com esforço, ou desistiu no meio —
simplesmente não aparece.

**Taxa de contenção.** Mede se o bot segurou o atendimento sem escalar. É um
número de **volume**, não de qualidade: sobe igual quando o bot resolve e quando
o cliente desiste de tentar.

Cruzados, os dois produzem o pior cenário possível: contenção alta com
satisfação não medida. O painel fica verde e ninguém sabe se a operação está
boa.

## A aposta

O texto do atendimento **já contém** a evidência da satisfação. Ela não precisa
ser perguntada — precisa ser lida.

O caso canônico do projeto é este:

> *"que atendimento maravilhoso, só esperei 3 horas"*

Uma pesquisa nunca vai receber essa frase. Um classificador de sentimento
ingênuo lê "maravilhoso" e marca promotor. O sistema precisa das duas metades ao
mesmo tempo: o que foi **dito** e o que foi **medido**.

## O que sai disso, e que nada mais consegue calcular

**Falso containment.** O cruzamento de "não escalou" com "saiu detrator". É a
tese virando número, e só quem infere satisfação do texto consegue calcular:
quem depende de pesquisa respondida perde justamente o cliente contido, que é o
que não responde.

## O que a tese NÃO promete

- **Não é NPS declarado.** É estimativa, e a interface diz isso em todo lugar.
- **Não decide nada sozinha.** Nenhuma saída aciona ação sobre ninguém.
- **Não pontua atendentes** — ver [Conformidade](conformidade.md).
- **Não é infalível, e diz onde falha.** O sinal de tempo é treinado em dados
  sintéticos; a cabeça de ironia é pouco confiável e por isso não pontua; fora
  da faixa de latência do treino o relógio domina a nota. Tudo isso está em
  [Limitações](limitacoes.md), com número.
