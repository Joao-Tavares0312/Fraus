# Dolos — Design System

Contrato visual da interface. Qualquer pessoa (ou agente) que escreva UI neste
projeto segue este documento. Ele não descreve como as telas estão hoje: descreve
como elas devem ser.

---

## 1. A metáfora, e por que ela governa a cor

Dolos é o daemon grego do engano. O produto existe porque **o cliente mente**: ele
escreve "ok, obrigado 🙂" e sai insatisfeito.

Disso sai a única regra de encoding que atravessa a interface inteira:

> **Âmbar é o que foi dito. Azul é o que foi medido.**

Âmbar (quente, humano, declarado) marca a superfície: o texto do cliente, o emoji
que ele escolheu, a fala literal. Azul-índigo (frio, instrumental, inferido) marca
a leitura da máquina: score, probabilidade, latência, tendência.

Quando as duas aparecem juntas — e o produto inteiro é sobre elas aparecerem
juntas — a distância entre âmbar e azul **é** a informação. É o mesmo gesto do
logo: a máscara em degradê quente na frente, a verdade em contorno frio atrás.

Nunca use âmbar para representar medição, nem azul para representar fala. A
metáfora quebra e a tela vira decoração.

---

## 2. Tokens

Todos os tokens vivem em `app/globals.css` como custom properties, declarados nos
dois temas. Nada de hex solto em componente.

### 2.1 Superfícies

| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--fundo` | `#FBFAF8` | `#0D0B12` | fundo da página |
| `--superficie` | `#FFFFFF` | `#161320` | cartões, painéis |
| `--superficie-2` | `#F4F2EE` | `#1E1A2B` | linhas alternadas, cabeçalho de tabela |
| `--borda` | `#E4E0D8` | `#2C2740` | separadores, contorno de cartão |
| `--borda-forte` | `#CBC5B8` | `#413A5C` | contorno de elemento focado ou ativo |

### 2.2 Tinta

| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--tinta-1` | `#1A1815` | `#F5F3EE` | números grandes, títulos |
| `--tinta-2` | `#4A463F` | `#C4C0B6` | corpo de texto |
| `--tinta-3` | `#6E6C62` | `#9B998F` | rótulo de eixo, timestamp, texto auxiliar |

**`--tinta-3` é o piso.** Ela foi escolhida por cálculo para cruzar 4.5:1 (AA) nos
dois temas contra `--superficie-2`, o pior caso. Nenhum texto pode usar cor mais
clara que ela. Isso não é preferência: a interface vai para projetor de banca, e
`--tinta-3` carrega o texto **"sem sinal"** — o estado que o produto existe para
não falsear.

### 2.3 Sinais — a metáfora aplicada

| Token | Claro | Escuro | Significa |
|---|---|---|---|
| `--dito` | `#C77A2E` | `#E8A055` | fala, texto do cliente, emoji |
| `--dito-fraco` | `#F2E4D2` | `#3A2A18` | preenchimento de área, realce de trecho |
| `--medido` | `#3B5BC4` | `#7B93E8` | score, probabilidade, série de NPS |
| `--medido-fraco` | `#DDE3F7` | `#1C2340` | preenchimento, faixa de referência |
| `--tempo` | `#4A8F86` | `#6FBFB3` | latência — sempre tracejado |

### 2.4 Categorias de NPS — escala divergente

Faixas fixas: **0–6 detrator · 7–8 neutro · 9–10 promotor**. Nunca redefina.

| Token | Claro | Escuro | Categoria |
|---|---|---|---|
| `--detrator` | `#C0392B` | `#E8705F` | 0–6 |
| `--neutro` | `#B08428` | `#D4A94A` | 7–8 |
| `--promotor` | `#2E7D5B` | `#5FBD91` | 9–10 |
| `--sem-sinal` | `#6E6C62` | `#9B998F` | sem dado — cinza, **jamais** na escala |

Quando uma dessas cores carregar **texto** e não só preenchimento, use a variante
`-texto` do token, calculada para AA. Cor de marcação e cor de tipo não são a
mesma coisa e não devem compartilhar hex.

`--sem-sinal` é cinza de propósito: ausência de dado não pertence à escala de
satisfação. Colori-la de vermelho seria afirmar insatisfação que ninguém mediu.

### 2.5 Espaço, raio, tipografia

Escala de espaço em múltiplos de 4: `4 8 12 16 24 32 48 64`. Nada fora dela.

Raio: `--raio-1: 6px` (etiqueta, botão), `--raio-2: 10px` (cartão, painel),
`--raio-3: 16px` (modal). Sem pílulas totalmente arredondadas — o produto é
instrumento de medição, não app de consumo.

Tipografia: uma família sem serifa para interface e **uma monoespaçada para todo
número que se compara** — score, nota, latência, percentual. Números tabulares
(`font-variant-numeric: tabular-nums`) em coluna de tabela e em cartão de
indicador, sempre. Número que dança na vertical entre linhas é erro.

Escala: `12 / 14 / 16 / 20 / 28 / 40`. O `40` é exclusivo do número principal de
um cartão de indicador.

---

## 3. Modo e postura

