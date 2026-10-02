---
name: Fraus — Instrumento
description: Painel de instrumento de laboratório sobre quase-preto neutro; todo número é um display de sete segmentos e a ausência de dado é um segmento apagado.
colors:
  background: "oklch(0.14 0.004 285)"
  foreground: "oklch(0.96 0.003 285)"
  card: "oklch(0.185 0.005 285)"
  popover: "oklch(0.175 0.005 285)"
  sidebar: "oklch(0.16 0.004 285)"
  muted: "oklch(0.245 0.006 285)"
  muted-foreground: "oklch(0.74 0.01 285)"
  linha: "oklch(0.96 0.003 285 / 26%)"
  compasso: "oklch(0.96 0.003 285 / 9%)"
  border: "oklch(0.96 0.003 285 / 13%)"
  primary: "oklch(0.83 0.095 84)"
  primary-foreground: "oklch(0.15 0.02 84)"
  dito: "oklch(0.78 0.14 72)"
  dito-texto: "oklch(0.85 0.125 72)"
  medido: "oklch(0.74 0.13 250)"
  medido-texto: "oklch(0.82 0.105 250)"
  detrator: "oklch(0.67 0.24 22)"
  neutro: "oklch(0.78 0.15 90)"
  promotor: "oklch(0.79 0.18 190)"
  sem-sinal: "oklch(0.705 0.015 286.067)"
  destructive: "oklch(0.79 0.121 22.216)"
  success: "oklch(0.78 0.16 150)"
  warning: "oklch(0.8 0.14 80)"
  atelie-halo: "oklch(0.62 0.2 320)"
typography:
  display-vitrine:
    fontFamily: "Bricolage Grotesque, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(2.6rem, min(8vw, 10.5vh), 6.5rem)"
    fontWeight: 500
    lineHeight: 0.95
    letterSpacing: "-0.035em"
  titulo-vitrine:
    fontFamily: "Bricolage Grotesque, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(2.1rem, 4.6vw, 3.75rem)"
    fontWeight: 500
    lineHeight: 1.02
    letterSpacing: "-0.028em"
  titulo-instrumento:
    fontFamily: "Martian Mono, ui-monospace, Cascadia Mono, monospace"
    fontWeight: 500
    letterSpacing: "-0.02em"
  rotulo-instrumento:
    fontFamily: "Martian Mono, ui-monospace, Cascadia Mono, monospace"
    fontSize: "0.6875rem"
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: "0.14em"
  prosa:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.0625rem"
    lineHeight: 1.7
  dado:
    fontFamily: "Martian Mono, ui-monospace, Cascadia Mono, monospace"
    fontFeature: "tabular-nums"
rounded:
  none: "0"
  pilula: "999px"
  cabeca: "50%"
spacing:
  telemetria: "34px"
  gutter-vitrine: "clamp(1rem, 4vw, 3rem)"
  secao-vitrine: "clamp(4.5rem, 9vw, 8rem)"
  pauta: "13px"
components:
  telemetria-topo:
    backgroundColor: "{colors.background}"
    textColor: "{colors.muted-foreground}"
    typography: "{typography.rotulo-instrumento}"
    height: "34px"
  painel:
    backgroundColor: "{colors.card}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.none}"
    padding: "16px 20px"
  botao-primario-vitrine:
    backgroundColor: "{colors.background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.none}"
    padding: "0 1.6rem"
    height: "3rem"
  botao-acessar-nav:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.pilula}"
    padding: "0.6rem 1rem"
  segmento-led:
    textColor: "{colors.medido}"
---

# Design System: Fraus — Instrumento

Registrado em 30/09/2026 a partir do que foi **construído** (`app/globals.css`, `app/vitrine.css`, `components/instrumento/**`, `components/lp/**`, `components/shell/**`), não do plano. Substitui por inteiro o mundo "Pauta / espaço profundo", que foi descartado; o que dele continua vivo está aqui, com o motivo. Contrato da rodada: `docs/superpowers/specs/2026-09-30-instrumento-design.md`. Verdade de produto: `PRODUCT.md`.

## Overview

**Creative North Star: "O Instrumento de Bancada"**

Um painel de laboratório sobre quase-preto neutro. Todo número medido é um display de sete segmentos; o segmento **apagado também é desenhado**, então "sem sinal" é um medidor ligado que não leu nada, nunca um `0`. É a invariante 2 do CLAUDE.md virada objeto. Superfície é retângulo de hairline de 1px, raio zero, rótulo em mono caixa alta. Nada de cartão colorido, nada de cenário: o único cenário que sobra é o orbe da vitrine.

