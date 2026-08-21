# Vidro líquido — plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: use `superpowers:subagent-driven-development`
> (recomendado) ou `superpowers:executing-plans` para executar tarefa a tarefa.
> Os passos usam caixa (`- [ ]`) para acompanhamento.

**Goal:** trocar a materialidade da dashboard do Fraus para vidro líquido —
fundo com luz, superfícies translúcidas, realce especular que segue o ponteiro —
sem perder a metáfora Pauta, o gate de contraste AA nem uma invariante de produto.

**Architecture:** quatro camadas empilhadas e disjuntas — ateliê (luz de fundo,
estática) → vidro (superfície translúcida com quina iluminada) → especular
(realce por ponteiro, via CSS vars escritas fora do React) → dado (opaco, sem
blur, intocado). O vidro entra pelos tokens e pelos componentes compartilhados,
então as sete telas mudam juntas; duas recebem composição sob medida.

**Tech Stack:** Next.js 16 (App Router), React 19, Tailwind v4, shadcn/ui sobre
Base UI, tokens OKLCH em `app/globals.css`, verificador de contraste próprio em
`scripts/contraste.mjs`.

**Spec:** `docs/superpowers/specs/2026-08-21-vidro-liquido-design.md`

## Global Constraints

- Trabalhe sempre dentro de `dashboard/`. Não existe `package.json` na raiz.
- **Não adicione nenhuma dependência.** O `CLAUDE.md` proíbe dependência nova sem
  motivo declarado, e este plano não precisa de nenhuma.
- **Não existe runner de teste JS neste projeto** e não se deve instalar um. O
  ciclo de verificação de cada tarefa é `npm run contraste`, `npx tsc --noEmit`,
  `npm run lint` e `npm run build`. Onde nenhum deles pega o defeito — efeito
  visual — a tarefa termina em screenshot conferido a olho.
- **Nada de hex solto em componente.** Cor entra por token em `app/globals.css`.
- Identificadores e docstrings em **português sem acento nos símbolos**
  (`useEspecular`, `Atelier`, `--vidro-fino`). Texto de interface leva acento.
- Commits em português, sem acento, no formato `tipo(escopo): resumo`.
- **Invariantes que nenhuma tarefa pode quebrar:** encoding `--dito` âmbar acima
  / `--medido` azul abaixo; cabeça vazada para `sem_sinal` e ausência de dado
  nunca vira zero; categoria nunca comunicada só por cor; score derivado no
  servidor; tema escuro único; `prefers-reduced-motion` respeitado; todo par de
  cor que carrega texto cruza 4.5:1.
- **Nada que carrega dado é translúcido.** Gráfico, tabela, transcrição e régua
  desenham em superfície opaca. Blur atrás de uma série de meio ponto come a
  série, e a régua da pauta é meio ponto.
- Trabalhe na branch `feat/vidro-liquido`, já criada, com a spec commitada.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade | Estado |
|---|---|---|
| `app/globals.css` | tokens `--vidro-*`, pisos, utilitários `.vidro*` e `.especular` | modificar |
| `scripts/contraste.mjs` | passa a verificar texto contra os pisos de vidro | modificar |
| `components/shell/Atelier.tsx` | camada 0 — a luz de fundo | **criar** |
| `app/layout.tsx` | monta o ateliê | modificar |
| `hooks/useEspecular.ts` | camada 2 — ponteiro → CSS vars | **criar** |
| `components/ui/{sheet,select,tooltip,sidebar}.tsx` | superfícies flutuantes | modificar |
| `components/ui/{card,button,input,textarea,tabs,badge,pagination,alert,table}.tsx` | controles e superfícies | modificar |
| `components/shell/CabecalhoPagina.tsx` | header fixo em vidro fino | modificar |
| `components/Painel.tsx` | o sistema ganha superfície | modificar |
| `app/page.tsx` + `components/{FaixaIndicadores,GraficoNpsLatencia}.tsx` | Visão geral sob medida | modificar |
| `components/{TabelaConversas,Transcricao}.tsx` | Atendimentos sob medida | modificar |
| `dashboard/DESIGN.md` | seção "A materialidade" + emenda ao §2.1 | modificar |

---

## Task 1: Tokens de vidro e o gate de contraste

O gate vem **primeiro**, antes de qualquer superfície existir. É a tarefa que
impede o reskin de comer a legibilidade, e ela é executável como teste de
verdade: `scripts/contraste.mjs` sai com código 1 quando um token some ou um par
reprova.

**Files:**
- Modify: `dashboard/scripts/contraste.mjs` (a constante `fundos`, hoje na linha 65)
- Modify: `dashboard/app/globals.css` (bloco `:root`, junto aos tokens de superfície)

**Interfaces:**
- Consumes: nada.
- Produces: os tokens `--vidro-fino-piso`, `--vidro-piso`, `--vidro-denso-piso`,
  `--vidro-fino-fundo`, `--vidro-fundo`, `--vidro-denso-fundo`, `--vidro-blur-fino`,
  `--vidro-blur`, `--vidro-blur-denso`, `--vidro-quina`, `--vidro-quina-baixa`,
  `--vidro-sombra`. A Task 3 consome todos.

**Contexto que o executor precisa saber:** o regex do `contraste.mjs` (linha ~58)
só captura tokens escritos literalmente como `oklch(L C H)`. Por isso os pisos
são valores **opacos e pré-calculados**, não `color-mix`. Um piso escrito com
`color-mix` seria ignorado em silêncio pelo parser, que é exatamente o modo de
falha que esta tarefa existe para evitar.

- [ ] **Step 1: Fazer o gate falhar**

Em `dashboard/scripts/contraste.mjs`, troque a linha 65:

```js
const fundos = ["--background", "--card", "--muted"];
```

por:

```js
// Os PISOS DE VIDRO entram aqui porque superficie translucida nao tem cor
// fixa: ela depende do que esta atras. Cada piso e a cor MAIS CLARA que
// aquela espessura pode assumir -- o fundo do vidro composto sobre a mancha
// mais brilhante do atelie --, ou seja, o pior caso para texto claro.
//
// Eles sao opacos e pre-calculados de proposito: o regex acima so captura
// `oklch(L C H)` literal, e um piso escrito com color-mix seria ignorado em
// silencio -- o modo de falha que esta lista existe para evitar.
const fundos = [
  "--background",
  "--card",
  "--muted",
  "--vidro-fino-piso",
  "--vidro-piso",
  "--vidro-denso-piso",
];
```

- [ ] **Step 2: Rodar e confirmar a falha**

```bash
cd dashboard && npm run contraste
```

Esperado: **FALHA**. Os três pisos ainda não existem no CSS, então
`tokens.get(nomeFundo)` devolve `undefined` e o laço os pula com
`if (!fundo) continue;` — o relatório sai **sem nenhuma linha `--vidro-*`**.
Confirme isso olhando a tabela: se não há linha citando um piso, o gate ainda
não está medindo o vidro. (Este é o ponto do passo: provar que a lista de fundos
sozinha não verifica nada.)

- [ ] **Step 3: Declarar os tokens de vidro**

Em `dashboard/app/globals.css`, dentro de `:root`, logo **depois** do bloco
`--sidebar-*` e **antes** do comentário `/* --- a pauta --- */`, insira:

```css
  /* --- A MATERIALIDADE: vidro liquido ---------------------------------
     Ver DESIGN.md, "A materialidade", e a spec de 2026-08-21.

     Tres espessuras, e nao uma escala continua, porque o custo de
     `backdrop-filter` e real e cada espessura resolve um problema diferente:
       fino  -> so sinaliza flutuacao (header, tooltip)
       medio -> superficie de trabalho (sidebar, painel, controle)
       denso -> o conteudo atras PRECISA sumir (sheet, popover, select), ou o
                rotulo da opcao compete com a tabela por tras dele.

     Cada espessura tem um PISO: a cor mais clara que ela pode assumir, com o
     vidro composto sobre a mancha mais brilhante do atelie. E contra o piso
     que `scripts/contraste.mjs` verifica o texto -- superficie translucida
     nao tem cor fixa, e o pior caso e o unico caso honesto de medir.

     Os pisos sao mais ESCUROS que --muted (L 0.274), que ja esta no conjunto
     verificado ha tempo. Se algum dia um piso passar de 0.274, isso nao e um
     detalhe: e o sinal de que o vidro clareou a ponto de ameacar o texto, e a
     espessura correspondente precisa de mais opacidade. */
  --vidro-fino-fundo: color-mix(in oklch, var(--card) 45%, transparent);
  --vidro-fundo: color-mix(in oklch, var(--card) 62%, transparent);
  --vidro-denso-fundo: color-mix(in oklch, var(--card) 82%, transparent);

  --vidro-fino-piso: oklch(0.25 0.006 78);
  --vidro-piso: oklch(0.24 0.006 78);
  --vidro-denso-piso: oklch(0.23 0.006 78);

  --vidro-blur-fino: 8px;
  --vidro-blur: 16px;
  --vidro-blur-denso: 28px;

  /* A QUINA ILUMINADA. E este par -- claro na aresta de cima, escuro na de
     baixo -- que faz a superficie parecer vidro em vez de plastico fosco.
     Sem ele, translucidez sozinha le como opacidade mal resolvida. */
  --vidro-quina: oklch(1 0 0 / 12%);
  --vidro-quina-baixa: oklch(0 0 0 / 20%);
  --vidro-sombra: 0 1px 2px oklch(0 0 0 / 20%), 0 8px 24px oklch(0 0 0 / 28%);
```

- [ ] **Step 4: Rodar o gate e confirmar que ele agora mede o vidro**

```bash
cd dashboard && npm run contraste
```

Esperado: **PASS**, e agora a tabela traz uma linha por par
`<token de texto> × <piso de vidro>` — 14 tokens de texto × 3 pisos = 42 linhas
novas. Confira que elas existem; a mensagem final deve ser
`Todos os pares de texto cruzam AA (4.5:1).`

Se algum par reprovar, **não afrouxe o gate**: baixe a claridade do piso que
reprovou e aumente a porcentagem de `--card` na `*-fundo` correspondente (menos
transparência = vidro mais escuro), e rode de novo.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git add dashboard/app/globals.css dashboard/scripts/contraste.mjs
git commit -m "feat(vidro): tokens de vidro e o gate medindo o pior caso

Superficie translucida nao tem cor fixa, entao o contraste.mjs -- que so
sabia comparar contra cor fixa -- nao teria o que medir. Cada espessura
declara um piso opaco, a cor mais clara que ela pode assumir, e e contra
ele que o texto e verificado."
```

---

## Task 2: O ateliê — a luz que o vidro refrata

**Files:**
- Create: `dashboard/components/shell/Atelier.tsx`
- Modify: `dashboard/app/layout.tsx`

**Interfaces:**
- Consumes: `--background`, `--primary`, `--medido`, `--dito` (já existem).
- Produces: `<Atelier />`, componente sem props, exportado nomeado.

- [ ] **Step 1: Criar o componente**

Crie `dashboard/components/shell/Atelier.tsx`:

```tsx
/**
 * O ATELIE: a luz que o vidro refrata.
 *
 * Sem esta camada o reskin de vidro nao existe. Vidro sobre fundo chapado e
 * indistinguivel de um cinza um pouco mais claro, porque nao ha nada atras
 * para refratar -- `backdrop-filter` borra o que esta atras, e atras de um
 * grafite uniforme so ha mais grafite.
 *
 * Tres manchas radiais de croma BAIXO sobre o `--background`: elas iluminam,
 * nao pintam. A dourada e a marca; a fria contrapesa do lado do `--medido`; a
 * quente fraca quebra a simetria das duas, que sozinhas leriam como gradiente
 * de template.
 *
 * E ESTATICO, e isso e uma decisao, nao uma pendencia. A alternativa avaliada
 * -- a luz mudar de cor conforme o resultado do periodo -- foi rejeitada: ela
 * criaria um canal de cor sem rotulo, contra o principio de que categoria
 * nunca e comunicada so por cor, e contra a regra de que a cor da marca nunca
 * codifica valor. Ver DESIGN.md, seccao 3.3.
 *
 * `aria-hidden` e `pointer-events-none` porque isto nao e conteudo nem alvo:
 * e o papel de parede da sala.
 */