Esta é uma superfície **Operate**: quem chega vem completar uma tarefa — entender
a qualidade do atendimento e mexer na configuração da IA. Escaneabilidade,
consistência e expectativa nativa vencem expressão. A marca vive na precisão dos
detalhes, não em ornamento.

Consequências práticas, todas obrigatórias:

- **Densidade alta por padrão.** Este é um painel de trabalho, não uma landing.
  Nada de espaço em branco heroico entre dois números que precisam ser comparados.
- **Sem animação decorativa.** Movimento só onde carrega informação: transição de
  estado, entrada de dado novo, foco. Duração 120–200 ms. Respeite
  `prefers-reduced-motion` sem exceção.
- **Nenhum degradê em superfície de dado.** Degradê existe no logo e no cabeçalho
  da marca. Em gráfico e cartão, cor chapada — degradê distorce leitura de área.
- **Sem sombra difusa.** Elevação por borda e por superfície, não por blur.

---

## 4. Regras de visualização

Estas regras vêm da pesquisa que fundamenta o produto. Violar é erro factual, não
divergência de gosto.

### 4.1 A regra que não se negocia

**NPS e latência aparecem sobrepostos no mesmo gráfico.** Otimizar um KPI isolado
quebra outro — empurrar deflexão derruba CSAT. Cartões isolados escondem
exatamente o trade-off que o produto existe para mostrar.

Eixo duplo é reconhecidamente um antipadrão, então ele vem com três mitigações
obrigatórias, todas já implementadas e que devem ser preservadas:

1. Domínio **fixo** em cada eixo (NPS em −100…100, latência a partir de zero), para
   que o alinhamento visual entre as curvas não seja uma escolha arbitrária.
2. Cada eixo rotulado e colorido com a série que representa; latência sempre
   **tracejada**.
3. Uma visão de tabela disponível no mesmo painel — quem precisar do número exato
   não depende da leitura cruzada.

### 4.2 Faixas de referência

Todo indicador com faixa conhecida na literatura mostra a faixa, não só o valor:

- **CSAT**: banda saudável 75–85% marcada no trilho.
- **Latência**: até 10s (pico de CSAT, ~84,7%), até 60s (saudável), até 180s
  (degradando, −2 a −3 pontos de CSAT por minuto), acima de 180s (faixa de
  abandono — 57% desistem). Os rótulos citam a literatura corretamente; não
  invente limiar nem atribua número a fonte que não o diz.

### 4.3 Honestidade

- **`score: null` é "sem sinal", nunca 0.** Em célula, em gráfico, em ordenação, em
  export. Nenhum `?? 0` no caminho de um score.
- **Agregado sem dado é estado vazio, não zero.** "NPS +0" quando nada foi medido é
  mentira com cara de medição.
- **O NPS é inferido do texto**, não perguntado ao cliente. Toda tela que o exibe
  carrega a etiqueta "estimativa" e a nota metodológica ao pé.
- **Estado vazio nomeia o que falta.** Se um dado não existe, diga qual endpoint ou
  qual etapa o produziria. Nunca preencha com número simulado.

---

## 5. Componentes

Três famílias fazem o trabalho pesado. Novos componentes devem se explicar como
variação de uma delas antes de existirem.

**Cartão de indicador.** Rótulo, número (mono, tabular, `40`), unidade, trilho com
faixa de referência quando houver, delta versus período anterior, e etiqueta de
qualificação (`estimativa`, `sem dado`) quando couber. Falha isolada: um cartão que
não carrega mostra seu próprio erro sem derrubar os vizinhos.

**Tabela.** Cabeçalho fixo, zebra por `--superficie-2`, números tabulares
alinhados à direita, ordenação que sempre manda `null` para o fim nos dois
sentidos, linha inteira clicável com foco visível. Rolagem horizontal própria — o
`body` nunca rola na horizontal.

**Painel de gráfico.** Título, subtítulo com a fonte ou o método quando o número
for derivado, o gráfico, e a alternância para tabela. Altura fixa por breakpoint;
gráfico que muda de altura ao trocar de dado causa salto de layout.

---

## 6. Acessibilidade — piso, não meta

- Contraste **AA (4.5:1)** para todo texto, verificado por cálculo e não a olho.
- Cor **nunca** é o único canal. Categoria de NPS carrega rótulo textual junto do
  hex; séries de gráfico se distinguem também por traço (contínuo vs. tracejado).
- Foco visível em tudo que recebe teclado, com contorno que sobrevive nos dois
  temas.
- Tabela com semântica de tabela. Ícone sozinho sempre com rótulo acessível.
- Alvo de toque mínimo 44×44 px em telas estreitas.

---

## 7. O que este documento proíbe

- Hex solto em componente, fora dos tokens.
- Vermelho, verde ou âmbar da escala de NPS usados para qualquer outra coisa.
- Zero no lugar de ausência de dado.
- Número inventado, simulado ou de exemplo em tela de produção.
- Degradê ou sombra difusa em superfície que carrega dado.
- Texto abaixo de `--tinta-3`.
- Gráfico sem eixo rotulado.
- Animação que não carrega informação.
