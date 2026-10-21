# Widgets em camadas e céu vivo — design

Data: 21/10/2026. Branch: `feat/widgets-camadas`, a partir da `main` (`1fd85e1`).
Mockups aprovados (descartáveis, fora do repositório) em `.superpowers/brainstorm/`:
`widgets-v1.html` (direção C), `dashboard-intensidade.html` (opção 2) e
`fundo-vivo.html` (céu).

## Por que

O João acha os botões, cards e o texto do Fraus com "cara de não profissional":
parecem componentes padrão com a cor trocada. A LP também tem um fundo simples
demais (`.lp::after`, riscos em `repeating-linear-gradient` e um brilho radial).
Ele desenhou duas artes de fundo, uma escura com pontos dourados e riscos
diagonais e outra dourada só com riscos, e quer as duas na LP. Os widgets novos
precisam servir à LP e à dashboard.

## O que foi decidido (pelo João)

1. **Direção C, "Camadas do FR"**, para botões, cards e texto. A peça repete a
   linguagem do monograma: placas empilhadas que se abrem no hover, como a
   extrusão do FR, e cantos cortados na diagonal da fenda. A palavra-chave do
   título recebe uma pincelada dourada inclinada.
2. **Na LP, a C entra inteira.** O botão primário tem três placas (ouro,
   `#a8904f` e `#6f5f36` no escuro), e no hover a da frente sobe e a de trás
   desce. O botão secundário tem canto cortado, contorno simples e um fio
   dourado que cresce embaixo no hover. Os cards têm a face e duas placas atrás,
   que se abrem no hover, e um fio dourado no topo à direita.
3. **Na dashboard, a C fica contida (opção 2 de `dashboard-intensidade.html`).**
   O canto cortado aparece em botões, controles e cards. O botão primário mantém
   as três placas da LP, menores. Os botões secundários seguem o `.btn.o`, com
   canto, contorno e fio dourado que cresce no hover, sem placas. A faixa de
   indicadores vira quatro cards separados, como no mockup aprovado. Card que
   não é clicável não ganha placa, porque a placa avisa "isso é clicável". O
   fio dourado no topo marca o NPS na faixa e o painel `dominante`.
4. **O fundo da LP vira o céu da arte dele, em movimento:** pontos dourados que
   piscam em ritmos diferentes e riscos finos que descem devagar na diagonal da
   arte (cerca de −22° da vertical). No fecho dourado (`.lp.inv`) os pontos
   somem e os riscos escurecem, como na arte `fraus-bg-gold.png`. A densidade e
   a velocidade do protótipo `fundo-vivo.html` foram aprovadas: cerca de 140
   pontos, 60% piscando com ciclos de 2,5 a 7 s, e 26 riscos com descida de 14
   a 30 s.
5. **Fica intocado:** a coreografia GSAP, o FR, o palco WebGL e suas poses, as
   seções, a ordem delas e os textos. Mudam só o fundo e a aparência dos widgets.

## Escopo

### Fundo (LP)

- Substitui o `.lp::after` atual. O céu continua `position: fixed` atrás de
  tudo (`z-index: 0`, abaixo do `.lp-palco` WebGL em `z-index: 1`) e sem
  ponteiro.
- **Só CSS, sem canvas e sem script por quadro.** Anima apenas `opacity` e
  `transform`/`translate`. É sobre isso que muda a regra do DESIGN.md (ver
  "Documentação").
- **Determinístico e renderizado no servidor:** as posições saem de um PRNG com
  semente fixa ou de uma lista gerada uma vez, nunca de `Math.random()` no
  render, porque isso quebraria a hidratação.
- `prefers-reduced-motion: reduce` deixa o céu parado e com a mesma cara da
  arte. A regra global de reduce do `lp.css` já zera `animation`, então basta
  conferir que o céu parado fica correto, com os riscos visíveis.