A tese que atravessa a interface inteira não mudou: **o dito fica acima da régua, o medido abaixo**. Âmbar é o que o cliente articulou (fala, texto, emoji); azul é o que o sistema mediu (score, probabilidade, latência, tendência). O produto vende a distância entre os dois, então ela nunca pode ficar invisível. O LED é azul porque número é medido.

Fusão aprovada pelo dono sobre mockups estáticos (seed 197a1d0c): **Régua** (telemetria, hairlines, mono, nav numerado, a régua dito/medido) + **Segmento** (LED, apagado = ausência, lâmpada sempre com palavra) + **Aurora** (só na vitrine: orbe, headline gigante, nav de vidro em pílula, CTA de borda cônica, halo e grão). **Tinta e tom** foi retirado da fusão por decisão do dono: nada de balão, halftone, linhas de velocidade ou sarjeta.

**Key Characteristics:**
- Quase-preto neutro (croma 0,004) com traço de matiz 285; degraus de superfície são passos de claridade, não de cor.
- Hairline 1px e raio 0; a linha de 26% (`--linha`) **afirma**, a de 9% (`--compasso`) só agrupa.
- Martian Mono em rótulo, dado e título de tela; Inter na prosa; Bricolage só no display da vitrine.
- Três cores com dono: âmbar dito, azul medido, dourado só em ação, foco e marca. Magenta só no orbe e no halo.
- Um momento vivo na vitrine (o orbe); a ferramenta é estática.

## Colors

Estratégia: **neutro quase-preto restrito, com duas vozes de dado e um metal de marca**. Tudo em OKLCH; o frontmatter é a fonte normativa e `scripts/contraste.mjs` só lê `oklch()` literal.

### Primary
- **Ouro fosco do monograma** (`--primary`, oklch 0.83 0.095 84): cor de **ação e foco**, medida do próprio `public/fraus-logo.svg`. Preenche controle, anel de foco, cursor `█` do nav ativo, o `00` da telemetria. **Nunca** codifica dado. Separa-se do âmbar do dito pelo croma (fosco 0,095 contra saturado 0,14): metálico contra pigmento; e por nunca dividirem superfície.

### Secondary (as duas vozes)
- **Âmbar do dito** (`--dito` 0.78 0.14 72; texto `--dito-texto` 0.85 0.125 72): fala, texto, emoji. Acima da régua.
- **Azul do medido** (`--medido` 0.74 0.13 250; texto `--medido-texto` 0.82 0.105 250): score, probabilidade, latência. Abaixo da régua. Cor padrão do `SegmentoLED`.
- Variantes `-fraco` (18% de mistura) para preenchimento; `-texto` para tipo. Cor de marcação e cor de tipo não são a mesma coisa.

### Tertiary (categorias, famílias, grafo)
- **Escala de NPS**: `--detrator` (0.67 0.24 22), `--neutro` (0.78 0.15 90), `--promotor` (0.79 0.18 190, teal, longe do dourado de propósito). Sempre com rótulo escrito.
- **Sem sinal** (`--sem-sinal`, 0.705 0.015 286): cinza fora da escala, de propósito.
- **Famílias do fusor**: `--emocao` (10), `--lexico` (140), `--ironia` (230), `--estilo` (170), `--tempo` (320, série sempre tracejada). Cada família tem `-fraco` e `-texto`; matiz de nenhuma é reciclado. `--outros-sinal` é cinza para prefixo que nenhuma família reconhece.
- **Sete emoções** (`--emo-medo` 315, `-nojo` 160, `-tristeza` 245, `-raiva` 0, `-surpresa` 280, `-alegria` 125, `-neutro` cinza acromático): cor de **marca, nunca de texto**. Validadas por vizinhos na ordem fixa da pauta (`ORDEM_EMOCOES` em `lib/partitura.ts`: medo, nojo, tristeza, raiva, surpresa, alegria, neutro). Nove cores num painel não se separam sozinhas; o que as legitima é o nome escrito em cada linha e a validação por vizinhos (CVD ΔE 12,5, visão normal 16,2, ≥3:1 sobre o card, medidos em 15/09/2026). Trocar um tom ou a ordem sem rodar o validador desfaz a medição. Desprezo (raiva + nojo) é a nota vazada no tom da raiva.
- **Grafo, nove tipos de nó**: `--no-*` com L 0,79 / C 0,19 iguais e só o matiz variando. Quente (30–95) = dito: emoji 30, conversa 60, termo 95. Frio (150–340) = medido/cadastrado: fonte 150, canal 195, feature 265, categoria 305, desfecho 340. `--no-importacao` é cinza (0.7 0 0): nó solto sem origem rastreável, ausência de afirmação. Claridade igual é deliberada: nenhum tipo é mais importante que outro. A tela carrega legenda própria agrupada nas duas famílias.
- **Erro / sucesso / aviso**: `--destructive`, `--success`, `--warning` (este compartilha o matiz do dourado e só vive como texto, nunca como preenchimento) e as trincas `-rich`, `-rich-border`, `-rich-text`.

