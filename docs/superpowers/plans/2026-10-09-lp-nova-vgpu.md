# LP nova com vgpu — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** uma landing page em `/leitura` que vende o Fraus, com um campo de partículas WebGPU (vgpu) que conta a leitura da conversa, e leituras reais pré-gravadas pelo motor de produção.

**Architecture:** Server Components para todo o texto; um único componente de cliente monta um canvas vgpu fixo, com compute shader avançando partículas num storage buffer e um `draw` instanciado lendo esse buffer. A rolagem e a leitura escolhida viram uniforms. As partes de decisão (enxames, regime, validação das leituras) são funções puras testadas no Vitest.

**Tech Stack:** Next 16 (Turbopack), React 19, `vgpu@0.5.0` + `@vgpu/wgsl` (loader), Vitest, Playwright, Python 3.11 (`httpx` já é dependência do projeto? conferir; se não, `urllib`).

**Spec:** `docs/superpowers/specs/2026-10-09-lp-nova-vgpu-design.md`

## Global Constraints

- Rota `/leitura`; nada em `app/page.tsx`, `components/lp/`, `lib/vitrine/` muda.
- `vgpu` fixado em `0.5.0` exato (é 0.x: minor quebra API).
- Cores: âmbar `--dito`, azul `--medido`, dourado só em ação/foco/marca, magenta só no orbe e no halo. Ler os tokens de `app/globals.css`; não digitar oklch novo.
- Bricolage só via `.display-vitrine`/`.titulo-vitrine`. Sem kicker acima de título.
- Nenhum `?? 0` / `|| 0` em `components/lp-nova/` e `lib/lp-nova/`.
- Score, nota, categoria e marcas vêm do `leituras.json` gravado do servidor; nada recalculado.
- Números de features e famílias só de `components/lp/fatos.ts` (`FATOS_DO_MODELO`, `FAMILIAS_DO_VETOR`).
- Identificadores em português sem acento; texto de tela com acento. Commits `tipo(escopo): resumo` sem acento.
- Canvas só nesta rota; `gpu.dispose()` ao desmontar; laço pausa com `document.hidden`.

## Review Focus

1. `leituras.json` ausente (antes do João rodar o script): a seção 4 mostra o estado vazio que nomeia o que falta, sem inventar leitura. Teste em Task 4.
2. WebGPU presente mas `init()` rejeita (adapter nulo, device perdido): a página cai no pôster, sem erro de console não tratado. Teste em Task 3 (regime) + Playwright em Task 9.
3. Navegação para `/entrar` no meio do laço: dispose sem `pageerror` (device destruído com frame em voo). Playwright em Task 9.
4. Leitura `sem-sinal` selecionada: LED apagado com rótulo "sem sinal", campo cinza; nunca "0". Teste em Task 4 e Task 7.
5. Viewport 390 px: nenhuma rolagem horizontal (`window.scrollX` depois de rolar à direita). Playwright em Task 9.

---

### Task 1: dependência, loader WGSL e rota de fumaça

**Files:**
- Modify: `dashboard/package.json` (dep `vgpu@0.5.0`, script `wgsl`)
- Modify: `dashboard/next.config.ts` (regra `*.wgsl`)
- Create: `dashboard/wgsl-env.d.ts`
- Create: `dashboard/app/leitura/page.tsx` (fumaça: gradiente)
- Create: `dashboard/lib/lp-nova/shaders/fumaca.wgsl` (removido na Task 6)
- Modify: `.mcp.json` (servidor `vgpu`)