export function Atelier() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-background"
    >
      {/* dourada -- a marca, alto a esquerda */}
      <div
        className="absolute -left-[15%] -top-[25%] h-[70vmax] w-[70vmax] rounded-full opacity-[0.13] blur-[80px]"
        style={{
          background:
            "radial-gradient(closest-side, var(--primary), transparent)",
        }}
      />
      {/* fria -- contrapeso do lado do medido, baixo a direita */}
      <div
        className="absolute -bottom-[30%] -right-[20%] h-[75vmax] w-[75vmax] rounded-full opacity-[0.11] blur-[90px]"
        style={{
          background:
            "radial-gradient(closest-side, var(--medido), transparent)",
        }}
      />
      {/* quente fraca -- quebra a simetria das outras duas */}
      <div
        className="absolute left-[45%] top-[55%] h-[45vmax] w-[45vmax] rounded-full opacity-[0.07] blur-[100px]"
        style={{
          background: "radial-gradient(closest-side, var(--dito), transparent)",
        }}
      />
    </div>
  );
}
```

- [ ] **Step 2: Montar no layout**

Em `dashboard/app/layout.tsx`, adicione o import junto aos outros de
`@/components/shell`:

```tsx
import { Atelier } from "@/components/shell/Atelier";
```

e insira `<Atelier />` como **primeiro filho** do `<body>`, antes do link
"Pular para o conteúdo":

```tsx
      <body className="min-h-svh antialiased">
        <Atelier />
```

- [ ] **Step 3: Verificar**

```bash
cd dashboard && npx tsc --noEmit && npm run lint
```

Esperado: sem erro.

- [ ] **Step 4: Conferir a olho**

Suba `npm run dev`, abra `/`, e confirme: o fundo deixou de ser grafite chapado
e ganhou variação suave de luz, **sem** nenhuma faixa ou banding visível, e
**sem** que qualquer texto tenha ficado mais difícil de ler. Role a página: as
manchas ficam paradas (são `fixed`), o conteúdo passa por cima.

Se aparecer banding, aumente o `blur-[]` da mancha culpada.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git add dashboard/components/shell/Atelier.tsx dashboard/app/layout.tsx
git commit -m "feat(vidro): o atelie, a luz que o vidro refrata

Estatico de proposito: luz derivada do dado criaria um canal de cor sem
rotulo, contra a regra de que categoria nunca e comunicada so por cor."
```

---

## Task 3: Os utilitários de vidro

**Files:**
- Modify: `dashboard/app/globals.css` (bloco `@layer utilities`, hoje no fim do arquivo)

**Interfaces:**
- Consumes: os tokens da Task 1.
- Produces: as classes `.vidro`, `.vidro-fino`, `.vidro-denso`. As Tasks 5–9 as consomem.

- [ ] **Step 1: Escrever os utilitários**

Em `dashboard/app/globals.css`, dentro do `@layer utilities` existente, **depois**
da regra `.estimado`, insira:

```css
  /* --- AS TRES ESPESSURAS DE VIDRO ------------------------------------
     A composicao e sempre a mesma e tem quatro partes:
       1. fundo semitranslucido    -> deixa a luz do atelie passar
       2. blur + saturate          -> a saturacao impede que tudo atras vire
                                      cinzento; blur sozinho dessatura
       3. a quina iluminada        -> inset claro em cima, escuro embaixo. E
                                      isto que le como vidro, e nao como
                                      plastico fosco
       4. sombra externa           -> separa da camada de baixo

     O fallback nao e detalhe: navegador sem `backdrop-filter` que recebesse
     so o fundo translucido mostraria texto sobre um retangulo semitransparente
     -- ilegivel. Ele recebe superficie SOLIDA, e a superficie solida e o
     proprio piso que o gate de contraste ja verifica. */
  .vidro-fino,
  .vidro,
  .vidro-denso {
    box-shadow:
      inset 0 1px 0 0 var(--vidro-quina),
      inset 0 -1px 0 0 var(--vidro-quina-baixa),
      var(--vidro-sombra);
    border: 1px solid var(--border);
  }

  .vidro-fino {
    background-color: var(--vidro-fino-fundo);
    backdrop-filter: blur(var(--vidro-blur-fino)) saturate(1.4);
  }
  .vidro {
    background-color: var(--vidro-fundo);
    backdrop-filter: blur(var(--vidro-blur)) saturate(1.5);
  }
  .vidro-denso {
    background-color: var(--vidro-denso-fundo);
    backdrop-filter: blur(var(--vidro-blur-denso)) saturate(1.6);
  }

  @supports not (backdrop-filter: blur(1px)) {
    .vidro-fino {
      background-color: var(--vidro-fino-piso);
    }
    .vidro {
      background-color: var(--vidro-piso);
    }
    .vidro-denso {
      background-color: var(--vidro-denso-piso);
    }
  }
```

- [ ] **Step 2: Verificar que o CSS compila**

```bash
cd dashboard && npm run build
```

Esperado: build sem erro. (Tailwind v4 falha o build em CSS inválido dentro de
`@layer`, então este passo é a checagem real de sintaxe.)

- [ ] **Step 3: Confirmar que o gate continua verde**

```bash
cd dashboard && npm run contraste
```

Esperado: PASS. Nenhum token mudou, mas rodar aqui prova que a Task 3 não
mexeu no que a Task 1 garantiu.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git add dashboard/app/globals.css
git commit -m "feat(vidro): as tres espessuras e o fallback solido