- A troca para o dourado acompanha a classe `inv` que a coreografia já liga e
  desliga. Nenhum código da coreografia muda.
- Celular: o mesmo céu, e cabe ao construtor reduzir a densidade se o custo
  medido pedir.

### Widgets da LP (`app/lp.css` e marcação mínima)

Peças afetadas: `.btn` e `.btn.o` (Hero, Topo/Entrar, Analista, Fecho),
`.stat` (Hero), `.card` (Sinais e Limites), `.ck li` (Problema), `.tag`,
`.step` (Analista), as abas e o resumo das leituras gravadas (`.ln-aba`,
`.leituras-gravadas summary`), além dos títulos `h1`, `h2` e `h3`.

Restrições que vêm da coreografia e não podem quebrar:

- **`data-embaralhar` reescreve `el.textContent`** no `pointerenter` e na
  entrada da `.tag`. Qualquer elemento filho dentro de `.btn` ou `.tag` é
  apagado no primeiro hover. **As placas precisam ser pseudo-elementos**
  (`::before` e `::after`) ou ficar fora do elemento embaralhado, e o nome
  acessível que a coreografia fixa em `<a>` continua valendo.
- **`.mag`** desloca o botão com o ímã, então as placas acompanham o próprio
  elemento.
- **`.rv`, `.step` e `[data-passos]`** recebem `opacity`/`x`/`scaleY` do GSAP, e
  as placas não podem depender de `transform` no mesmo elemento de um jeito que
  conflite com o GSAP.
- **Títulos** são quebrados em `.w > span`, com máscara `overflow: hidden`, para
  a palavra subir. A pincelada fica dentro da máscara ou a máscara ganha folga,
  porque a pincelada não pode sair cortada.
- **`.lp.inv`** inverte cores no fecho, e as placas e a pincelada precisam de
  variantes nesse estado (o protótipo inverte para placa grafite e texto ouro).

**Pincelada:** cai em "análise", em "A análise começa." do Hero. Exige marcar
essa palavra (o `Palavras` hoje recebe só texto). O texto e o layout não mudam.
Pinceladas em outros `h2` ficam fora deste trabalho.

### Widgets da LP: peça por peça

| Peça | Tratamento |
|---|---|
| `.btn` | três placas (`::before` e `::after` mais o próprio fundo, ou outra montagem sem filhos), que se abrem no hover |
| `.btn.o` | canto cortado, contorno e fio dourado que cresce embaixo |
| `.card` e `.stat` | face com canto cortado e duas placas atrás, que se abrem no hover; fio dourado no topo à direita. A `.stat` ganha a marca diagonal da fenda no canto, como no mockup C |
| `.ck li` | canto cortado e fio, sem placas: é lista, não card |
| `.step` | não vira caixa; só o marcador da linha do tempo troca o círculo por um quadrado com o canto cortado (o `::before` já existe e o GSAP move o `.step`, não o marcador) |
| `.tag` | canto cortado pequeno, sem placas |
| `.ln-aba` e o `summary` das leituras | canto cortado, como o `.btn.o` |

### Widgets da dashboard

- **`components/ui/button.tsx`**, com mudança **global**. Telas fora do escopo
  que usam `Button`, como `FormularioAuth` e a sidebar, herdam a forma nova, e
  isso é aceito para manter o produto coerente.
  - `default`: canto cortado e placas da LP, menores (a placa de trás aparece
    em repouso e se abre no hover).
  - `outline` e `secondary`: canto, contorno e fio dourado no hover, sem placas.
  - `destructive`: canto, sem placas e sem fio dourado (ouro é ação, não alerta).
  - `ghost`, `link` e os tamanhos `icon*`: sem canto e sem placa, porque o
    corte num quadrado de 24 a 36 px vira ruído.
  - O tamanho do corte acompanha o tamanho do botão.
- **Controles** (`input`, `select`, `textarea` e os gatilhos de `tabs`): canto
  cortado, para não ficar botão cortado ao lado de campo arredondado na mesma
  barra. Sem placas.
