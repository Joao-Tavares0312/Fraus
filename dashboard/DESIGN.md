# Fraus — Design System

Contrato visual da interface. Quem escrever UI neste projeto segue este documento.
Ele não descreve como as telas estão hoje: descreve como elas devem ser.

**Chassi:** shadcn/ui sobre Tailwind v4, tokens em OKLCH, tema escuro único —
herdado do sistema do `wascer-kronos`. A camada de dado é própria do Fraus.

---

## 1. A metáfora, e por que ela governa a cor

Fraus é a divindade romana da fraude. O produto existe porque **o cliente mente**:
ele escreve "ok, obrigado 🙂" e sai insatisfeito.

Disso sai a regra de encoding que atravessa a interface inteira:

> **Âmbar é o que foi dito. Azul é o que foi medido.**

Âmbar (quente, humano, declarado) marca a superfície: o texto do cliente, o emoji
que ele escolheu, a fala literal. Azul (frio, instrumental, inferido) marca a
leitura da máquina: score, probabilidade, tendência.

Quando as duas aparecem juntas — e o produto inteiro é sobre isso — a distância
entre âmbar e azul **é** a informação. É o gesto do logo: a máscara em degradê
quente na frente, a verdade em contorno frio atrás.

Nunca use âmbar para medição nem azul para fala. A metáfora quebra e a tela vira
decoração.

### 1.1 A regra que separa marca de dado

**O lime da marca nunca aparece em dado.** `--primary` é lime; ele vive em botão,
foco, item ativo da navegação e nada mais. Nenhuma série, categoria ou barra usa
lime.

Isso não é preferência: sem essa regra, a cor da marca e a cor de "cliente
satisfeito" ficariam vizinhas e ninguém distinguiria controle de medição. Por isso
**promotor é teal, não verde** — precisa estar longe do lime.

---

## 2. Tokens

Tema escuro único, como o Kronos. Tokens em `app/globals.css`; consumo via classes
utilitárias do Tailwind. Nada de hex solto em componente.

### 2.1 Chassi (herdado do Kronos, não alterar)

| Token | Valor | Uso |
|---|---|---|
| `--background` | `oklch(0.141 0.005 285.823)` | fundo da aplicação |
| `--card` / `--popover` | `oklch(0.21 0.006 285.885)` | cartão, painel, sidebar |
| `--foreground` | `oklch(0.985 0 0)` | texto primário |
| `--muted` / `--accent` | `oklch(0.274 0.006 286.033)` | superfície secundária, hover |
| `--muted-foreground` | `oklch(0.705 0.015 286.067)` | texto auxiliar — **piso de contraste** |
| `--border` | `oklch(1 0 0 / 10%)` | separador, contorno |
| `--input` | `oklch(1 0 0 / 15%)` | contorno de campo |
| `--primary` / `--ring` | `oklch(0.843 0.179 134)` | marca, foco, item ativo |
| `--primary-foreground` | `oklch(0.22 0.05 134)` | texto sobre lime |
| `--destructive` | `oklch(0.704 0.191 22.216)` | erro |
| `--success` | `oklch(0.78 0.16 150)` | sucesso |
| `--warning` | `oklch(0.8 0.14 80)` | alerta |
| `--radius` | `0.625rem` | base; a escala `sm…4xl` deriva dela |

Superfícies "rich" (`--destructive-rich`, `--success-rich`, `--warning-rich` e as
variantes `-border` / `-text`) ficam reservadas a ênfase única e crítica, como o
Kronos as usa. Não decore com elas.

`--muted-foreground` é o **piso de cor de texto**. Nada mais claro que ele carrega
texto, e é ele que carrega o rótulo **"sem sinal"** — o estado que o produto existe
para não falsear.

### 2.2 Camada de dado (própria do Fraus)

Os `--chart-1..5` do Kronos são uma rampa monocromática de lime, correta para dado
sequencial e **errada aqui**: o Fraus precisa de séries distintas e de uma escala
divergente. Substitua-os.

**A metáfora, em séries:**

| Token | Valor | Significa |
|---|---|---|
| `--dito` | `oklch(0.80 0.15 60)` | fala, texto do cliente, emoji |
| `--dito-fraco` | `color-mix(in oklch, var(--dito) 18%, transparent)` | preenchimento, realce de trecho |
| `--medido` | `oklch(0.70 0.15 265)` | score, probabilidade, série de NPS |
| `--medido-fraco` | `color-mix(in oklch, var(--medido) 18%, transparent)` | faixa de referência, área |
| `--tempo` | `oklch(0.72 0.13 320)` | latência — **sempre tracejada** |

**Categorias de NPS — escala divergente.** Faixas fixas: **0–6 detrator · 7–8
neutro · 9–10 promotor**. Nunca redefina, e leia-as de `GET /modelo`, não do front.

| Token | Valor | Categoria |
|---|---|---|
| `--detrator` | `oklch(0.65 0.20 22)` | 0–6 |
| `--neutro` | `oklch(0.74 0.10 90)` | 7–8 |
| `--promotor` | `oklch(0.75 0.13 190)` | 9–10 |
| `--sem-sinal` | `var(--muted-foreground)` | sem dado — **jamais** na escala |

