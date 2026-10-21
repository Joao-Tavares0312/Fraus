# Widgets em camadas e céu vivo — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** trocar o fundo da LP pelo céu animado da arte do João e redesenhar botões, cards e texto na direção C, "Camadas do FR", inteira na LP e contida na dashboard, a partir de uma definição única de forma.

**Architecture:** um arquivo CSS compartilhado (`dashboard/app/camadas.css`, importado por `globals.css`, que o layout raiz carrega para a LP e para a dashboard) define o canto cortado, as placas, o fio dourado, a pincelada e os tokens das placas nos dois temas. A LP consome essas classes no `lp.css` e na marcação; a dashboard as consome nas variantes `cva`. O céu é um componente de servidor com posições geradas por PRNG de semente fixa e animado só em CSS.

**Tech Stack:** Next.js (App Router), Tailwind v4 + `cva`, CSS puro na LP, Vitest (`environment: node`, `renderToStaticMarkup`), validador Playwright da LP.

**Spec:** `docs/superpowers/specs/2026-10-21-widgets-camadas-e-ceu-design.md`. Mockups aprovados em `/home/joaopedro/GITHUB/Fraus/.superpowers/brainstorm/3424194-1792584196/content/` (`widgets-v1.html` coluna C, `dashboard-intensidade.html` opção 2, `fundo-vivo.html`); as artes estão em `/home/joaopedro/Documents/Notas/fraus-bg-dark.png` e `fraus-bg-gold.png`.

Todos os caminhos abaixo são relativos a `dashboard/` no worktree `/home/joaopedro/GITHUB/Fraus-widgets`. Os comandos rodam dentro de `dashboard/`.

## Global Constraints

- **Não muda:** `components/lp-nova/Coreografia.tsx`, `lib/lp-nova/coreografia.ts`, `lib/lp-nova/palco-fr.ts`, as poses, as seções, a ordem delas e os textos. Mudam só o fundo e a aparência dos widgets.
- **`data-embaralhar` reescreve `textContent`**: nenhum elemento filho dentro de `.btn` ou `.tag` da LP. As placas são `::before`, `::after` e `filter: drop-shadow`.
- **Sem `Math.random()` no render**: o céu é determinístico e renderizado no servidor.
- O céu anima só `opacity` e `transform`/`translate`, sem canvas e sem script por quadro. Com reduce, fica parado e visível.
- **Uma fonte:** o polígono do canto e as cores das placas existem só em `app/camadas.css`.
- **Foco visível** em todo controle com canto cortado, nos dois temas: o `clip-path` corta o anel externo, então o foco é desenhado por dentro.
- Alvo mínimo de 44 px na LP. Contraste AA (`npm run contraste`). Ouro é ação e marca, nunca dado. Sem dependência nova.
- Identificadores em português sem acento. Commits `tipo(escopo): resumo` em português sem acento, terminando com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

### Valores fixados pelo spec e pelos mockups

| Item | Valor |
|---|---|
| Ângulo dos riscos | −22° da vertical (`rotate(-22deg)`) |
| Pontos | 140; 8% grandes (5–7 px), o resto entre 1,5 e 3 px; opacidade de 0,35 a 1; 60% piscam com ciclo de 2,5 a 7 s |
| Riscos | 26; comprimento de 180 a 520 px; alfa de 0,04 a 0,12; descida de 14 a 30 s, deslocando `(0,45·L, 1,1·L)` |
| Cor dos pontos | `#e9cf8e`, com brilho `0 0 (1,6·s) rgba(233,207,142,.45)` |
| Placas no escuro | face `--primary` `#D6BA72`, placa 2 `#a8904f`, placa 3 `#6f5f36`; placas dos cards `#34302a` e `#2a2621` |
| Placas no fecho (`.lp.inv`) | face `#171819`, placa 2 `#3a3326`, placa 3 `#7a6532`; texto ouro |
| Deslocamento das placas | botão LP: repouso 3/6 px, hover face −3, placa 3 em 7 px; card: repouso 4/8, hover face −2, placas 5/12 |
| Canto (`--chanfro`) | botão LP 12 px, card LP 18 px, botão da dashboard 9 px (`sm`/`xs` 7 px), card da dashboard 12 px, `.tag`/badge 6 px |
| Pincelada | `skewX(-24deg)`, inset `.08em -.12em .02em`, fundo ouro, texto `#171819` |
| Easing das placas | `cubic-bezier(.3,1.4,.5,1)` no botão, 300 ms; `cubic-bezier(.3,1.3,.5,1)` no card, 350 ms |