- [ ] `cd dashboard && npm install vgpu@0.5.0 --save-exact`
- [ ] `next.config.ts`: dentro de `turbopack`, acrescentar `rules: { "*.wgsl": { loaders: ["@vgpu/wgsl/loader-webpack"], as: "*.js" } }`
- [ ] `wgsl-env.d.ts`: `/// <reference types="@vgpu/wgsl/wgsl-types" />`
- [ ] script `"wgsl": "node scripts/checar-wgsl.mjs"` — percorre `lib/lp-nova/shaders/*.wgsl` e roda `npx vgpu check <arq>` em cada um, saindo não-zero no primeiro erro. Módulos puros (só `export`) também passam pelo check.
- [ ] Página de fumaça: componente de cliente que faz `init()` → `surface()` → `effect()` com `fumaca.wgsl` (`return vec4f(uv, 0.4, 1.0)`).
- [ ] Verificar: `npm run wgsl` verde; `npm run build` verde; `npm run dev` e abrir `/leitura` no Chrome mostra o gradiente.
- [ ] `.mcp.json`: `"vgpu": { "command": "npx", "args": ["-y", "vgpu@0.5.0", "mcp", "--project-from-cwd"] }`
- [ ] Commit `chore(lp-nova): vgpu 0.5.0, loader wgsl e rota de fumaca`

### Task 2: enxames (puro)

**Files:** Create `dashboard/lib/lp-nova/enxames.ts`, `dashboard/lib/lp-nova/enxames.test.ts`

**Interfaces — Produces:**
```ts
export type Enxame = { chave: string; qtd: number; inicio: number; particulas: number; centro: [number, number] };
export function distribuirEnxames(total: number): Enxame[];
```
`particulas` proporcional a `qtd / FATOS_DO_MODELO.features`, maior resto para fechar a soma em `total`; `inicio` é o índice da primeira partícula do enxame; `centro` no círculo de raio 0.32 em torno de (0.5, 0.5), ângulo pela ordem de `FAMILIAS_DO_VETOR`.

- [ ] Testes: soma == total para 4000, 16000, 120000; ordem e chaves iguais a `FAMILIAS_DO_VETOR`; `inicio` contíguo; família com qtd 7 tem mais partículas que família com qtd 3; `total` < 7 lança `RangeError`.
- [ ] Falhar, implementar, passar (`npx vitest run lib/lp-nova/enxames.test.ts`), commit `feat(lp-nova): particulas por familia na contagem real`.

### Task 3: regime (puro)

**Files:** Create `dashboard/lib/lp-nova/regime.ts`, `regime.test.ts`

**Interfaces — Produces:**
```ts
export type Regime = "vivo-alto" | "vivo-baixo" | "poster";
export type MotivoRegime = "inicial" | "sem-webgpu" | "falha-gpu" | "movimento-reduzido" | "quadros" | "bateria";
export type Sinais = { temWebGpu: boolean; movimentoReduzido: boolean; falhouInit: boolean };
export function regimeInicial(s: Sinais): { regime: Regime; motivo: MotivoRegime };
export function rebaixar(atual: Regime, motivo: "quadros" | "bateria"): { regime: Regime; motivo: MotivoRegime };
export const PARTICULAS: Record<"vivo-alto" | "vivo-baixo", { desktop: number; celular: number }>; // 120000/16000 e 30000/4000
export function rotuloDoRegime(r: Regime, m: MotivoRegime): string; // "GPU · alto", "pôster · sem WebGPU" ...
```
Regras: movimento reduzido vence tudo → pôster; sem WebGPU → pôster; init falhou → pôster; senão vivo-alto. `rebaixar` só desce de alto para baixo; de baixo ou pôster, devolve o mesmo (nunca sobe, nunca oscila).

- [ ] Testes para cada combinação + `rebaixar("vivo-baixo")` idempotente + rótulos.
- [ ] Commit `feat(lp-nova): regime da cena com descida unica`.

### Task 4: leituras gravadas — conversas, script e validação

**Files:**
- Create: `dados_lp/{obrigado,ironia,espera,promotor,sem-sinal}.csv`
- Create: `scripts/gravar_leituras_lp.py`, `tests/test_gravar_leituras_lp.py`
- Create: `dashboard/lib/lp-nova/leituras.ts`, `leituras.test.ts`