`--sem-sinal` é cinza de propósito: ausência de dado não pertence à escala de
satisfação. Pintá-la de vermelho seria afirmar insatisfação que ninguém mediu.

Quando uma cor de categoria carregar **texto** e não só preenchimento, verifique o
contraste contra `--card` e clareie o token se não cruzar 4.5:1. Cor de marcação e
cor de tipo não são a mesma coisa.

**Como isso está implementado.** Clarear caso a caso deixaria o mesmo token com
duas lightness espalhadas pelos componentes, então cada token de dado tem uma
variante `-texto` fixa — `--dito-texto`, `--medido-texto`, `--tempo-texto`,
`--detrator-texto`, `--neutro-texto`, `--promotor-texto`. A regra de uso é
simples: **preenchimento usa o token base, tipografia usa a variante `-texto`**.
As razões são verificadas por cálculo em `scripts/contraste.mjs`
(`npm run contraste`), que lê os tokens do próprio `globals.css` e testa cada
variante contra `--background`, `--card` e `--muted` — nenhuma lista duplicada,
então um token editado aparece no relatório sem ninguém lembrar. A menor razão
do conjunto é 5,66:1.

Os tokens de dado também expõem `--dito-fraco`, `--medido-fraco` e
`--tempo-fraco` (18% sobre transparente) para preenchimento de área e realce de
trecho, onde contraste de texto não se aplica.

### 2.3 Espaço, raio, tipografia

Espaço em múltiplos de 4. Raio sempre pela escala derivada de `--radius` — sem
pílulas totalmente arredondadas: o produto é instrumento de medição, não app de
consumo.

Fonte sem serifa para interface, **monoespaçada para todo número que se compara**
— score, nota, latência, percentual — com `tabular-nums` em coluna de tabela e em
cartão de indicador, sempre. Número que dança na vertical entre linhas é erro.

---

## 3. Modo e postura

Superfície **Operate**: quem chega vem completar uma tarefa — entender a qualidade
do atendimento e mexer na configuração da IA. Escaneabilidade, consistência e
expectativa nativa vencem expressão. A marca vive na precisão dos detalhes.

- **Densidade alta.** Painel de trabalho, não landing. Sem espaço em branco heroico
  entre números que precisam ser comparados.
- **Movimento só onde carrega informação** — transição de estado, entrada de dado,
  foco. Use a curva `--ease-fluid` do chassi, 120–200 ms. Respeite
  `prefers-reduced-motion` sem exceção.
- **Nenhum degradê em superfície de dado.** Degradê existe no logo. Em gráfico e
  cartão, cor chapada — degradê distorce leitura de área.
- **Elevação por borda e superfície**, não por sombra difusa.

---

## 4. Regras de visualização

Vêm da pesquisa que fundamenta o produto. Violar é erro factual, não divergência
de gosto.

### 4.1 A regra que não se negocia

**NPS e latência aparecem sobrepostos no mesmo gráfico.** Otimizar um KPI isolado
quebra outro — empurrar deflexão derruba CSAT. Cartões isolados escondem o
trade-off que o produto existe para mostrar.

Eixo duplo é antipadrão reconhecido, então vem com três mitigações obrigatórias:

1. Domínio **fixo** em cada eixo (NPS em −100…100, latência a partir de zero), para
   que o alinhamento entre as curvas não seja escolha arbitrária.
2. Cada eixo rotulado e colorido com sua série; latência sempre **tracejada**.
3. Visão de tabela no mesmo painel — quem precisa do número exato não depende da
   leitura cruzada.

### 4.2 Faixas de referência

Todo indicador com faixa conhecida mostra a faixa, não só o valor:

- **CSAT**: banda saudável 75–85% marcada no trilho.
- **Latência**: até 10s (pico de CSAT, ~84,7%), até 60s (saudável), até 180s
  (degradando, −2 a −3 pontos de CSAT por minuto), acima de 180s (abandono — 57%
  desistem). Cite a literatura corretamente; não invente limiar.

### 4.3 Honestidade

- **`score: null` é "sem sinal", nunca 0** — em célula, gráfico, ordenação, export.
  Nenhum `?? 0` no caminho de um score.
- **Agregado sem dado é estado vazio, não zero.** "NPS +0" sem medição é mentira
  com cara de medição.
- **O NPS é inferido do texto**, não perguntado ao cliente. Toda exibição carrega a
  etiqueta "estimativa" e a nota metodológica ao pé.
- **`importancias` ≠ `contribuicoes`.** A primeira é o peso global do modelo; a
  segunda é o que pesou naquele atendimento, com sinal. Exibi-las sem distinguir é
  o erro que derruba numa banca.
- **Estado vazio nomeia o que falta** — qual endpoint, qual etapa. Nunca preencha
  com número simulado.

---

## 5. Componentes