## Review Focus

1. **Hover depois do embaralhar:** passar o mouse num `.btn` da LP roda o embaralhar, que reescreve o texto. As placas precisam continuar lá depois, e o nome acessível também. *(Task 3)*
2. **Foco por teclado em controle cortado:** o Tab num `Input`, `SelectTrigger`, `TabsTrigger` ou `Button` mostra foco visível dentro do recorte, nos dois temas. *(Tasks 4 e 5)*
3. **Reduce e sem JS na LP:** com reduce o céu fica parado mas presente; sem JS o céu aparece completo, porque é SSR. *(Task 1)*
4. **Fecho dourado:** ao entrar no `#fecho` (`.lp.inv`), os pontos somem, os riscos escurecem e os botões invertem (face grafite, texto ouro). *(Tasks 1 e 3)*
5. **Indicador sem dado ou com erro:** os quatro cards separados mantêm `—`, "Sem estimativa" e o erro local no próprio card, sem um card vazio colapsar a grade, e a impressão continua legível. *(Task 6)*

---

### Task 1: Céu vivo da LP

**Files:**
- Create: `lib/lp-nova/ceu.ts`, `lib/lp-nova/ceu.test.ts`, `components/lp-nova/Ceu.tsx`
- Modify: `app/page.tsx` (montar `<Ceu />` como primeiro filho de `.lp`), `app/lp.css` (remover o `.lp::after` atual e adicionar as regras do céu), `scripts/validar-lp-playwright.mjs`

**Interfaces:**
- Produces: `export type Ponto = { x: number; y: number; tamanho: number; opacidade: number; pisca: boolean; ciclo: number; atraso: number }`, `export type Risco = { x: number; y: number; comprimento: number; alfa: number; duracao: number; atraso: number }`, `export function gerarCeu(semente: number): { pontos: Ponto[]; riscos: Risco[] }` (x/y em %, tempos em s, `atraso` ≤ 0) e `export const SEMENTE_CEU = 7`. `Ceu()` é um componente de servidor que renderiza `<div className="lp-ceu" aria-hidden="true">` com `<i className="lp-ponto">` e `<b className="lp-risco">`, passando os valores por variáveis CSS inline (`--s`, `--o`, `--d`, `--l`, `--a`).

- [ ] **Step 1: Write the failing tests** in `lib/lp-nova/ceu.test.ts`
  - `gerarCeu(SEMENTE_CEU)` tem 140 pontos e 26 riscos.
  - Chamar duas vezes com a mesma semente dá resultados `toEqual`; uma semente diferente dá resultado diferente.
  - Todo ponto tem `0 ≤ x,y ≤ 100`, `0.35 ≤ opacidade ≤ 1`, `1.5 ≤ tamanho ≤ 7` e `atraso ≤ 0`; os que piscam têm `2.5 ≤ ciclo ≤ 7`.
  - A fração que pisca fica entre 0,5 e 0,7.
  - Todo risco tem `180 ≤ comprimento ≤ 520`, `0.04 ≤ alfa ≤ 0.12` e `14 ≤ duracao ≤ 30`.
  - `renderToStaticMarkup(<Ceu />)` é idêntico em duas chamadas, contém `aria-hidden="true"` e 140 ocorrências de `class="lp-ponto`.