### Neutral
- **Quase-preto** (`--background`), **card** 0.185, **popover** 0.175, **sidebar** 0.16, **muted/secondary/accent** 0.245. Não é preto puro: preto puro faz a régua de meio ponto flutuar no vácuo (argumento herdado do grafite).
- **`--muted-foreground`** (0.74 0.01 285) é o **piso de cor de texto**: nada mais escuro que isto carrega texto.
- **Halo** (`--atelie-halo`, magenta 0.62 0.2 320): cenografia da vitrine. Sem canal de significado.

### Named Rules
**A Regra do Dito e do Medido.** Âmbar acima da linha, azul abaixo. Onde as duas séries são medidas (NPS × latência) a régua **não** entra, senão vira notação decorativa. `Painel` aceita a prop `regua` só quando o dado realmente se divide.
**A Regra do Ouro Fora do Dado.** `--primary` nunca aparece numa série, barra, categoria ou célula. Só ação primária, foco de teclado, cursor do nav, valor de telemetria e a marca. Uma exceção nomeada legada: o cursor de leitura da partitura (não codifica valor).
**A Regra do Magenta Cenográfico.** Magenta só no orbe, no halo e na borda cônica do CTA da vitrine. Nunca em dado.
**A Regra do Piso.** Todo par de cor que carrega texto cruza AA (4,5:1) por cálculo. O portão manda no vidro; o vidro nunca afrouxa o portão.

## Typography

**Display Font:** Bricolage Grotesque (fallback `ui-sans-serif, system-ui`), **só na vitrine**.
**Body Font:** Inter (fallback pilha de sistema), com `cv01` e `ss03`.
**Label/Mono Font:** Martian Mono (fallback `ui-monospace, Cascadia Mono, Consolas`).

Todas por `next/font/google` no `app/layout.tsx`, baixadas no build e servidas do próprio deploy: zero rede em runtime. Variáveis: `--fonte-martian`, `--fonte-inter`, `--fonte-bricolage`; tokens de uso `--fonte-mono`, `--fonte-sans`, `--fonte-display`.

**Caráter:** mono de instrumento para tudo que é rótulo ou número, prosa humana onde mono cansa, e um display de contraste violento apenas onde o visitante chega de passagem.

### Hierarchy
- **Display da vitrine** (`.display-vitrine`, 500, `clamp(2.6rem, min(8vw, 10.5vh), 6.5rem)`, 0,95, -0,035em): manchete. O teto depende da altura (`min` com `vh`) para o hero não estourar em monitor largo e baixo. No hero o `h1` sobrepõe corpo `clamp(2.6rem, min(8.4vw, 10svh), 5.6rem)` e peso 800; o `.vt-sec .titulo-vitrine` sobe para 700.
- **Título de seção da vitrine** (`.titulo-vitrine`, 500, `clamp(2.1rem, 4.6vw, 3.75rem)`, 1,02, -0,028em).
- **Título de tela** (`.titulo-instrumento`): mono, 500, caixa alta, -0,02em. Nunca display.
- **Rótulo** (`.rotulo-instrumento`, 0,6875rem, 0,14em, caixa alta, `muted-foreground`): campo, painel, telemetria, grupo do menu.
- **Dado** (`.num`): mono + `tabular-nums`. Todo número comparável.
- **Prosa** (Inter): transcrição, explicação, aparato; na vitrine `.vt-prosa` 1,0625rem / 1,7, máx. 34rem.

