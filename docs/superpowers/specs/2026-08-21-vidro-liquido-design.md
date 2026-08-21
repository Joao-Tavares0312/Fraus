# Vidro líquido — reskin de materialidade da dashboard

**Data:** 2026-08-21
**Estado:** spec aprovada, plano de implementação pendente
**Telas afetadas:** as sete (chassi), com composição sob medida em duas

---

## 1. O que se decidiu, e o que se decidiu contra

O pedido foi aplicar *liquid glass* na interface do Fraus. Três alcances foram
postos na mesa e o escolhido foi o **reskin completo**: o vidro vira a
linguagem de superfície da dashboard inteira, não um enfeite em camada de
overlay.

Isso foi escolhido **sabendo** que ele contraria pontos do `DESIGN.md` vigente,
que foram apontados antes da decisão:

- §2.1 elimina o cartão com fundo e borda próprios como agrupador de página;
  o vidro o reintroduz.
- §3.1 define o fundo como "papel de ensaio grafite", e papel não refrata.
- §6 restringe movimento a "um momento autorado"; o realce especular que segue
  o ponteiro é um segundo.

A decisão foi tomada com esses custos declarados. Esta spec registra a emenda em
vez de fingir que o contrato antigo continua inteiro — o `DESIGN.md` será
alterado no ponto exato, com o motivo.

### 1.1 O que NÃO foi trocado

A metáfora **Pauta** sobrevive. O vidro é chassi — superfície, fundo, borda,
profundidade. A tese de composição continua sendo a partitura:

- a linha do sistema que separa o **dito** (acima) do **medido** (abaixo);
- o encoding `--dito` âmbar / `--medido` azul, marcado como vinculante no
  `PRODUCT.md`;
- a cabeça vazada do `sem_sinal`;
- a armadura à esquerda, o aparato no rodapé.

Tudo isso passa a ser desenhado **sobre** vidro, opaco e sem blur. Nenhum
elemento que carrega dado vira translúcido.

---

## 2. Arquitetura: quatro camadas

O material é uma pilha de quatro camadas com responsabilidades disjuntas. Cada
uma pode ser entendida e alterada sem ler as outras.

```
 camada 3  DADO         régua, séries, cabeça vazada, números   ← opaco, sem blur
 camada 2  ESPECULAR    realce que segue o ponteiro             ← ::after, CSS vars
 camada 1  VIDRO        superfície translúcida + quina de luz   ← backdrop-filter
 camada 0  ATELIÊ       manchas de luz fixas sobre o grafite    ← fixed, aria-hidden
```

### 2.1 Camada 0 — o ateliê

Elemento fixo de tela cheia, `pointer-events-none`, `aria-hidden`, atrás de todo
o conteúdo. Três gradientes radiais suaves sobre `--background`:

| Mancha | Matiz | Papel |
|---|---|---|
| dourada | matiz do `--primary` (80) | a marca, no canto superior |
| fria | matiz do `--medido` (265) | contrapeso, no canto inferior oposto |
| quente fraca | matiz do `--dito` (60) | quebra a simetria das duas |

Croma baixo em todas: elas iluminam, não pintam. **Sem esta camada o reskin não
existe** — vidro sobre fundo chapado é indistinguível de um cinza mais claro,
porque não há o que refratar.

É **estático**. Não anima, não reage a dado, não muda com o período filtrado.
A alternativa "a luz vem do dado" foi explicitamente rejeitada: criaria um canal
de cor sem rótulo, contra o princípio de que categoria nunca é comunicada só por
cor e contra a regra de que a cor da marca nunca codifica valor.

**Arquivo:** `dashboard/components/shell/Atelier.tsx`, montado uma vez em
`app/layout.tsx`, antes do `SidebarProvider`.

### 2.2 Camada 1 — o vidro

Um conjunto de tokens `--vidro-*` em `globals.css` e três utilitários. Cada
espessura é uma composição de quatro coisas:

1. fundo semitranslúcido (`color-mix` do `--card` com transparente);
2. `backdrop-filter: blur() saturate()` — a saturação é o que impede o vidro de
   deixar tudo atrás cinzento;
3. **quina iluminada**: `box-shadow` `inset` claro na aresta superior e escuro na
   inferior. É isto que faz parecer vidro em vez de plástico fosco;
4. sombra externa para separar da camada de baixo.

| Utilitário | Blur | Onde |
|---|---|---|
| `.vidro-fino` | baixo | header fixo, tooltip, badge — só sinaliza flutuação |
| `.vidro` | médio | sidebar, `Painel`, superfícies de controle |
| `.vidro-denso` | alto | sheet, dialog, popover, select |

`.vidro-denso` existe por necessidade de leitura, não de estética: num menu
suspenso o conteúdo atrás **precisa** desaparecer, ou o rótulo da opção compete
com a tabela por trás dele.

Toda espessura declara `@supports not (backdrop-filter: blur(1px))` com fundo
opaco equivalente. Navegador sem suporte recebe superfície sólida legível, nunca
um retângulo semitransparente ilegível.

### 2.3 Camada 2 — o especular

Realce radial em `::after` de cada superfície de vidro, posicionado por duas
custom properties `--px` / `--py`.

**Implementação:** hook `useEspecular()` que devolve uma ref. Ele escuta
`pointermove` e escreve as vars **direto no `style` do nó dentro de
`requestAnimationFrame`**. Nenhum estado de React é tocado — um `useState` por
movimento de mouse repintaria a árvore inteira da dashboard continuamente.

**Desligamento, os dois casos:**

- `prefers-reduced-motion: reduce` → o `::after` some, o vidro continua;
- ponteiro grosso (`pointer: coarse`) → também some. Touch não tem hover: o
  realce ficaria congelado no último ponto tocado, que é pior que não existir.