- [ ] **Step 2: Run** `npx vitest run lib/lp-nova/ceu.test.ts`. Expected: FAIL (módulo inexistente).
- [ ] **Step 3: Implement `gerarCeu` and `Ceu`.** PRNG `mulberry32(semente)`, sem `Math.random`. Os intervalos estão na tabela de valores. O teste de `Ceu` fica no mesmo arquivo; se o import de `.tsx` exigir, renomeie o arquivo para `ceu.test.tsx` e inclua `lib/**/*.test.tsx` no `vitest.config`.
- [ ] **Step 4: CSS do céu em `app/lp.css`.**
  - `.lp-ceu`: `position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden` e fundo `radial-gradient(120% 90% at 30% 20%, #1b1c1f, #131416 70%)`.
  - Animação `lp-pisca` (opacidade até .08, escala .6, no meio do ciclo) e `lp-cai` (entra e sai em 15%/85%, desloca `calc(var(--l)*.45) calc(var(--l)*1.1)`).
  - `.lp.inv .lp-ceu`: fundo `radial-gradient(120% 90% at 50% 40%, #d5b86f, #c3a663 80%)`, pontos com `opacity: 0` e riscos `rgba(120,95,40, calc(var(--a)*3))`. A cor transiciona em 0,6 s, como o `.lp`.
  - No reduce, a regra global já zera `animation`; adicione `.lp-risco { opacity: 1 }` dentro do bloco de reduce, para os riscos não sumirem (na animação eles começam em `opacity: 0`).
  - Apague o `.lp::after`.
- [ ] **Step 5: Add validator checks** em `scripts/validar-lp-playwright.mjs`:
  - `exigir("ceu: pontos", count(".lp-ceu .lp-ponto") === 140)` no cenário padrão e no sem JS;
  - no cenário de reduce, `getComputedStyle(primeiro .lp-risco).animationName === "none"` e `opacity === "1"`;
  - no fecho, depois de `.lp.inv`, a opacidade computada de um `.lp-ponto` é `"0"`.
- [ ] **Step 6: Run** `npx vitest run lib/lp-nova/ceu.test.ts && npm run lint && npm run build`, depois, com `npm run start` rodando, `npm run test:lp`. Expected: tudo PASS, com as linhas `ceu:` no relatório.
- [ ] **Step 7: Commit** `feat(lp): ceu vivo da arte do Joao no lugar dos riscos fixos`.

### Task 2: Primitivas compartilhadas de forma

**Files:**
- Create: `app/camadas.css`, `lib/camadas.test.ts`
- Modify: `app/globals.css` (`@import "./camadas.css";` logo após os imports existentes; tokens das placas em `:root, .dark` e `.light`)

**Interfaces:**
- Produces (classes CSS, consumidas pelas Tasks 3 a 6):
  - `.chanfro`: `clip-path` do canto cortado com `var(--chanfro, 12px)` no topo-esquerdo e no canto inferior direito, mais o traço diagonal da borda nesses dois cantos (gradientes de fundo de `var(--cor-borda-chanfro, var(--border))`, de modo que a borda de 1 px continue na diagonal). Foco: `.chanfro:focus-visible { outline: 2px solid var(--ring); outline-offset: -2px }`.
  - `.placas`: o elemento fica sem `clip-path` e com fundo transparente, `position: relative; isolation: isolate`. `::before` é a face (`var(--placa-face)`, mesmo polígono) e `::after` é a placa 2 (`var(--placa-2)`, deslocada `var(--placa-repouso, 3px)`). A placa 3 é `filter: drop-shadow(var(--placa-fundo, 6px) var(--placa-fundo, 6px) 0 var(--placa-3))` no próprio elemento. No `:hover`/`:focus-visible`, a face vai para `var(--placa-sobe, -3px)` e a sombra para `var(--placa-abre, 7px)`.
  - `.placas-so-hover`: igual, mas em repouso a placa 2 e a sombra ficam em 0.
  - `.fio`: segmento dourado de 2 px no topo à direita, com 40% da largura e `linear-gradient(90deg, transparent, var(--primary))`, aplicado como camada de `background-image`, sem consumir pseudo-elemento.
  - `.fio-hover`: sublinhado dourado de 2 px que cresce de 0 a 100% da largura no `:hover`/`:focus-visible` (usa `::after`; não combinar com `.placas`).
  - `.pincel`: a pincelada da palavra-chave, com os valores da tabela.
  - `.fenda`: marca diagonal de 24 px no canto superior direito, com opacidade .5 (camada de `background-image`).
  - Tokens em `:root, .dark`: `--placa-2: #a8904f; --placa-3: #6f5f36; --placa-card-2: #34302a; --placa-card-3: #2a2621`. Em `.light`: as mesmas variáveis, derivadas com `color-mix(in oklch, var(--primary), var(--foreground) 25%/45%)` para o botão e `color-mix(in oklch, var(--card), var(--foreground) 8%/14%)` para os cards.

