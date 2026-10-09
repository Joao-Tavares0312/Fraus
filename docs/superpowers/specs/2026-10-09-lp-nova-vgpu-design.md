# LP nova com vgpu — design

**Data:** 09/10/2026 · **Branch:** `feat/lp-nova-vgpu` · **Rota:** `/leitura`

## Objetivo

Uma landing page nova que **vende o Fraus**, chamativa e sem cara de template,
construída sobre o [vgpu](https://vgpu.sh) (biblioteca WebGPU da Vercel Labs,
`vgpu@0.5.0`). Ela nasce numa rota própria; a vitrine atual em `/` fica
intocada. Depois de pronta e medida, o dono decide se ela assume a raiz.

### O que foi decidido (pelo dono, 09/10/2026)

| Pergunta | Decisão |
|---|---|
| Onde mora | Rota nova (`/leitura`), vitrine de `/` intocada |
| Sistema visual | Instrumento (DESIGN.md) levado ao extremo: mesmas cores com dono, mesma tipografia, sem as amarras da ferramenta |
| "Agentes da Vercel" | Tooling de desenvolvimento do vgpu (MCP, skill, `examples`, `check`). Nada de LLM no produto |
| Ação principal | Ver o Fraus ler uma conversa |
| Como o anônimo vê a leitura | **Leituras reais pré-gravadas** pelo motor de produção. Nenhum endpoint público novo |

### Restrições herdadas

- Invariante 1: nenhum LLM, nenhuma chamada de rede de predição na página.
- Invariante 2: a leitura sem fala do cliente aparece como "sem sinal", nunca 0.
- Invariante 3: score, nota, categoria e marcas vêm do servidor. A página não recalcula nada.
- Invariante 7: a gravação das leituras falha alta se o motor real não responder. Sem dublê.
- DESIGN.md: âmbar = dito, azul = medido, dourado só em ação/foco/marca, magenta só no orbe e no halo. Bricolage só em `.display-vitrine`/`.titulo-vitrine`. Sem kicker acima de título. Canvas só na rota da página, nunca no layout raiz.
- Honestidade: nenhum logo, depoimento, cliente ou número sem fonte. O NPS aparece como estimativa.

## A história (sete tempos, um canvas)

Um canvas WebGPU fixo atrás da página, guiado pela rolagem (mesma arquitetura
do motor atual: `position: sticky` e progresso medido, sem pin de GSAP).

| # | Seção | Conteúdo | O que a GPU faz |
|---|---|---|---|
| 1 | Hero | Manchete *"O cliente disse obrigado. Saiu insatisfeito."*; a fala `ok, obrigado 🙂` em âmbar; o LED acende com a nota **gravada** dessa conversa. CTAs: "Ver o Fraus ler ↓" (âncora) e "Entrar" | A frase rasterizada vira as posições iniciais das partículas e se desfaz no campo |
| 2 | O problema | Pesquisa quase ninguém responde, e quem responde nem sempre diz o que sente. Só números com fonte já citada no repositório | Campo disperso, ruído âmbar |
| 3 | O fusor | Seção fixada: 7 enxames proporcionais a `FAMILIAS_DO_VETOR`, caem no orbe-fusor e saem azuis | Compute com atratores por família; orbe em WGSL |
| 4 | Leituras gravadas | Seletor de 5 leituras; transcrição com as falas que puxaram a nota; LED, categoria e emoção. Etiqueta de procedência | O campo reage à leitura: âmbar e agitado num detrator, azul e assentado num promotor, cinza e parado no sem sinal |
| 5 | Para o analista | NPS inferido com intervalo, "sem sinal" que nunca vira 0, atribuição por fala, com peças reais (`SegmentoLED`) | Campo recua e escurece |
| 6 | O que o Fraus não faz | Não pontua atendente, não roda LLM, não finge NPS declarado | Parado |
| 7 | Fecho | "Entrar" e "Tenho um convite" (/cadastrar, que já exige código) | Partículas voltam ao orbe e respiram |

**Proibido (anti-slop):** gradiente roxo genérico, grade de 3 cards com ícone,
depoimento ou logo inventado, número sem fonte, kicker, glassmorphism geral.

## Arquitetura