Use os primitivos do shadcn (`components/ui/`) como base. Componente novo se
explica como variação de uma destas famílias antes de existir.

**Cartão de indicador.** Rótulo, número (mono, tabular), unidade, trilho com faixa
de referência quando houver, e etiqueta de qualificação (`estimativa`, `sem dado`)
quando couber. Falha isolada: um cartão que não carrega mostra o próprio erro sem
derrubar os vizinhos.

**Tabela.** Cabeçalho fixo, números tabulares à direita, ordenação que manda `null`
para o fim nos dois sentidos, linha clicável com foco visível, rolagem horizontal
própria — o `body` nunca rola na horizontal.

**Painel de gráfico.** Título, subtítulo com a fonte ou o método quando o número
for derivado, o gráfico, e a alternância para tabela. Altura fixa por breakpoint;
gráfico que muda de altura ao trocar de dado causa salto de layout.

**App shell.** Sidebar (primitivo `sidebar` do chassi) com o logo, as três
seções de leitura — Visão geral, Atendimentos, Modelo —, o grupo **Ajustes**
com as duas telas que mexem no sistema — Configurações e Integrações — e o
estado de saúde da API sempre visível no rodapé. Os dois grupos são separados
de propósito: olhar e mexer não são a mesma postura. A seção ativa se marca por `aria-current="page"` **e** por
uma barra de 2px em `--primary`: item ativo é o único lugar onde o lime toca a
navegação, e cor nunca é o único canal.

**Filtro de período.** É global e mora na **URL** (`?de=&ate=`), não em estado
de cliente: as páginas são de servidor, o recorte fica compartilhável, e existe
uma fonte só do que "o período" significa — indicador, série, tabela e export
nunca divergem. Todo link da navegação carrega o recorte adiante. Os atalhos se
ancoram no **último dia com dado**, não em `hoje`, e mostram o intervalo real que
aplicam; ancorar em hoje devolveria recorte vazio sem explicar por quê. Uma
seção que o filtro não afeta — a de Modelo — não exibe o filtro.

**Tela de configuração.** Um painel por grupo de valores, e três regras:

1. **A validação mora no servidor.** O `400` da API nomeia o problema ("buraco
   entre detrator e neutro: nenhuma faixa cobre a nota 6") e é essa frase que
   aparece na tela — nunca "erro ao salvar". Reimplementar a regra no
   TypeScript criaria a segunda fonte da mesma verdade que este projeto já
   pagou uma vez para não ter.
2. **A consequência vem antes do botão.** Mexer nas faixas reclassifica
   atendimento já pontuado (a categoria é derivada na leitura; o `score` não é
   recalculado). Quem aperta salvar lê isso antes de apertar.
3. **Voltar ao padrão usa os valores de fábrica que o `GET` devolve**, nunca
   números digitados de novo na interface.

O controle só existe se a API persistir o valor **e** ele mudar comportamento.
Não há interruptor por sinal (texto/emoji/tempo): os três estão fundidos nos
coeficientes de um modelo treinado, e um controle que não faz o que diz é pior
que a ausência dele. A tela declara essa ausência em vez de escondê-la.

**Segredo, nunca.** Onde a interface fala de credencial, o campo é o **nome de
uma variável de ambiente** — não existe campo de senha em tela nenhuma, e o
rótulo diz isso, porque alguém vai tentar colar um token ali. `configurada:
false` significa "a variável não existe no ambiente da API", não "a credencial
está errada".

**Ação destrutiva.** A confirmação diz o que a ação NÃO faz, quando isso for a
dúvida real: remover uma fonte apaga o cadastro da origem e nenhum atendimento.
Confirmação inline no lugar de modal — a tela é de trabalho, não de interrupção.

**Contribuição × importância.** As duas nunca aparecem com a mesma forma. Peso
global (`importancias`) é barra que cresce da esquerda, colorida por tipo de
sinal, e vive na tela Modelo. Contribuição daquele atendimento (`contribuicoes`)
é barra divergente saindo de um eixo central, na escala detrator/promotor, e
vive na tela do atendimento. Copy, geometria e cor dizem a mesma coisa três
vezes.

---

## 6. Acessibilidade — piso, não meta

- Contraste **AA (4.5:1)** para todo texto, verificado por cálculo.
- Cor **nunca** é o único canal: categoria carrega rótulo textual; séries se
  distinguem também por traço (contínuo vs. tracejado).
- Foco visível em tudo que recebe teclado, usando `--ring`.
- Tabela com semântica de tabela. Ícone sozinho sempre com rótulo acessível.
- Alvo de toque mínimo 44×44 px em telas estreitas.

---

## 7. O que este documento proíbe

- Lime em dado. Ele é da marca.
- Hex solto fora dos tokens.
- Cor de categoria de NPS usada para outra coisa.
- Zero no lugar de ausência de dado.
- Número inventado, simulado ou de exemplo em tela.
- Degradê ou sombra difusa em superfície que carrega dado.
- Texto mais claro que `--muted-foreground`.
- Gráfico sem eixo rotulado.
- Animação que não carrega informação.