### Named Rules
**A Regra dos 11px.** Nenhum texto abaixo de 11px (0,6875rem); a banca lê em projetor. `lib/tipografia.test.ts` varre TSX por `text-[..]` e o `globals.css` por `font-size` literal.
**A Regra da Display Contida.** Bricolage entra só via `.display-vitrine` e `.titulo-vitrine`, ambas em `globals.css`. `tipografia.test.ts` falha se `--fonte-display` ou `--fonte-bricolage` vazar para qualquer outra regra, ou se `--fonte-sans`/`--fonte-mono` deixarem de apontar para Inter/Martian. `vitrine.css` sobrepõe só tamanho e peso, nunca família.
**A Regra do Tracking Inverso.** Tipo grande fecha (-0,03 a -0,04em), rótulo pequeno abre (0,12 a 0,16em). A escala da vitrine não vale para a dashboard.

## Layout

**Dashboard.** Pilha de "sistemas" (`Painel`), não grade de cartões: quem agrupa é espaço mais régua. Cada tela abre com a telemetria de 34px, depois a **armadura horizontal** (quatro células lado a lado, largura total, mesma altura curta, separadas por régua), depois o painel dominante. Um dominante por tela (`lib/hierarquia.ts`, `DOMINANTE_POR_TELA`); `apoio` é o padrão para ninguém virar dominante por omissão. Padding: dominante `p-4 sm:p-6`, apoio `p-4 sm:p-5`. Nav lateral colapsável para 32px (só o número sobrevive).

**Vitrine (01/10/2026).** `.vt-wrap` máx. 82rem com gutter `clamp(1rem, 4vw, 3rem)`; seções com `padding-block: clamp(4.5rem, 9vw, 8rem)` separadas por hairline `--compasso`. Ordem: hero (manchete à esquerda, orbe à direita), constelação fixada, sem sinal, sistema em linhas, fecho. Abaixo de 900px a constelação empilha (palco em cima, texto embaixo) e os rótulos das famílias saem do palco — a contagem segue no texto.

**A dobra por altura.** A manchete do hero usa `clamp(3rem, min(9.2vw, 13.5vh), 8.75rem)`: a 1280×720 o CTA fica acima da dobra. No celular o orbe ocupa o topo e o hero abre com `padding-top: 74vw` para o título começar abaixo dele (orbe atrás de manchete derruba o contraste). O `body` nunca rola na horizontal (`.vt` usa `overflow-x: clip`, que não quebra o `sticky`). Mobile 390 sem corte.

**Ritmo.** Pauta de 13px, peso 1px, opacidade 0,03 (papel de ensaio virou ruído de instrumento). Grade de 1px da seção Sistema: `gap: 1px` sobre fundo `--linha`.

### Named Rules
**A Regra da Dobra.** Toda mudança no hero se confere a 1280×720 e a 390px de largura: CTA visível, sem rolagem horizontal.
**A Regra da Régua Única.** Só a linha `--linha` afirma; filete interno é `--compasso`. Não empilhe bordas.

## Elevation & Depth

**Plano por padrão; profundidade é opacidade e hairline.** A superfície é quase opaca (fino/médio ~90–92% de `--card`, denso 97%), com `border: 1px solid var(--linha)` e uma sombra de assentamento `0 1px 0 oklch(0 0 0 / 30%)`. Sem quina iluminada, sem halo, sem chanfro. Blur só onde há sobreposição real: o denso (`blur(16px) saturate(1.2)`: popover/sheet), a faixa sticky do cabeçalho (`blur(12px)`) e o nav de pílula da vitrine (`blur(14px) saturate(1.3)`). Sem `backdrop-filter` o navegador recebe o **piso** opaco (`--vidro-*-piso`), medido por `npm run pisos`.

As classes `.vidro-fino`, `.vidro`, `.vidro-denso` e `.chanfro` **permanecem** (30 componentes as carregam) mas o Instrumento as reduz a hairline e `clip-path: none`; só o tema chuva as reativa por baixo. Pisos medidos em 30/09/2026: 0.192 / 0.191 / 0.188.

O ateliê é **calmo**: planeta, estrelas, grade laser, sol listrado e marca impressa em opacidade 0; sobra a mancha fria a 0,07 e o papel pautado. A mancha dourada foi zerada na revisão final porque esquentava cabeçalho e sidebar; **o dourado é ação, foco e marca, não luz de ambiente**.

### Named Rules
**A Regra da Espessura como Opacidade.** Vidro engrossa por opacidade, nunca por luz baixa. Par que reprova no `contraste` faz a espessura ganhar opacidade.