Navegador sem backdrop-filter recebe o proprio piso do gate de contraste,
nao um retangulo semitransparente com texto por cima."
```

---

## Task 4: O especular que segue o ponteiro

**Files:**
- Create: `dashboard/hooks/useEspecular.ts`
- Modify: `dashboard/app/globals.css` (`@layer utilities`)

**Interfaces:**
- Consumes: nada das tarefas anteriores.
- Produces: `useEspecular<T extends HTMLElement = HTMLDivElement>(): RefObject<T | null>`
  e a classe `.especular`. Um elemento precisa das **duas** para o realce existir.
  As Tasks 5–9 consomem ambos.

**Contexto que o executor precisa saber:** o hook escreve as CSS vars direto no
`style` do nó. Não use `useState` — um estado por `pointermove` repintaria a
árvore inteira da dashboard continuamente, num app com gráficos Recharts e um
canvas de grafo montados. Este é o requisito de desempenho central da tarefa.

- [ ] **Step 1: Criar o hook**

Crie `dashboard/hooks/useEspecular.ts`:

```ts
"use client";

import { useEffect, useRef } from "react";

/**
 * O REALCE ESPECULAR: o brilho que acompanha o ponteiro sobre o vidro.
 *
 * Devolve uma ref para pendurar no elemento que tem a classe `.especular`. O
 * hook escreve `--px` e `--py` (a posicao do ponteiro dentro do elemento, em
 * porcentagem) DIRETO no `style` do no, dentro de um `requestAnimationFrame`.
 *
 * POR QUE NAO `useState`: um estado por `pointermove` repintaria a arvore
 * inteira da dashboard a cada movimento do mouse, com Recharts e o canvas do
 * grafo montados. O realce e puramente visual e nao pertence ao estado do
 * React -- escrever no no e a implementacao correta, nao um atalho.
 *
 * OS DOIS DESLIGAMENTOS, e o segundo e o que costuma ser esquecido:
 *   - `prefers-reduced-motion: reduce` -- o realce some, o vidro fica;
 *   - `pointer: coarse` -- toque nao tem hover, entao o realce congelaria no
 *     ultimo ponto tocado, o que e pior do que nao existir.
 * Ambos sao consultados aqui E no CSS: aqui para nao pendurar listener a toa,
 * no CSS para que o pseudo-elemento nao exista.
 */
export function useEspecular<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const no = ref.current;
    if (!no) return;

    const semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)");
    const ponteiroGrosso = window.matchMedia("(pointer: coarse)");
    if (semMovimento.matches || ponteiroGrosso.matches) return;

    let quadro = 0;

    function aoMover(evento: PointerEvent) {
      if (quadro) return;
      quadro = requestAnimationFrame(() => {
        quadro = 0;
        const alvo = ref.current;
        if (!alvo) return;
        const caixa = alvo.getBoundingClientRect();
        if (caixa.width === 0 || caixa.height === 0) return;
        const x = ((evento.clientX - caixa.left) / caixa.width) * 100;
        const y = ((evento.clientY - caixa.top) / caixa.height) * 100;
        alvo.style.setProperty("--px", `${x.toFixed(2)}%`);
        alvo.style.setProperty("--py", `${y.toFixed(2)}%`);
      });
    }

    function aoSair() {
      const alvo = ref.current;
      if (!alvo) return;
      // Volta ao repouso em vez de congelar o brilho na ultima posicao: vidro
      // parado com um realce aceso fora do ponteiro parece defeito.
      alvo.style.removeProperty("--px");
      alvo.style.removeProperty("--py");
    }

    no.addEventListener("pointermove", aoMover);
    no.addEventListener("pointerleave", aoSair);
    return () => {
      if (quadro) cancelAnimationFrame(quadro);
      no.removeEventListener("pointermove", aoMover);
      no.removeEventListener("pointerleave", aoSair);
    };
  }, []);

  return ref;
}
```

- [ ] **Step 2: Escrever a classe**

Em `dashboard/app/globals.css`, dentro do `@layer utilities`, **depois** do bloco
das três espessuras, insira:

```css
  /* O realce especular. Posicionado por `--px`/`--py`, que o hook
     `useEspecular` escreve no no; sem o hook, o padrao 50%/0% deixa um brilho
     discreto no alto da superficie, que e um repouso plausivel e nao um bug.

     `isolation: isolate` porque o pseudo-elemento usa `overlay`, e sem
     contexto de empilhamento proprio ele mistura com o que estiver embaixo na
     pagina, nao com a superficie. */
  .especular {
    position: relative;
    isolation: isolate;
    --px: 50%;
    --py: 0%;
  }
  .especular::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: -1;
    border-radius: inherit;
    pointer-events: none;
    background: radial-gradient(
      35rem circle at var(--px) var(--py),
      oklch(1 0 0 / 9%),
      transparent 60%
    );
    transition: opacity 200ms var(--ease-fluid);
  }

  /* Os dois desligamentos, espelhando o hook. Touch nao tem hover: o realce
     ficaria aceso no ultimo ponto tocado, parado, que le como sujeira na tela. */
  @media (prefers-reduced-motion: reduce), (pointer: coarse) {
    .especular::after {
      display: none;
    }
  }
```

- [ ] **Step 3: Verificar**

```bash
cd dashboard && npx tsc --noEmit && npm run lint && npm run build
```

Esperado: sem erro.

- [ ] **Step 4: Provar o hook numa superfície real**

Ainda **sem** commitar, aplique temporariamente em `components/Painel.tsx` para
ver funcionando: torne o arquivo `"use client"`, chame
`const ref = useEspecular<HTMLElement>();` e ponha
`ref={ref} className="vidro especular"` no `<section>`.

Rode `npm run dev`, abra `/`, e confirme os três comportamentos:
1. o brilho acompanha o mouse sobre o painel;
2. tirando o mouse, ele volta ao repouso no alto — não congela onde estava;
3. com movimento reduzido ligado no SO, o brilho **não existe** e o vidro continua.

**Depois de confirmar, desfaça a alteração no `Painel.tsx`** — ela é da Task 7:

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git checkout -- dashboard/components/Painel.tsx
```

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git add dashboard/hooks/useEspecular.ts dashboard/app/globals.css
git commit -m "feat(vidro): realce especular por ponteiro, fora do React