**Interfaces — Produces (TS):**
```ts
export type Leitura = { id: "obrigado"|"ironia"|"espera"|"promotor"|"sem-sinal"; titulo: string;
  score: number | null; nota: number | null; categoria: string | null; motivo_sem_sinal: string | null;
  mensagens: MensagemAtribuida[] & { autor: string; texto: string }[]; contribuicoes: unknown[]; sha256: string };
export type Procedencia = { gravado_em: string; api: string; modelo: string };
export type ConjuntoLeituras = { procedencia: Procedencia; leituras: Leitura[] };
export function validarLeituras(bruto: unknown): ConjuntoLeituras | { falta: string };
```
`validarLeituras(null)` → `{ falta: "leituras ainda não gravadas — rode scripts/gravar_leituras_lp.py" }`. Recusa se faltar uma das 5, se `sem-sinal` tiver `score` não nulo, se outra tiver `score` nulo, se procedência incompleta.

Script Python: lê os 5 CSVs, `POST {FRAUS_LP_API}/analisar` com `{"csv": ..., "nome": "<id>.csv"}` e `Authorization: Bearer {FRAUS_LP_TOKEN}`, `GET /modelo` para a versão; mantém só as chaves da spec (sem `vocabulario`); aplica as mesmas recusas antes de escrever; escreve `dashboard/lib/lp-nova/leituras.json`. Função pura `montar_conjunto(respostas, modelo, agora, api, shas)` testada no pytest sem rede; a parte de rede é fina.

- [ ] Escrever CSVs com horários ISO com fuso (`-03:00`), autores `cliente`/`bot`, sem PII.
- [ ] pytest para `montar_conjunto`: descarta `vocabulario`; recusa `sem-sinal` com nota; recusa faltando leitura.
- [ ] Vitest para `validarLeituras`: null, conjunto válido (fixture inline), cada recusa.
- [ ] Commit `feat(lp-nova): leituras gravadas do motor real com procedencia`.
- [ ] **Passo humano (João):** `FRAUS_LP_API=... FRAUS_LP_TOKEN=... uv run python scripts/gravar_leituras_lp.py` e commit do JSON.

### Task 5: shaders

**Files:** Create em `dashboard/lib/lp-nova/shaders/`: `comum.wgsl`, `simular.wgsl`, `particulas.wgsl`, `orbe.wgsl`

**Contrato de bindings:**
- `comum.wgsl` (puro): `export struct Particula { pos: vec2f, vel: vec2f, familia: u32, semente: f32, tinta: f32, _p: f32 }` (32 bytes); `export struct Cena { tempo: f32, dt: f32, progresso: f32, humor: f32, aspecto: f32, total: u32, _a: f32, _b: f32, centros: array<vec4f, 7> }`; funções `hash11`, `ruido2`.
- `simular.wgsl`: `@group(0) @binding(0) var<uniform> cena: Cena; @binding(1) var<storage, read_write> particulas: array<Particula>;` `@compute @workgroup_size(256)`. Força = alvo por fase (`progresso` em [0,1] por trechos: <0.15 frase→disperso, 0.15–0.35 ruído, 0.35–0.65 atrator do centro da família, 0.65–0.8 queda no orbe (0.5,0.5) e `tinta`→1, depois respiração no orbe) + ruído curl + amortecimento; `humor` em [-1,1] (detrator→promotor, 0 = sem sinal) muda agitação.
- `particulas.wgsl`: `var<storage, read> particulas`, `vs_main` com 6 vértices por instância (quad), `fs_main` disco suave; cor = mistura âmbar→azul por `tinta`; cinza quando `humor` == 0 na fase 4.
- `orbe.wgsl`: `effect` de tela cheia (fragmento) com ruído de `@vgpu/wgsl-std/noise` desenhando o orbe com halo magenta; intensidade por `progresso`.
- [ ] `npm run wgsl` verde (com `--require-validation` na máquina com GPU).
- [ ] Commit `feat(lp-nova): shaders do campo, do orbe e da simulacao`.

### Task 6: a cena (imperativo)

**Files:** Create `dashboard/lib/lp-nova/cena.ts`; delete `fumaca.wgsl`