## Shapes

**Raio zero** (`--radius: 0`): retângulo de hairline. O chanfro de 45° do F e do R saiu junto com o vidro. Exceções explícitas, sempre com `rounded-full`: a cabeça da categoria, o ponto de status, o nav em pílula da vitrine (999px), o orbe (50%). Botão da vitrine é retangular. Marcadores de lâmpada são quadrados de 0,5rem com brilho.

## Components

### SegmentoLED (peça-assinatura)
`components/instrumento/SegmentoLED.tsx` + `lib/segmentos.ts` (parte pura, testável sem React).
- **Alfabeto:** `0-9`, `-` (e o menos tipográfico U+2212, mesmo sinal), `+` (segmento do meio + traço vertical), `,`, `.`, `:`, espaço. Caractere fora do alfabeto **não some**: entra como texto cru em mono (um display que engole caractere muda o número em silêncio).
- **Vírgula com cauda:** a vírgula do pt-BR é um ponto com cauda descendo à esquerda; o ponto (`.`) é célula própria, só círculo. Sem a cauda, `66,1` lia como `66.1` (milhar em pt-BR).
- **`null` é apagado:** renderiza N células (padrão 3) com os sete segmentos a 10% de opacidade, nunca `0`. `aria-label` vira `${rotulo}: sem sinal`.
- **`rotulo` obrigatório:** SVG de polígonos não diz nada a leitor de tela, e "2,9" de quê não diz nada a quem vê.
- **Não calcula, não arredonda, não converte.** Recebe a string já formatada em pt-BR (`formatarNps`, `formatarSegundosLED`...). Uma fonte só de formatação (invariante 3).
- **Cor:** `medido` (azul, padrão), `marca` (dourado, fatos da marca), `tinta` (foreground, observado e não inferido), `erro` (só o easter egg). Brilho: um `drop-shadow(0 0 3px currentColor)` no grupo aceso, não por polígono. Sem estado, serve em Server Component.

### TelemetriaTopo
Faixa de 34px no topo de cada tela: mono 11px, caixa alta, 0,14em, `border-b border-linha`, fundo `--background`. Carrega **só fatos verdadeiros do produto** ("NPS ESTIMATIVA", "LLM 00"), nunca métrica inventada. `TelemetriaValor` põe o valor em dourado (marca, não dado). O lado direito some abaixo de `sm`. `TelemetriaDaRota` escolhe pela rota.

### Navegação numerada
Lateral: mono 11px, caixa alta, filete inferior, sem raio. Item `01_VISÃO GERAL` com o **cursor `█` dourado** na tela ativa; ativa também leva `aria-current="page"` (cor nunca é o único canal). A numeração vem de `lib/navegacao.ts`, a mesma fonte da telemetria; a ordem é a da tela e não a do papel (`usuario` vê 01 e 02, que continuam sendo 01 e 02). Grupos: Seções (5 de olhar), Referência (docs, aparece só com `NEXT_PUBLIC_URL_DOCS`, ícone de saída, aba nova), Ajustes (só `dev`). Rodapé: "Modelos locais / Sem LLM em runtime". Cada item carrega o período na URL.

### Painel (hairline)
Sistema de largura total: cabeçalho com `rotulo-instrumento` e `border-b border-linha`; corpo; prosa metodológica sobe para o **aparato da tela** (`RessalvaDaTela`), recolhível mas nunca removida. Rótulos curtos (`estimativa`, `observado`, `sem sinal`) ficam colados ao dado. Props `erro` e `vazio` substituem o conteúdo no lugar dele; `regua` divide dito/medido. Entrada: sobe 8px uma vez ao entrar em cena (`whileInView` + `once`).

### Armadura de indicadores
`FaixaIndicadores`: quatro células em fileira, rótulo + LED, sem barra de progresso decorativa. NPS e CSAT levam "estimativa" e o sublinhado pontilhado (`.estimado`); contenção e latência são observadas e não levam. Cada célula falha sozinha.

### Cabeça da categoria (`EtiquetaCategoria`, slot único)
Três formas, nesta ordem de honestidade, num só componente que tabela, piores atendimentos, ficha do grafo e tela do atendimento atravessam:
- **cheia**: medido, com evidência, ponto colorido.
- **tracejada**: medido, evidência **fraca**, anel tracejado **na cor da classe**; texto por extenso "evidência fraca: motivo". Vem do servidor (`fraus/evidencia.py`), derivada de fala observável (quantas mensagens e palavras), **nunca** da probabilidade do modelo: probabilidade não calibrada não é confiança.
- **vazada**: não medido, anel oco cinza (`CabecaVazada`), nunca quarto ponto cheio; escreve "sem sinal" por extenso.
Um componente irmão daria três formas em quatro lugares, e o que ninguém lembrasse de trocar continuaria mentindo confiança.