CSS vars escritas no no dentro de rAF: um useState por pointermove
repintaria a arvore inteira com Recharts e o canvas do grafo montados.
Desliga em reduced-motion e em ponteiro grosso -- toque nao tem hover, e o
realce congelaria no ultimo ponto tocado."
```

---

## Task 5: As superfícies que flutuam

Sidebar, sheet, select e tooltip. São as que mais ganham com vidro e as de menor
risco: já flutuam sobre o conteúdo por definição.

**Files:**
- Modify: `dashboard/components/ui/sidebar.tsx`
- Modify: `dashboard/components/ui/sheet.tsx`
- Modify: `dashboard/components/ui/select.tsx`
- Modify: `dashboard/components/ui/tooltip.tsx`

**Interfaces:**
- Consumes: `.vidro`, `.vidro-fino`, `.vidro-denso` da Task 3.
- Produces: nada que outra tarefa importe.

- [ ] **Step 1: Localizar as superfícies**

```bash
cd dashboard && grep -n "bg-sidebar\|bg-popover\|bg-background\|bg-primary\b" components/ui/sidebar.tsx components/ui/sheet.tsx components/ui/select.tsx components/ui/tooltip.tsx
```

Anote cada ocorrência: são exatamente os pontos a trocar.

- [ ] **Step 2: Trocar as superfícies**

Regra de substituição, aplicada a cada ocorrência encontrada:

| Componente | De | Para |
|---|---|---|
| `sidebar.tsx` — o painel da barra | `bg-sidebar` | `vidro` (remova o `bg-sidebar`) |
| `sheet.tsx` — o conteúdo (não o overlay) | `bg-background` | `vidro-denso` |
| `select.tsx` — o popup de opções | `bg-popover` | `vidro-denso` |
| `tooltip.tsx` — o balão | `bg-primary` ou `bg-popover` | `vidro-fino` |

Duas ressalvas que o executor precisa respeitar:

- **Não toque no overlay do `sheet.tsx`** (linha 31, `bg-black/10 …
  backdrop-blur-xs`). Ele é a cortina atrás da gaveta, não a gaveta.
- No `tooltip.tsx`, se o texto usava `text-primary-foreground` por causa do
  `bg-primary`, troque para `text-foreground` — texto escuro sobre vidro escuro
  fica ilegível, e isto o gate de contraste **não** pega, porque ele mede tokens,
  não a combinação escolhida no componente.

- [ ] **Step 3: Verificar**

```bash
cd dashboard && npx tsc --noEmit && npm run lint && npm run build
```

Esperado: sem erro.

- [ ] **Step 4: Conferir a olho**

`npm run dev`. Percorra:
- **sidebar** em `/` — vira vidro, e o item ativo continua legível;
- **select** em `/configuracoes` — abra um seletor e confirme que o texto da
  opção lê **sem** competir com a tabela por trás (é o motivo de `vidro-denso`);
- **tooltip** — passe o mouse num rótulo com dica e confirme o texto legível;
- **sheet** — abra a gaveta (no telefone, a navegação lateral) e confirme.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git add dashboard/components/ui/sidebar.tsx dashboard/components/ui/sheet.tsx dashboard/components/ui/select.tsx dashboard/components/ui/tooltip.tsx
git commit -m "feat(vidro): sidebar, sheet, select e tooltip em vidro

Menu suspenso leva a espessura densa por leitura, nao por estetica: com
vidro fino o rotulo da opcao compete com a tabela atras dele."
```

---

## Task 6: Controles e superfícies de conteúdo

**Files:**
- Modify: `dashboard/components/ui/card.tsx`
- Modify: `dashboard/components/ui/button.tsx`
- Modify: `dashboard/components/ui/input.tsx`
- Modify: `dashboard/components/ui/textarea.tsx`
- Modify: `dashboard/components/ui/tabs.tsx`
- Modify: `dashboard/components/ui/badge.tsx`
- Modify: `dashboard/components/ui/pagination.tsx`
- Modify: `dashboard/components/ui/alert.tsx`
- Modify: `dashboard/components/ui/table.tsx`

**Interfaces:**
- Consumes: `.vidro`, `.vidro-fino` da Task 3.
- Produces: nada que outra tarefa importe.

**Regra que governa esta tarefa inteira:** só vira vidro o que é **superfície de
moldura**. O que é preenchimento de ação ou marcação de dado continua sólido.

| Alvo | O que fazer | Por quê |
|---|---|---|
| `card.tsx` — raiz | `bg-card` → `vidro` | é moldura |
| `button.tsx` — variantes `outline` e `secondary` | superfície → `vidro-fino` | são molduras |
| `button.tsx` — variante `default` (o `bg-primary`) | **não mexer** | ação primária é preenchimento sólido; vidro nela derruba o par verificado `--primary-foreground` sobre `--primary` (hoje 9,64:1) |
| `button.tsx` — variante `destructive` | **não mexer** | mesmo motivo |
| `input.tsx`, `textarea.tsx` | `bg-transparent`/`bg-input` → `vidro-fino` | campo é moldura |
| `tabs.tsx` — a lista | `bg-muted` → `vidro-fino` | é trilho |
| `tabs.tsx` — o gatilho ativo | **não mexer** | precisa de contraste sólido contra o trilho, ou "qual aba está ativa" vira adivinhação |
| `badge.tsx` — variante `outline` | → `vidro-fino` | é moldura |
| `badge.tsx` — demais variantes | **não mexer** | badge carrega **categoria**, e categoria é dado |
| `pagination.tsx` | segue as variantes de `button.tsx` | herda |
| `alert.tsx` | superfície → `vidro-fino`, **preservando** as cores `*-rich-*` | as `rich` carregam severidade, que é dado |
| `table.tsx` — `<thead>` fixo | → `vidro-fino` | cabeçalho flutua sobre as linhas ao rolar |
| `table.tsx` — `<tbody>`, linhas, células | **não mexer** | é dado; blur atrás de número é o defeito que este plano existe para evitar |