- [ ] **Step 1: Write the failing test** `lib/camadas.test.ts` (lê arquivos como `hierarquia.test.ts` faz):
  - `camadas.css` existe e define `.chanfro`, `.placas`, `.placas-so-hover`, `.fio`, `.fio-hover`, `.pincel` e `.fenda`;
  - o `globals.css` importa `./camadas.css`;
  - **guarda da fonte única:** nenhum arquivo em `app/` ou `components/`, além de `camadas.css`, contém `calc(100% - var(--chanfro` nem os hexadecimais `#a8904f`/`#6f5f36`;
  - `.light` define `--placa-2` e `--placa-3`.
- [ ] **Step 2: Run** `npx vitest run lib/camadas.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement** `app/camadas.css` e os tokens, conforme a Interface.
- [ ] **Step 4: Run** `npx vitest run lib/camadas.test.ts && npm run build && npm run contraste`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(interface): primitivas de canto, placas e pincelada numa fonte so`.

### Task 3: Widgets da LP

**Files:**
- Modify: `app/lp.css`, `components/lp-nova/Palavras.tsx`, `components/lp-nova/secoes/Hero.tsx`, `scripts/validar-lp-playwright.mjs`
- Test: `components/lp-nova/Palavras.test.tsx` (novo)

**Interfaces:**
- Consumes: as classes da Task 2.
- Produces: `Palavras({ texto, destaque }: { texto: string; destaque?: string })`. A palavra igual a `destaque` sai como `<span class="w w-pincel"><span class="pincel">análise</span></span>`; as outras não mudam.

- [ ] **Step 1: Write the failing test** `Palavras.test.tsx`:
  - `renderToStaticMarkup(<Palavras texto="A análise começa." destaque="análise" />)` contém exatamente uma `class="pincel"`, envolvendo `análise`, e três `class="w`;
  - sem `destaque`, a saída é idêntica à atual (zero `pincel`).
- [ ] **Step 2: Run** `npx vitest run components/lp-nova/Palavras.test.tsx`. Expected: FAIL.
- [ ] **Step 3: Implement** o parâmetro `destaque` e passe `destaque="análise"` no `Hero`. `.lp .w.w-pincel` ganha folga lateral e vertical para a pincelada inclinada não sair cortada pela máscara (`padding-inline: .14em; margin-inline: -.14em` ou equivalente).
- [ ] **Step 4: Restyle in `app/lp.css`**, peça por peça, conforme a tabela "Widgets da LP" do spec e os valores deste plano:
  - `.btn` → `placas`, com os valores do botão da LP;
  - `.btn.o` → `chanfro fio-hover`;
  - `.card` e `.stat` → `placas` com as cores de card e `fio`; `.stat` também com `fenda`;
  - `.ck li` → `chanfro fio`;
  - `.tag` → `chanfro` de 6 px;
  - `.step::before` → quadrado de 18 px com canto cortado no lugar do círculo;
  - `.ln-aba` e `.leituras-gravadas summary` → `chanfro`;
  - variantes `.lp.inv`, com as cores do fecho.

  A forma chega pelas classes compartilhadas **na marcação**: as seções ganham só nomes de classe (por exemplo, `className="btn placas mag rv"`), e o texto, a ordem e os atributos `data-*` não mudam. O `lp.css` declara apenas as variáveis de cada peça (`--chanfro`, `--placa-face`, `--placa-2`, `--placa-3` e os deslocamentos), nunca o polígono, como a guarda da Task 2 exige. O `.lp .btn` hoje tem `background` e `border`; remova os dois, porque a face vem do `::before`.
- [ ] **Step 5: Add validator checks**: no desktop, depois de `hover` no primeiro `.lp .btn` e de esperar 1 s,
  - `textContent` volta ao original;
  - `getComputedStyle(btn, "::before").content !== "none"` e o `filter` do elemento contém `drop-shadow`;
  - o `aria-label` é igual ao texto;
  - a captura `lp-hero` mostra a pincelada inteira, conferida no olho.
- [ ] **Step 6: Run** `npx vitest run && npm run lint && npm run build`; depois `npm run test:lp` e as capturas do Hero, do Problema, dos Sinais, do Analista, dos Limites e do Fecho, em desktop (1440×900) e celular (390×844). Expected: PASS, e as placas, a pincelada e o fecho como nos mockups.
- [ ] **Step 7: Commit** `feat(lp): botoes, cards e titulos em camadas do FR`.