```
app/leitura/page.tsx            Server Component: monta as secoes
app/leitura/leitura.css         estilos `ln-*` (nao herda `vt-*`)
components/lp-nova/
  CenaLeitura.tsx               o UNICO componente de cliente com canvas
  SeletorDeLeituras.tsx         cliente: escolhe a leitura, avisa a cena
  secoes/*.tsx                  Server Components, uma por tempo
lib/lp-nova/
  enxames.ts                    PURO: particulas por familia, centros
  regime.ts                     PURO: escolhe o regime a partir dos sinais
  leituras.ts                   PURO: tipos + validacao do leituras.json
  leituras.json                 GERADO por scripts/gravar_leituras_lp.py
  cena.ts                       imperativo: vgpu, laco, rolagem
  shaders/
    comum.wgsl                  structs e constantes (modulo puro)
    simular.wgsl                compute: avanca as particulas
    particulas.wgsl             vertice/fragmento das particulas
    orbe.wgsl                   o orbe-fusor (ruido de @vgpu/wgsl-std)
scripts/renderizar-posteres.mjs pôsteres via vgpu/node, adapter "software"
public/lp-nova/*.png            pôsteres versionados
dados_lp/*.csv                  (raiz do repo) as 5 conversas sinteticas
scripts/gravar_leituras_lp.py   (raiz do repo) grava leituras.json
```

`next.config.ts` ganha a regra do loader `@vgpu/wgsl/loader-webpack` para
`*.wgsl` no Turbopack; `wgsl-env.d.ts` tipa os imports.

## Regimes

| Regime | Quando | O que aparece |
|---|---|---|
| `vivo-alto` | WebGPU presente | Campo completo, orbe completo |
| `vivo-baixo` | saúde de quadro, bateria ou tier pedem | Menos partículas, DPR menor. Desce **uma vez**, nunca sobe (padrão `adaptive-quality`) |
| `poster` | sem WebGPU, ou `prefers-reduced-motion` | PNG por momento-chave, renderizado do mesmo WGSL |
| sem JS | — | HTML com os pôsteres em `<img>` |

Um rótulo mono discreto nomeia o regime (`GPU · alto`, `pôster · sem WebGPU`).

Orçamento: celular 16k partículas (alto) / 4k (baixo), DPR ≤ 1,5; desktop até
120k. O laço pausa com a aba oculta ou o canvas fora da tela. `gpu.dispose()`
ao desmontar.

## Leituras gravadas

Cinco conversas sintéticas em CSV canônico, **com horário**:

1. `obrigado` — "ok, obrigado 🙂" depois de três tentativas frustradas (a do hero)
2. `ironia` — "nossa, que atendimento EXCELENTE 🙃"
3. `espera` — cliente educado, resposta lenta, escalação
4. `promotor` — resolvido rápido, elogio sincero
5. `sem-sinal` — o cliente nunca escreve

`scripts/gravar_leituras_lp.py` chama `POST /analisar` (rota que não grava)
na API indicada por `FRAUS_LP_API` com a credencial de `FRAUS_LP_TOKEN`
(nunca escrita em arquivo) e grava `dashboard/lib/lp-nova/leituras.json` com,
de cada análise, só `score`, `nota`, `categoria`, `motivo_sem_sinal`,
`mensagens` e `contribuicoes`. O `vocabulario` fica **de fora**: a referência
dele são contagens do banco de produção. Procedência: data, URL, versão do
modelo (`GET /modelo`), SHA-256 de cada CSV.

Recusa gravar se faltar leitura, se a `sem-sinal` voltar com nota, ou se
alguma das outras voltar sem nota.

Na tela, as marcas saem de `marcasDaAtribuicao` (`lib/derivacoes.ts`), a
mesma função da dashboard: uma fonte só para "o que puxou a nota".

## Testes

- **Vitest:** `enxames` soma o total e respeita `FAMILIAS_DO_VETOR`; `regime`
  cobre os quatro casos; `leituras` valida as 5 leituras, a `sem-sinal` com
  `score: null` e a procedência completa.
- **pytest:** `test_derivacoes_dashboard.py` varre a pasta nova atrás de
  contagem de features divergente de `NOMES_FEATURES` e de `?? 0` / `|| 0`.
- **WGSL:** `npm run wgsl` roda `vgpu check` em cada `.wgsl`.
- **Pôster:** duas renderizações com a mesma semente, `pixelDiff` exige igualdade.
- **Playwright:** `validar-lp-playwright.mjs` cobre `/leitura`: um canvas,
  regime certo, 390 px sem rolagem horizontal, CTA na dobra a 1280×720.

## Tooling de agente (só desenvolvimento)

- MCP local do vgpu no `.mcp.json` do projeto (`npx -y vgpu@0.5.0 mcp --project-from-cwd`)
- Exemplos `fluid` e `adaptive-quality` lidos via `npx vgpu examples` como referência

## Fora do escopo

Endpoint público ao vivo, trocar a raiz `/`, formulário de lead, backend novo,
mudança na vitrine atual.