- [ ] **Step 1: Aplicar a tabela acima, arquivo por arquivo**

Trabalhe um arquivo por vez. Antes de cada um:

```bash
cd dashboard && grep -n "bg-" components/ui/<arquivo>.tsx
```

- [ ] **Step 2: Verificar**

```bash
cd dashboard && npx tsc --noEmit && npm run lint && npm run build && npm run contraste
```

Esperado: tudo sem erro, contraste PASS.

- [ ] **Step 3: Conferir a olho, com atenção a três coisas**

`npm run dev`, e percorra `/`, `/atendimentos`, `/configuracoes`:
1. o **botão primário** continua sólido e o rótulo dentro dele lê perfeitamente;
2. a **aba ativa** continua obviamente distinta da inativa;
3. a **etiqueta de categoria** (detrator/neutro/promotor) manteve a cor e o
   rótulo textual — nenhuma virou vidro.

- [ ] **Step 4: Commit**

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git add dashboard/components/ui
git commit -m "feat(vidro): controles e molduras em vidro, dado e acao solidos

Vira vidro so o que e moldura. Botao primario, aba ativa e etiqueta de
categoria ficam solidos -- os dois primeiros porque precisam de contraste
verificado, o terceiro porque categoria e dado."
```

---

## Task 7: O header fixo e o sistema

**Files:**
- Modify: `dashboard/components/shell/CabecalhoPagina.tsx:32`
- Modify: `dashboard/components/Painel.tsx`

**Interfaces:**
- Consumes: `.vidro`, `.vidro-fino`, `.especular` e `useEspecular` (Tasks 3 e 4).
- Produces: nada que outra tarefa importe.

**Aviso ao executor:** esta tarefa **reintroduz o painel com fundo e borda
próprios**, que o `DESIGN.md` §2.1 tinha eliminado de propósito. Isso é
deliberado e aprovado, e a emenda ao documento é a Task 10. Não "conserte" isso.

- [ ] **Step 1: O header**

Em `dashboard/components/shell/CabecalhoPagina.tsx`, linha 32, troque:

```tsx
    <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
```

por:

```tsx
    <header className="vidro-fino sticky top-0 z-20 rounded-none border-x-0 border-t-0 shadow-none">
```

O `rounded-none border-x-0 border-t-0 shadow-none` existe porque o header é uma
faixa colada no topo, não um bloco solto: as bordas laterais e a sombra do
utilitário genérico ficariam penduradas no vazio.

- [ ] **Step 2: O sistema**

Em `dashboard/components/Painel.tsx`:

1. Adicione `"use client";` na **primeira linha** do arquivo (o hook exige).
2. Importe o hook: `import { useEspecular } from "@/hooks/useEspecular";`
3. Dentro do componente, antes do `return`:
   `const refEspecular = useEspecular<HTMLElement>();`
4. Na `<section>`, troque:

```tsx
    <section className={cn("quebra-evitar min-w-0", className)}>
```

por:

```tsx
    <section
      ref={refEspecular}
      className={cn(
        "vidro especular quebra-evitar min-w-0 rounded-lg p-4 sm:p-5",
        className,
      )}
    >
```

5. Ajuste o `semPadding`: como a `<section>` agora tem `p-4 sm:p-5` própria, o
   conteúdo que gerencia o próprio respiro (tabela, gráfico) precisa sangrar
   até a borda. Troque o `<div>` do conteúdo:

```tsx
      <div className={cn("min-w-0", semPadding ? "pt-3" : "pt-4")}>
```

por:

```tsx
      <div
        className={cn(
          "min-w-0",
          semPadding ? "-mx-4 pt-3 sm:-mx-5" : "pt-4",
        )}
      >
```

- [ ] **Step 3: Verificar**

```bash
cd dashboard && npx tsc --noEmit && npm run lint && npm run build
```

Esperado: sem erro.

- [ ] **Step 4: Conferir a olho — e este é o passo mais importante do plano**

`npm run dev`. Em `/` e `/atendimentos`:

1. **role a página**: o header em vidro fino deixa o conteúdo passar por baixo
   de forma legível, e o título do header continua lendo;
2. **role a lista de atendimentos até o fim**, observando fluidez. Se houver
   engasgo perceptível, **a espessura do painel cai antes de qualquer outra
   coisa**: troque `vidro` por `vidro-fino` em `Painel.tsx` e reavalie. Isto é o
   risco de desempenho da spec §7, e este é o ponto onde ele aparece;
3. confirme que a **régua do sistema** (`border-linha` no `<header>` do painel)
   continua visível — meio ponto sobre vidro pode sumir. Se sumiu, é achado, não
   detalhe: registre e resolva subindo o `--linha` para `oklch(1 0 0 / 32%)`;
4. confirme que gráfico e tabela **sangram** até a borda do painel, sem faixa
   dupla de respiro.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git add dashboard/components/shell/CabecalhoPagina.tsx dashboard/components/Painel.tsx
git commit -m "feat(vidro): header fixo e o sistema em vidro

O painel volta a ter fundo e borda proprios, que o DESIGN.md 2.1 tinha
eliminado. E consequencia direta do reskin aprovado, nao descuido -- a
emenda ao documento vem junto."
```

---

## Task 8: Visão geral sob medida

**Files:**
- Modify: `dashboard/app/page.tsx`
- Modify: `dashboard/components/FaixaIndicadores.tsx`
- Modify: `dashboard/components/GraficoNpsLatencia.tsx`