### Task 4: Botão e badge da dashboard

**Files:**
- Modify: `components/ui/button.tsx`, `components/ui/badge.tsx`
- Test: `components/ui/button.test.ts` (novo)

**Interfaces:**
- Consumes: `.chanfro`, `.placas`, `.fio-hover` (Task 2).
- Produces: `buttonVariants` com a mesma API (`variant`, `size`); nenhum consumidor muda.

- [ ] **Step 1: Write the failing test** `button.test.ts`, chamando `buttonVariants`:
  - `({})` (default/default) contém `placas` e não contém `rounded-md`;
  - `({ variant: "outline" })` e `({ variant: "secondary" })` contêm `chanfro` e `fio-hover`, mas não `placas`;
  - `({ variant: "destructive" })` contém `chanfro` e não contém `fio-hover` nem `placas`;
  - `({ variant: "ghost" })` e `({ variant: "link" })` não contêm `chanfro` nem `placas`;
  - `({ size: "icon" })`, `"icon-sm"`, `"icon-xs"` e `"icon-lg"` não contêm `chanfro` nem `placas`, para qualquer variante;
  - `({ size: "sm" })` declara `[--chanfro:7px]`.
  - `badgeVariants({ variant: "outline" })` contém `chanfro`.
- [ ] **Step 2: Run** `npx vitest run components/ui/button.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Troque o arredondamento pelas classes compartilhadas, com `[--chanfro:9px]` como base e `7px` em `xs`/`sm`.
  - Use `compoundVariants` para tirar canto e placas dos tamanhos `icon*`; mantenha `rounded-md` neles e em `ghost`/`link`.
  - O foco do `default` (que não tem `clip-path`) usa o `outline` padrão.
  - No `default`, o deslocamento é proporcional (repouso 2/4 px, hover −2 e 5 px, como no mockup da dashboard).
  - Mantenha `active:translate-y-px` só onde não houver placas; nas placas, o `:active` aproxima a face (`--placa-sobe: 2px`).
- [ ] **Step 4: Run** `npx vitest run && npm run lint && npm run build`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(interface): botao e etiqueta com canto da fenda`.

### Task 5: Controles e regiões com canto

**Files:**
- Modify: `app/globals.css` (`.superficie` vira canto cortado com `--chanfro: 12px`; `.superficie-flutuante` não muda), `components/ui/input.tsx`, `components/ui/textarea.tsx`, `components/ui/select.tsx` (só o `SelectTrigger`), `components/ui/tabs.tsx` (`TabsList` default e `TabsTrigger`), `components/ui/alert.tsx`
- Test: `lib/camadas.test.ts` (estender)

**Interfaces:**
- Consumes: `.chanfro` (Task 2).

- [ ] **Step 1: Extend the failing test**:
  - em `globals.css`, a regra `.superficie` não tem `border-radius: 12px` e é coberta pelo `camadas.css`, com `.superficie` incluída no seletor de `.chanfro`;
  - `input.tsx`, `textarea.tsx`, o `SelectTrigger` e o `TabsTrigger` não contêm `rounded-md` nem `focus-visible:ring-2` (o foco passa a vir do `.chanfro`) e contêm `chanfro` ou `superficie`;
  - `.superficie-flutuante` continua com `border-radius: 12px`.
- [ ] **Step 2: Run** `npx vitest run lib/camadas.test.ts`. Expected: FAIL.
- [ ] **Step 3: Implement.** Campos e gatilhos usam `--chanfro: 7px`. O `alert` mantém a borda esquerda colorida (`border-l-2`), e o canto não pode apagá-la.
- [ ] **Step 4: Verify focus in the browser.**
  - Com `npm run dev` e `DASHBOARD_URL`, rode `node scripts/validar-navegacao-playwright.mjs`.
  - Tire capturas com Tab focando um `Input` (Analisar), um `SelectTrigger` e um `TabsTrigger`, nos temas Escuro e Claro.
  - Expected: o validador passa e o anel de foco aparece dentro do recorte.