- **`CartaoIndicador` e `FaixaIndicadores`:** a faixa deixa de ser uma caixa
  com divisórias e passa a ter quatro cards com canto cortado e espaço entre
  eles (quatro colunas em tela larga, duas nas menores, como hoje). O NPS leva o
  fio dourado. As regras de impressão da faixa precisam continuar legíveis.
- **`Painel` e `lib/hierarquia.ts`:** o nível `dominante` ganha canto cortado e
  fio dourado. O `apoio` continua só com a linha no topo, sem virar caixa, para
  não disputar peso.
- **Regiões com caixa própria** (`.superficie` usada direto nas páginas e
  `alert`): canto cortado, sem fio.
- **Sobreposições** (tooltip, popover, sheet e menus): ficam como estão.
- `components/ui/badge.tsx` ganha o canto da `.tag` da LP.
- **Tema claro:** as mesmas formas, com as cores das placas derivadas dos
  tokens do claro e não fixadas em hexadecimal do escuro.

### Uma fonte para as duas superfícies

Hoje a LP usa classes próprias no `lp.css` e a dashboard usa `cva` com
Tailwind. A forma (o polígono do canto, as placas, o fio e a pincelada) passa a
ter **uma única definição**, com intensidade `lp` (inteira) ou `ferramenta`
(contida), consumida pelos dois lados. O mecanismo (arquivo CSS compartilhado,
utilitários do Tailwind ou variáveis) fica a cargo do construtor, desde que não
existam duas cópias do polígono ou das cores das placas.

## Restrições de acessibilidade e de produto

- **`clip-path` corta o anel de foco e o `outline`.** Todo controle com canto
  cortado continua com foco visível, nos dois temas e na LP. Isso precisa ser
  verificado, não suposto.
- Alvo mínimo de 44 px na LP, como já é hoje.
- Contraste AA mantido: o texto escuro sobre o ouro e o texto ouro sobre a placa
  grafite do fecho passam no `npm run contraste`.
- Ouro continua sendo ação e marca, nunca dado. A pincelada e o fio são
  identidade, não valor.
- Sem dependência nova.

## Fora do escopo

Coreografia, FR, palco WebGL, partículas do palco, seções, a ordem delas, os
textos, o Lenis, o layout da tela de acesso (`/entrar`, `/cadastrar`), gráficos,
tabelas e o layout da sidebar. Os botões dessas telas herdam a forma nova pelo
`Button`.

## Documentação

O `dashboard/DESIGN.md` é atualizado na mesma entrega:

- o fundo contínuo da LP passa a ser o céu animado em CSS, com o comportamento
  no reduce e no fecho;
- "controles de 8px e regiões de 12px; borda simples" vira canto cortado, com
  as duas intensidades;
- o trecho da dashboard que proíbe fundo animado continua valendo, porque a
  dashboard não recebe o céu.

## Verificação

`npm test`, `npm run lint`, `npm run build`, `npm run contraste`,
`npm run pisos` e `npm run test:lp` (o validador da LP confere embaralhar,
reduce, fecho e celular). Além deles, capturas da LP em desktop e celular e no
fecho, e da visão geral da dashboard nos dois temas, olhadas de fato.

## Escolhas da Neuro

- Placas em pseudo-elementos, por causa do `data-embaralhar`.
- Uma só definição de forma para as duas superfícies, com o mecanismo livre.
- `Button` mudado de forma global: auth e sidebar herdam a forma nova.
- Card não clicável sem placa; o fio dourado no NPS e no painel dominante.
- `apoio` continua sem caixa; sobreposições continuam como estão.
- Controles ganham canto; `ghost`, `link` e os botões de ícone, não.
- `.ck li` sem placas; `.step` muda só o marcador.
- Tabelas, gráficos e as telas de acesso não mudam de layout.