**Interfaces:**
- Consumes: `.vidro`, `.vidro-fino`, `.especular`, `useEspecular`.
- Produces: nada que outra tarefa importe.

- [ ] **Step 1: Ler antes de escrever**

```bash
cd dashboard && cat app/page.tsx components/FaixaIndicadores.tsx && grep -n "fill\|stroke\|background\|Cartesian\|Tooltip" components/GraficoNpsLatencia.tsx | head -40
```

- [ ] **Step 2: A armadura**

Em `FaixaIndicadores.tsx`, dê à faixa de indicadores superfície `vidro` com
`especular` (mesmo padrão da Task 7, passo 2: `"use client"`, hook, `ref`,
`className`). **Não mexa** em nada dentro dela: os números continuam `.num`
tabulares, os rótulos `estimativa`/`observado` continuam colados ao número, e a
cabeça vazada do `sem sinal` continua como está.

- [ ] **Step 3: O visor do gráfico**

Em `GraficoNpsLatencia.tsx`, envolva o gráfico numa superfície **sólida**:

```tsx
<div className="rounded-md bg-card/80 p-3">
  {/* o ResponsiveContainer existente, sem alteracao */}
</div>
```

Este é o "visor" da spec §2.4: superfície opaca embutida no vidro. Blur atrás de
uma série de meio ponto come a série, e a sobreposição NPS × latência é o
compromisso vinculante do `PRODUCT.md` — ela não pode perder legibilidade.

**Não altere** cor de série, tracejado da série de tempo, domínio de eixo nem o
comportamento de `sem sinal`.

- [ ] **Step 4: Verificar**

```bash
cd dashboard && npx tsc --noEmit && npm run lint && npm run build
```

- [ ] **Step 5: Conferir a olho**

`npm run dev`, abra `/`. Confirme:
1. a série de latência continua **tracejada** e a de NPS contínua;
2. os pontos `sem sinal` continuam vazados e **não** foram desenhados em zero;
3. as etiquetas dos eixos leem sobre o visor;
4. os rótulos `estimativa` continuam visíveis na armadura, com o sublinhado
   pontilhado do `.estimado`.

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git add dashboard/app/page.tsx dashboard/components/FaixaIndicadores.tsx dashboard/components/GraficoNpsLatencia.tsx
git commit -m "feat(vidro): visao geral -- armadura em vidro, grafico em visor

O grafico ganha superficie solida embutida: blur atras de uma serie de meio
ponto come a serie, e a sobreposicao NPS x latencia e compromisso do
PRODUCT.md."
```

---

## Task 9: Atendimentos sob medida

**Files:**
- Modify: `dashboard/components/TabelaConversas.tsx`
- Modify: `dashboard/components/Transcricao.tsx`

**Interfaces:**
- Consumes: `.vidro-fino`, e o `<thead>` já ajustado na Task 6.
- Produces: nada que outra tarefa importe.

- [ ] **Step 1: Ler antes de escrever**

```bash
cd dashboard && grep -n "className" components/TabelaConversas.tsx | head -40 && grep -n "className" components/Transcricao.tsx | head -40
```

- [ ] **Step 2: A tabela**

Em `TabelaConversas.tsx`:
- o **corpo** da tabela fica em superfície sólida (`bg-card/80` no container que
  rola), pelo mesmo motivo do visor: é dado;
- o **cabeçalho fixo** já é `vidro-fino` pela Task 6; confirme que ele de fato
  gruda ao rolar e que o texto lê com linhas passando por baixo;
- **preserve integralmente** o clique na linha inteira, incluindo a guarda de
  `getSelection()` e o `closest("a,button")` — é comportamento existente e
  quebrá-lo é regressão silenciosa;
- **preserve** a coluna de categoria com rótulo textual e a célula `sem sinal`,
  que nunca mostra zero.

- [ ] **Step 3: A transcrição**

Em `Transcricao.tsx`, as bolhas de mensagem ficam **sólidas**. Elas carregam o
encoding `--dito` e a atribuição por sentença — é a tela que mais depende de
leitura de texto longo, e translucidez ali é onde vidro faz o pior estrago.

O que ganha vidro aqui é só a **moldura** em volta da lista (o painel, que já
veio da Task 7). Se a transcrição tiver cabeçalho fixo próprio, ele leva
`vidro-fino`.

- [ ] **Step 4: Verificar**

```bash
cd dashboard && npx tsc --noEmit && npm run lint && npm run build
```

- [ ] **Step 5: Conferir a olho**

`npm run dev`, abra `/atendimentos`:
1. clique numa linha e confirme que ela abre o atendimento;
2. selecione texto dentro de uma linha e confirme que **não** navega;
3. role a lista inteira observando fluidez;
4. abra uma transcrição e confirme que a fala lê confortavelmente e que a
   marcação âmbar do trecho que puxou a nota continua visível;
5. encontre um atendimento **sem sinal** e confirme que ele aparece como sem
   sinal, não como zero.

- [ ] **Step 6: Commit**

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git add dashboard/components/TabelaConversas.tsx dashboard/components/Transcricao.tsx
git commit -m "feat(vidro): atendimentos -- moldura em vidro, fala solida

A transcricao e a tela que mais depende de leitura longa: as bolhas ficam
solidas, e o vidro vive so na moldura."
```

---

## Task 10: A emenda ao contrato visual e a verificação final

**Files:**
- Modify: `dashboard/DESIGN.md`

**Interfaces:**
- Consumes: tudo.
- Produces: o contrato visual atualizado.

**Por que isto é tarefa e não rodapé:** a banca julga rigor metodológico. Uma
decisão de estilo documentada com o custo declarado é defensável; uma
contradição silenciosa entre o documento e a tela não é.

- [ ] **Step 1: A emenda ao §2.1**

Em `dashboard/DESIGN.md`, na seção "2.1 O que sai", no item que começa com
"**O cartão como estrutura de página.**", acrescente ao fim do item:

```markdown
  > **Emenda de 21/08/2026.** O painel voltou a ter fundo e borda próprios ao
  > adotar o vidro líquido (ver seção 7). A regra original continua valendo no
  > que ela realmente defendia — a página é uma pilha de sistemas, não uma
  > grade de cartões, e quem agrupa continua sendo espaço mais régua. O que
  > mudou é que o sistema agora tem **material**, e material precisa de
  > superfície. Registrado como custo assumido, não como regra revogada.
```

- [ ] **Step 2: A seção nova**

Ao fim de `dashboard/DESIGN.md`, depois da seção 6 (Movimento), acrescente:

```markdown
---

## 7. A materialidade

Adotada em 21/08/2026. Ver
`docs/superpowers/specs/2026-08-21-vidro-liquido-design.md`.

A superfície da interface é **vidro líquido**: quatro camadas com
responsabilidades disjuntas.

| Camada | O que é | Onde vive |
|---|---|---|
| 0 — ateliê | manchas de luz fixas sobre o grafite | `components/shell/Atelier.tsx` |
| 1 — vidro | superfície translúcida com quina iluminada | `.vidro-fino`, `.vidro`, `.vidro-denso` |
| 2 — especular | realce que segue o ponteiro | `hooks/useEspecular.ts` + `.especular` |
| 3 — dado | régua, séries, números — opaco, sem blur | os componentes de dado |

**A camada 0 não é decoração.** Vidro sobre fundo chapado é indistinguível de
cinza mais claro: sem luz atrás, não há o que refratar. Ela é estática, e essa
é uma decisão — luz derivada do dado criaria um canal de cor sem rótulo, contra
a seção 3.4 e contra a regra de que a cor da marca nunca codifica valor.

**Três espessuras, não uma escala.** `backdrop-filter` é o efeito mais caro de
CSS, e cada espessura resolve um problema distinto: o fino sinaliza flutuação,
o médio é superfície de trabalho, o denso existe porque num menu suspenso o
conteúdo atrás **precisa** sumir para o rótulo da opção ser legível.

**A regra dura: nada que carrega dado é translúcido.** Gráfico, tabela,
transcrição e régua desenham em superfície opaca embutida no vidro — um visor.
Blur atrás de uma série de meio ponto come a série, e a régua da pauta é meio
ponto.

**O contraste governa o vidro, não o contrário.** Cada espessura declara um
`--vidro-<n>-piso`: a cor mais clara que ela pode assumir, com o vidro composto
sobre a mancha mais brilhante do ateliê. É contra esse pior caso que
`npm run contraste` verifica o texto. Par que reprova faz a espessura ganhar
opacidade — o gate nunca é afrouxado. Se um piso passar de `--muted` (L 0.274)
em claridade, o vidro clareou demais.

**O especular tem dois desligamentos**, e o segundo é o esquecido:
`prefers-reduced-motion` e **ponteiro grosso**. Toque não tem hover, e o realce
congelaria no último ponto tocado — pior que não existir.
```

- [ ] **Step 3: A verificação de ponta a ponta**

```bash
cd dashboard && npm run contraste && npx tsc --noEmit && npm run lint && npm run build
cd .. && uv run pytest -q
```

Esperado: tudo verde. O `pytest` é regressão — nada de back-end mudou, e se ele
falhar, alguma coisa saiu do escopo.

- [ ] **Step 4: A conferência manual que script nenhum pega**

Com `npm run dev`, percorra as **sete** telas — `/`, `/atendimentos`, uma
transcrição, `/modelo`, `/configuracoes`, `/integracoes`, `/analisar`, `/grafo` —
e confirme:

1. nenhuma tela ficou com texto sobre vidro difícil de ler;
2. `prefers-reduced-motion` ligado no SO → nenhum realce especular, vidro intacto;
3. largura de telefone → nenhum realce, layout de pé, sem rolagem horizontal;
4. rolagem longa em `/atendimentos` sem engasgo;
5. o **grafo** continua legível — ele não herda material do chassi, e destoar
   ali é achado a registrar, não a consertar nesta entrega;
6. estados vazios continuam **nomeando o que falta**, sem número inventado.

Tire screenshot das sete telas para o julgamento visual final.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/dell08/Documents/GitHub/Fraus"
git add dashboard/DESIGN.md
git commit -m "docs(design): a materialidade, e a emenda ao contrato do painel

O painel com fundo proprio voltou. Fica registrado com o motivo em vez de
deixar o documento e a tela se contradizendo em silencio."
```

---

## Auto-revisão do plano

**Cobertura da spec:** §2.1 ateliê → Task 2. §2.2 vidro → Tasks 1 e 3. §2.3
especular → Task 4. §2.4 dado opaco → regra global + Tasks 6, 8, 9. §3 contraste
→ Task 1. §4.1 chassi → Tasks 5, 6, 7. §4.2 sob medida → Tasks 8, 9. §4.3
herança → verificado na Task 10, passo 4. §4.4 documentação → Task 10. §5
invariantes → Global Constraints + conferências das Tasks 6, 8, 9. §6
verificação → Task 10, passos 3 e 4. §7 riscos → Task 7, passo 4 (desempenho) e
Task 1 (contraste). Sem lacuna.

**Placeholders:** nenhum "TBD", nenhum "similar à Task N" — as instruções de
`"use client"` + hook + ref são repetidas por extenso na Task 8. Todo passo de
código traz o código.

**Consistência de tipos:** `useEspecular<T>()` devolve `RefObject<T | null>`, e
tanto a Task 7 quanto a Task 8 a chamam como `useEspecular<HTMLElement>()` para
pendurar em `<section>`. Os nomes de token declarados na Task 1 são exatamente
os consumidos nas Tasks 3 e 4: `--vidro-{fino,,denso}-fundo`,
`--vidro-{fino,,denso}-piso`, `--vidro-blur{-fino,,-denso}`, `--vidro-quina`,
`--vidro-quina-baixa`, `--vidro-sombra`.