### Vitrine (`vt-*`)
Direção aprovada pelo dono em 01/10/2026 sobre uma mescla de protótipos: hero e orbe da v0, fósforo de osciloscópio da v1, máscara da v6 virando a constelação da v4.
- **Cena** (`components/lp/CenaVitrine.tsx` + `lib/vitrine/motor.ts`): UM canvas fixo, UM contexto WebGL escrito à mão, quatro programas — fósforo (retícula, traço âmbar do dito e azul do medido, scanline, vinheta) com o orbe por cima, pontos da constelação, fios até o fusor, aglomerado do sem sinal. Sem three.js e sem GSAP: a seção fixada é `position: sticky` com progresso medido pelo motor (o pin do GSAP injeta wrapper no DOM e briga com o React). Lenis faz a rolagem suave.
- **Orbe**: um objeto só que atravessa a página por quadros de rolagem (`lib/vitrine/coreografia.ts`, parte pura e testada). **A cor é canal**: o peso de cada mancha muda por seção — âmbar (dito) domina na entrada da conversa e no fecho, azul (medido) domina no fusor, magenta só oscila. No sem sinal, saturação 0 e giro parado.
- **Constelação** (`components/lp/Constelacao.tsx`): as falas sintéticas viram pontos, os pontos montam a máscara (metade âmbar, metade azul), a máscara se desfaz em **um nó por feature agrupado na contagem real** (`FAMILIAS_DO_VETOR`, guardada contra `NOMES_FEATURES` por `tests/test_derivacoes_dashboard.py`) e os nós caem no orbe-fusor; aí aparece a nota 2,9 e "quem puxou a nota". Quatro passos de texto trocam em fade; sem JS ou com movimento reduzido aparecem empilhados.
- **Cartões minimalistas** (pedido do dono): nada de caixa com fundo, chip ou painel com cabeçalho na vitrine. Fala é citação tipográfica com rótulo mono; o Sistema é lista de linhas com hairline.
- **LED fino**: `SegmentoLED traco="fino"` — mesma célula e alfabeto, segmento de 4 em vez de 12, sem brilho, apagado a 8%. Só na vitrine; a ferramenta segue no traço cheio.
- **CTA primário** (`.vt-botao--feixe`): miolo `--background`, borda cônica dourado → magenta. Secundário `--contorno`: hairline, hover dourado.

### Ícone de ação
`components/IconeDeAcao.tsx`. **Um verbo, um desenho:** todo botão de ação leva o ícone do VERBO (salvar, cancelar, remover, copiar, criar, atualizar, executar…), tirado de um mapa único, à esquerda do texto; só "próxima" o leva à direita. "Salvar faixas" e "Salvar equipe" têm o mesmo desenho. Controle de **seleção** (perfil, ordem de data, linha clicável de lista) não leva ícone de verbo: ele escolhe, não faz, e o estado já é dito por `aria-pressed`. O ícone é sempre decorativo (`aria-hidden`); o nome do botão é o texto.
**Traço:** os ícones vêm do lucide e são redesenhados por CSS (`.lucide` em `globals.css`): 1,5px, ponta reta, junta viva. Ponta redonda a 2px é desenho de app amigável sobre uma superfície de hairline e raio zero. A regra cobre todo ícone da ferramenta; a vitrine não usa lucide.

### Estados (coreografia)
Todo componente interativo tem padrão, hover, foco, ativo, desabilitado, carregando, erro e vazio.
- **Carregando** = esqueleto com a **forma** do resultado (`app/dashboard/loading.tsx`: armadura de quatro células, gráfico, lista), `aria-busy`. **Nunca desenha LED apagado**: apagado quer dizer "o medidor leu e não há sinal", e aqui ele ainda não leu. Nunca roda girando.
- **Vazio** (`EstadoVazio`) nomeia o que falta e o endpoint ou a etapa que resolveria (`Resolvido por ...`, `Falta rodar: ...`). Moldura tracejada. Nunca preenche com número simulado. Com API fora, fala menos: a ação está na faixa do topo e a prosa recolhe para aparato.
- **Erro isolado**: o sistema que falha mostra o próprio erro no lugar dele, com o peso dele; os vizinhos continuam de pé.
- **Sem sinal**: LED apagado ou cabeça vazada. Nunca zero, nunca cinza dentro da escala.
- **Foco**: anel de 2px `--ring` (dourado) em `:focus-visible`, também para `summary` e links.