**Arquivo:** `dashboard/hooks/useEspecular.ts`.

### 2.4 Camada 3 — o dado

Regra dura: **nada que carrega dado é translúcido.**

Gráficos, tabelas, transcrição, régua do sistema e séries desenham em superfície
opaca embutida no vidro — um visor. Blur atrás de uma série de meio ponto come a
linha, e a régua da pauta é justamente meio ponto.

---

## 3. Contraste: o gate que segura o reskin

Este é o ponto onde um reskin de vidro tipicamente destrói a legibilidade sem
emitir nenhum aviso, e o Fraus tem um gate verificado por cálculo que precisa
continuar valendo.

**O problema:** `dashboard/scripts/contraste.mjs` compara cada token de texto
contra `--background`, `--card` e `--muted` — cores fixas. Uma superfície
translúcida **não tem cor fixa**: ela depende do que está atrás. O script, como
está, não teria o que medir.

**A solução:** cada espessura declara um token `--vidro-<n>-piso` — a cor **mais
clara que aquela superfície pode assumir**, calculada como o fundo do vidro
composto sobre a mancha mais brilhante do ateliê. É o pior caso para texto claro
sobre ela.

O script passa a incluir os três pisos na lista de fundos verificados. Todo par
que carrega texto continua cruzando **AA (4.5:1)**.

**Regra de resolução de conflito:** par que reprova → a espessura de vidro ganha
opacidade até passar. O gate manda no vidro; o vidro não afrouxa o gate. Se uma
espessura precisar de tanta opacidade que deixe de parecer vidro, ela vira
superfície sólida e isso é registrado — não se entrega um número ilegível para
manter um efeito.

---

## 4. Escopo

### 4.1 Chassi (as sete telas herdam)

| Arquivo | Mudança |
|---|---|
| `app/globals.css` | tokens `--vidro-*`, pisos, utilitários `.vidro*` e `.especular` |
| `components/shell/Atelier.tsx` | **novo** — camada 0 |
| `app/layout.tsx` | monta o ateliê |
| `hooks/useEspecular.ts` | **novo** — camada 2 |
| `components/ui/sidebar.tsx` | superfície de vidro |
| `components/ui/sheet.tsx` | `.vidro-denso`; já tem `backdrop-blur` no overlay |
| `components/ui/select.tsx`, `tooltip.tsx` | `.vidro-denso` / `.vidro-fino` |
| `components/ui/card.tsx`, `button.tsx`, `input.tsx`, `textarea.tsx`, `tabs.tsx`, `badge.tsx`, `pagination.tsx`, `alert.tsx`, `table.tsx` | superfície e borda |
| `components/shell/CabecalhoPagina.tsx` | `.vidro-fino` no lugar do `bg-background/95 backdrop-blur` atual |
| `components/Painel.tsx` | superfície de vidro no sistema |

### 4.2 Sob medida

- **Visão geral** — armadura de indicadores sobre vidro; `GraficoNpsLatencia` em
  visor sólido embutido.
- **Atendimentos** — `TabelaConversas` (cabeçalho fixo em `.vidro-fino`, corpo
  em visor) e `Transcricao`.

### 4.3 Herdam do chassi, sem composição nova

Modelo, Configurações, Integrações, Analisar, Grafo.

O canvas do grafo é desenho próprio e **não** herda material do chassi; ele fica
como está nesta entrega, dentro de um sistema de vidro. Se destoar, vira trabalho
separado.

### 4.4 Documentação

- `dashboard/DESIGN.md`: seção nova **"A materialidade"** descrevendo as quatro
  camadas, e emenda ao §2.1 registrando a volta do painel com fundo próprio, com
  o motivo e a data.
- `dashboard/PRODUCT.md`: sem mudança. Nenhum compromisso de produto é afetado.

---

## 5. Invariantes preservadas

Nada abaixo é estilo, e nada abaixo muda:

1. encoding âmbar = dito / azul = medido;
2. cabeça vazada para `sem_sinal`; ausência de dado nunca vira zero;
3. categoria nunca comunicada só por cor — sempre com rótulo textual;
4. score, nota e categoria derivados no servidor;
5. tema escuro único, sem alternador;
6. `prefers-reduced-motion` respeitado;
7. todo par de cor que carrega texto cruza AA por cálculo;
8. interface inteiramente em português do Brasil.

---

## 6. Verificação

| Comando | Critério |
|---|---|
| `npm run contraste` | verde, já incluindo os três pisos de vidro |
| `npx tsc --noEmit` | sem erro |
| `npm run build` | sem erro |
| `uv run pytest -q` | verde (nada de back-end muda; é regressão) |
| screenshots | as sete telas, antes e depois, para julgamento visual |

Verificação manual obrigatória, porque script nenhum pega:

- `prefers-reduced-motion` ligado → especular ausente, vidro intacto;
- largura de telefone → especular ausente, layout de pé;
- rolagem longa em Atendimentos → sem engasgo perceptível com o `backdrop-filter`.

---

## 7. Riscos declarados

**Custo de composição.** `backdrop-filter` em muitas superfícies simultâneas é o
efeito mais caro de CSS. Mitigação: três espessuras e não uma escala contínua,
visor sólido no que rola muito, e a checagem de rolagem acima. Se a rolagem
engasgar, a espessura da superfície que rola cai antes de qualquer outra coisa.

**Perda de contraste.** Endereçada pela seção 3, que é o motivo de ela existir.

**Distância do contrato antigo.** Registrada na seção 1 e emendada no
`DESIGN.md`. A banca julga rigor metodológico: uma decisão de estilo documentada
com o custo declarado é defensável; uma contradição silenciosa entre o doc e a
tela não é.