**Interfaces — Produces:**
```ts
export type CenaLeitura = { pronto: Promise<Regime>; definirHumor(h: number): void; definirProgresso(p: number): void; dispose(): void };
export function iniciarCena(canvas: HTMLCanvasElement, opcoes: { celular: boolean; aoMudarRegime(r: Regime, m: MotivoRegime): void }): CenaLeitura;
```
Molde: `renderer.ts` do exemplo `fluid` (init dinâmico, `surface(gpu, canvas, { dpr: [1, 1.5|2] })`, rAF com passo fixo, `document.hidden`, `dispose` idempotente). Storage `storage(gpu, total * 32, "read-write")` semeado em JS (posições da frase rasterizada num canvas 2D offscreen, família por `distribuirEnxames`). Por quadro: `simular.set({cena, particulas}).dispatch(ceil(total/256))`, `frame(gpu, f => { f.pass({target, clear}, orbe); f.pass({target}, desenhoParticulas) })`. Saúde de quadro: média móvel de 60 quadros > 24 ms por 2 s → `rebaixar("quadros")` e reconstrói com `PARTICULAS["vivo-baixo"]`.
- [ ] Verificação manual no Chrome: `/leitura` anima; `chrome://gpu` mostra WebGPU; forçar rebaixa por query `?forcar=baixo` (só em dev) troca o rótulo.
- [ ] Commit `feat(lp-nova): cena vgpu com compute, orbe e descida unica`.

### Task 7: página, seções e seletor

**Files:** `app/leitura/page.tsx`, `app/leitura/leitura.css`, `components/lp-nova/CenaLeitura.tsx`, `components/lp-nova/SeletorDeLeituras.tsx`, `components/lp-nova/secoes/{Hero,Problema,Fusor,Leituras,Analista,Limites,Fecho}.tsx`

Usar a skill `impeccable` (modo Persuade) e `dashboard/DESIGN.md`. Reaproveitar `SegmentoLED` (traço fino), `marcasDaAtribuicao`, `FAMILIAS_DO_VETOR`. `CenaLeitura` mede o progresso da rolagem (como `lib/vitrine/motor.ts`) e chama `definirProgresso`; `SeletorDeLeituras` mapeia a leitura escolhida para `humor` (detrator −1, neutro −0,2, promotor +1, sem sinal 0 — **a partir da `categoria` do servidor**, não da nota) e chama `definirHumor` via contexto. Regime `poster`: `<img>` de `public/lp-nova/`.
- [ ] Vitest: `humorDaCategoria` (puro) cobre as 4 categorias e `null`.
- [ ] Commit por seção relevante; última `feat(lp-nova): pagina /leitura com as sete secoes`.

### Task 8: pôsteres

**Files:** `dashboard/scripts/renderizar-posteres.mjs`, `public/lp-nova/{hero,fusor,fecho}.png`

`init({ adapter: "software" })` de `vgpu/node` (rodar `npx vgpu install-software-renderer` antes), mesma semente, avança N passos até cada `progresso`, salva PNG 1600×1000. Renderiza duas vezes e compara com `pixelDiff`; diferente → sai 1.
- [ ] Commit `feat(lp-nova): posteres do mesmo wgsl em renderizador de software`.

### Task 9: guardas

- [ ] `tests/test_derivacoes_dashboard.py`: incluir `components/lp-nova` e `lib/lp-nova` na varredura de "N features" e um teste que falha com `?? 0`/`|| 0` nessas pastas.
- [ ] `scripts/validar-lp-playwright.mjs`: parametrizar a rota; `/leitura` com 1 canvas, rótulo de regime presente, 390 px sem rolagem horizontal, navegar para `/entrar` sem `pageerror`.
- [ ] Commit `test(lp-nova): guardas de features, ausencia e playwright`.

### Task 10: documentação

- [ ] `dashboard/DESIGN.md`: seção "LP nova (`/leitura`, experimento vgpu)" — segunda rota com canvas, por quê, regimes.
- [ ] `docs/handoff.md`: estado e passo humano do `gravar_leituras_lp.py`.
- [ ] Commit `docs(lp-nova): design e handoff`.