### Easter egg da mentira (`lib/mentira.tsx`)
Com o painel do easter egg aberto, os indicadores da visão geral exibem números **falsos**: violação deliberada e **encenada** da invariante 2, sustentada por quatro travas: (1) nada sai da memória (zero escrita, zero API; estado de render); (2) leitor de tela recebe a verdade (o falso é `aria-hidden` e um `sr-only` diz que foi falsificado e qual o real); (3) selo `--destructive` inescapável no mesmo quadro; (4) volta sozinha em 8s, `Esc` ou clique fora. Gráficos e tabela **não** mentem. O falso é determinístico (`(d*7+3)%10` só nos algarismos, sem `Math.random`) e o LED vai a `cor="erro"`. Qualquer variação que quebre uma trava não é o easter egg, é defeito.

### Motion
Vocabulário em `lib/movimento.ts` (150–250 ms, curva `--ease-fluid` `cubic-bezier(0.32, 0.72, 0, 1)`). Na **ferramenta**, dois momentos autorados: o cursor de leitura na linha do tempo e a entrada dos sistemas (8px, uma vez, escalonada em 40 ms na armadura). Resposta a gesto (hover, a marca `MarcaFraus` que responde a cinco cliques) é outra categoria e não conta.

**A exceção da vitrine (cena WebGL).** Desde 01/10/2026 a vitrine tem um canvas WebGL com laço de quadros — decisão do dono, que inverte a de 30/09 (orbe em CSS puro, sem canvas). A regra que sobrevive é onde ele mora: **só em `app/page.tsx`**, nunca no layout raiz, porque a ferramenta é lida por horas e não pode ter GPU girando atrás de tabela e gráfico. Contexto WebGL é liberado ao desmontar (`WEBGL_lose_context`). Sem WebGL, o canvas some e a página segue legível. `scripts/validar-lp-playwright.mjs` cobra exatamente um canvas e o regime certo.
**`prefers-reduced-motion` congela, não desacelera:** na vitrine o motor entra no regime `vt-estatico` — nenhum laço, um quadro redesenhado só quando a página rola, orbe parado, constelação no estágio dos nós, seção não fixa. As animações CSS da vitrine (entrada da manchete, borda do CTA, seta) também param. Na ferramenta, o bloco global zera transições e o `<Movimento>` passa `reducedMotion="user"` ao Motion.

## Do's and Don'ts

### Do:
- **Do** passar ao `SegmentoLED` a string já formatada em pt-BR e sempre um `rotulo`; `valor={null}` para ausência.
- **Do** manter âmbar acima e azul abaixo; use `-texto` quando a cor carrega tipo.
- **Do** manter o dourado em ação, foco, cursor e marca, e o magenta no orbe e no halo.
- **Do** rodar `npm run contraste` e `npm run pisos` ao tocar token de cor, vidro ou ateliê, e `npm run build` (ele compila o CSS e processa assets; os outros gates não).
- **Do** conferir trabalho visual olhando, a 1280×720 e a 390px, nos dois temas.
- **Do** rotular amostras sintéticas como tal em todo lugar em que aparecem.
- **Do** nomear o que falta em estado vazio, com a etapa ou o endpoint.
- **Do** derivar score, nota e categoria no servidor; o LED apresenta, não calcula.

### Don't:
- **Don't** renderizar `0` para ausência; `null` é segmento apagado e "sem sinal" por extenso.
- **Don't** usar kickers/eyebrows acima de título na vitrine (removidos na revisão final).
- **Don't** usar dourado em série, barra, categoria ou célula de dado, nem como luz de ambiente.
- **Don't** usar Bricolage fora de `.display-vitrine`/`.titulo-vitrine`, nem display em rótulo ou dado.
- **Don't** pôr orbe, halo, grade ou coreografia atrás de tabela, gráfico ou qualquer rota do Operate.
- **Don't** escrever texto abaixo de 11px.
- **Don't** empilhar bordas, reintroduzir chanfro, raio ou quina iluminada no tema Instrumento.
- **Don't** reciclar matiz de família nem reordenar/retocar as sete emoções sem rodar o validador.
- **Don't** pontuar atendentes: nenhum elemento de interface pode transformar reconhecimento de emoção em score de performance por pessoa (CLAUDE.md, EU AI Act).
- **Don't** pôr comentário ou regra que cite `.tema-chuva` antes do bloco real dele: o gate recorta pela primeira ocorrência da string e mede o bloco errado (ver Temas e gates).