- [ ] **Step 5: Run** `npx vitest run && npm run lint && npm run build && npm run contraste && npm run pisos`. Expected: PASS.
- [ ] **Step 6: Commit** `feat(interface): campos, abas e regioes com canto cortado`.

### Task 6: Painel dominante e faixa de indicadores

**Files:**
- Modify: `lib/hierarquia.ts`, `lib/hierarquia.test.ts`, `components/CartaoIndicador.tsx`, `components/FaixaIndicadores.tsx`, `components/FaixaIndicadores.test.tsx`, `app/globals.css` (regras `.faixa-indicadores`, linhas 316–324)

**Interfaces:**
- Produces: `classesDoNivel("dominante")` passa a conter `superficie fio`, e `classesDoNivel("apoio")` não muda (`painel-apoio p-4 sm:p-5`). `CartaoIndicador` ganha `destaque?: boolean` (põe a classe `fio`); `FaixaIndicadores` passa `destaque` só ao NPS.

- [ ] **Step 1: Write the failing tests.**
  - `hierarquia.test.ts`: `classesDoNivel("dominante")` contém `fio`; `classesDoNivel("apoio")` é `"painel-apoio p-4 sm:p-5"`.
  - `FaixaIndicadores.test.tsx`: o mock de `CartaoIndicador` passa a expor `data-destaque={String(!!destaque)}`. Só o cartão "NPS inferido" tem `data-destaque="true"`.
  - Um novo caso renderiza o `CartaoIndicador` real (sem mock, com `motion/react` mockado para `div`). `className` contém `superficie` e `fio` quando `destaque`, e com `valor: null` e `erro` o texto do erro continua no próprio card.
- [ ] **Step 2: Run** `npx vitest run lib/hierarquia.test.ts components/FaixaIndicadores.test.tsx`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - `.faixa-indicadores` vira uma grade com `gap: .75rem`, sem borda, fundo, divisórias nem padding próprios: duas colunas, e quatro a partir de 1200 px.
  - Cada `CartaoIndicador` recebe `superficie` (canto de 12 px) e `fio` quando `destaque`.
  - Sem placas: o card não é clicável.
  - No `@media print`, os cards mantêm a borda e `break-inside: avoid`.
- [ ] **Step 4: Run** `npx vitest run && npm run build`. Capture a visão geral (`/dashboard`) com dados de demonstração (`uv run python scripts/api_demo.py` na raiz e o dashboard apontando para `:8000`) nos dois temas, em 1440 px e 390 px, além de um estado com a API desligada (o `—` em cada card). Expected: quatro cards separados, o NPS com fio e o painel NPS × latência com canto e fio.
- [ ] **Step 5: Commit** `feat(dashboard): indicadores em cards separados e fio no dominante`.

### Task 7: Documentação e verificação final

**Files:**
- Modify: `DESIGN.md` (frontmatter `rounded:` → `chanfro:` com os valores da tabela; seção "Direção", com o bullet de controles e regiões; seção "LP", com um parágrafo "Céu" descrevendo o comportamento no reduce, no fecho e sem JS, e o registro de que ele é a única animação contínua permitida, em CSS e atrás do palco; seção "Dashboard", com o canto cortado, o fio do dominante, as placas só onde se clica e a faixa em cards), `../docs/` se `scripts/reunir_docs.py` copiar o DESIGN.md (rodar o script)
- Test: nenhum novo

- [ ] **Step 1: Update `DESIGN.md`.** Mantenha a frase que proíbe fundo animado na dashboard.
- [ ] **Step 2: Run** na raiz `uv run python scripts/reunir_docs.py` e `uv run mkdocs build --strict`. Expected: build limpo.
- [ ] **Step 3: Full gate** em `dashboard/`: `npm test && npm run lint && npm run build && npm run contraste && npm run pisos && npm run test:lp`. Expected: tudo PASS. Cole a saída no relatório.
- [ ] **Step 4: Final look.** Capture a LP (Hero, Sinais, Faixa, Analista, Limites e Fecho) em desktop e celular, além de reduce e sem JS, e a dashboard (visão geral, Atendimentos e Analisar) em Escuro e Claro. Compare com os mockups aprovados e anote as divergências.
- [ ] **Step 5: Commit** `docs(design): canto da fenda, placas e ceu vivo`.