## Temas e gates

**Dois temas, ambos escuros.** O padrão é o Instrumento (`:root, .dark`, o app renderiza sempre com `.dark`); a segunda opção é **chuva de neon** (`.tema-chuva`), que sobrepõe só o chassi: asfalto índigo, dourado de sódio (`0.81 0.1 82`), quina de neon ciano/magenta, atelier aceso e vidro mais grosso. Ela **não toca a camada de dado**: `--dito` continua âmbar, `--medido` azul, famílias intactas; o dourado segue fora de dado; todo par de texto cruza AA nos dois temas.

**Gate ciente de tema.** `scripts/contraste.mjs` recorta o bloco base (`:root, .dark {`) e cada bloco cujo seletor começa com `.tema-`, sobrepõe à base como a cascata (um tema só declara o que muda) e roda a matriz inteira por tema. Um mapa único deixaria o segundo tema sobrescrever o primeiro e o relatório sairia verde medindo um tema só. `scripts/pisos.mjs` mede o pior caso de vidro sobre o ateliê (só lê `oklch()` literal, por isso os pisos são pré-calculados, não `color-mix`).
**O cuidado com `.tema-chuva`.** O laço que descobre temas usa `^(\.tema-…)\s*\{` (ancorado no início de linha), mas `recortarBloco` localiza o bloco por `indexOf` do seletor **em qualquer ponto do arquivo**, e depois abre na primeira `{` seguinte. Logo, qualquer comentário ou regra anterior ao bloco real que escreva a string `.tema-chuva` (por exemplo `.tema-chuva .vidro-fino`) faz o gate recortar o trecho errado e medir o bloco errado, com relatório verde. Em `globals.css` o bloco real vem antes de toda outra menção e o comentário que o antecede fala do tema sem escrever o seletor. Mantenha assim.

**Ciclo de verificação:** `pisos`, `contraste`, `tsc --noEmit`, `lint` e `build` não se substituem, e nenhum vê a tela. Quatro já devolveram verde com o build quebrado.

## Adições e desvios conscientes desta rodada

- **Revisão final (30/09/2026):** kickers removidos da LP; dourado só em ação e marca (mancha dourada do ateliê zerada, LED da faixa de fatos em `tinta`); hero a 1280×720 com CTA na dobra (orbe por altura); mobile 390 sem corte nem rolagem horizontal; armadura da visão geral em faixa curta com leitura do NPS em faixa própria; grafo com respiro e reenquadramento ao redimensionar.
- **`.lp-*` no `globals.css`** é resíduo da vitrine anterior; a LP nova vive em `vitrine.css` com prefixo `vt-` justamente para não herdar hover de peça extinta.
- **Nove tipos de nó do grafo não foram alterados nesta rodada, mesmo com o revisor pedindo.** Os matizes estão congelados: a família (quente/fria) já diz dito/medido de longe, o matiz diz o tipo de perto, a legenda agrupa os nove, e claridade/croma iguais impedem hierarquia acidental. Mexer nas cores em rodada de chassi, sem validar de novo legenda, contraste e leitura no canvas, trocaria uma decisão medida por gosto. Reabra só como decisão própria, com validação.
- **Vidro que não é mais vidro:** `--vidro-*-fundo`, `--vidro-quina`, `.chanfro`, `.especular` ficam como vocabulário porque o tema chuva os usa. Em `lib/hierarquia.ts`, a diferença entre `vidro` e `vidro-fino` é hoje só o padding e o tipo; não leia como duas opacidades.
- **Não canonizado (defeitos carregados, não regras):** comentários do `globals.css` ainda citam croma "0.085"/"0.15" para dourado/âmbar (o token vigente é 0.095/0.14) e "DESIGN.md secão 4" numerada como no arquivo antigo. Os ícones `lucide-react` deixaram de ser defeito carregado em 02/10/2026: ganharam traço próprio e regra de uso (ver "Ícone de ação"); o glifo `█` do cursor continua sendo texto, e continua sendo a peça.
