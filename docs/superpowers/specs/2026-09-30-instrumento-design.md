# Instrumento — redesign visual do Fraus (30/09/2026)

Aprovado pelo dono do projeto em sessão de brainstorming, sobre mockups
estáticos (7 direções → fusão v2). Este documento é o contrato da
implementação; o DESIGN.md é reescrito **no fim**, a partir do que foi
construído (ver "Fechamento").

## Decisão

O mundo visual **"Pauta / espaço profundo"** sai como padrão de fábrica e
entra o **Instrumento**: um painel de instrumento de laboratório sobre quase
preto neutro, com **hero de orbe vivo** na vitrine. É a fusão de quatro
direções:

| Origem | O que entra |
|---|---|
| **Régua** | telemetria no topo, hairlines de 1px, mono, nav numerado `01_VISÃO GERAL █`, zero raio, a régua dito/medido como peça central |
| **Segmento** | números em LED de sete segmentos; "sem sinal" = segmentos apagados (nunca `0`); lâmpada sempre com a palavra |
| **Aurora** | hero da LP: orbe animado, headline gigante, nav de vidro, CTA com borda cônica, halo e grão |
| *(fora)* | **Tinta e tom** foi retirado da fusão por decisão do dono: nada de balão, halftone, linhas de velocidade, SFX ou sarjeta de mangá |

## O que NÃO muda (invariantes e compromissos de marca)

- `--dito` âmbar acima da linha, `--medido` azul abaixo. O LED é **azul**
  (medido); o dourado é só ação, foco e marca; o magenta vive **só no ateliê**
  (orbe/halo), nunca em dado.
- Textos de honestidade (estimativa, sem sinal, evidência fraca, nota
  metodológica, estados vazios que nomeiam o que falta) permanecem.
- CLAUDE.md, invariantes 2 e 3: o LED **apresenta** o valor que o servidor
  mandou; não calcula, não arredonda por conta própria além de formatar, e
  `null` nunca vira `0` (vira segmentos apagados + rótulo).
- A cabeça cheia/tracejada/vazada continua sendo o slot único de
  `EtiquetaCategoria`.
- Todo par de cor que carrega texto cruza AA por cálculo (`npm run contraste`);
  `npm run pisos` continua o juiz das espessuras de vidro.
- `prefers-reduced-motion` congela o orbe. O orbe e o halo moram **só na
  vitrine** (`coreografiaValeEm`), nunca atrás de tabela e gráfico.
- Sem dependência nova de runtime além de fontes via `next/font`.

## Tipografia

- **Martian Mono** — rótulos, nav, telemetria, dado, títulos de tela (`--fonte-mono`).
- **Inter** (já na casa) — prosa longa e transcrição, onde mono cansa.
- **Bricolage Grotesque** — display da vitrine (substitui Mona Sans; só
  `.display-vitrine` e `.titulo-vitrine`, a mesma trava do `tipografia.test.ts`).
- Todas por `next/font` (baixadas no build, zero rede em runtime).

## Chassi (tokens)

Neutro quase preto (`~#08080a`), superfícies em opacidade branca 2–6%,
borda `1px rgba(255,255,255,.26)` para régua e `.09` para filete interno,
raio 0 (o chanfro 45° dos painéis dá lugar ao retângulo de hairline),
vidro só no nav da LP e em popover/sheet. Planeta, estrelas, grade laser e
sol listrado do ateliê são **desligados** (opacidade 0); ficam o halo e o grão
na vitrine. O tema **chuva de neon** é mantido como segunda opção, herdando
os componentes novos pelos tokens.

## Componentes novos

- `SegmentoLED` — SVG de sete segmentos (`0-9 - , . :`), células apagadas a
  10% de opacidade, `aria-label` com o valor por extenso, `null` →
  segmentos apagados + rótulo textual obrigatório.
- `TelemetriaTopo` — a faixa de 34px no topo de cada tela.
- `Orbe` — três manchas em `mix-blend-mode: screen` girando, só na LP.
- `RéguaDaLeitura` — timeline dito/medido da LP (dados de amostra
  **rotulados como sintéticos**).

## Escopo

1. **Fundação:** tokens, fontes, `tema.ts`, ateliê calmo, `SegmentoLED`,
   `TelemetriaTopo`, `Painel`/`FaixaIndicadores`/`CartaoIndicador`/
   `NavegacaoLateral`/`CabecalhoPagina` no novo idioma.
2. **LP:** hero (orbe), leitura (régua), sistema (grade de sinais, 7 famílias +
   Fusor + sem sinal), honestidade, fecho, rodapé.
3. **Dashboard, as 7 telas** + páginas de entrar/cadastrar.
4. **Assets:** logo/monograma (variantes), `og:image`, favicon/ícone, banner
   do README.
5. **Gates:** vitest, tsc, lint, build, `contraste`, `pisos`, captura
   Playwright desktop + mobile, revisão final do Impeccable.

## Fora de escopo

Backend, modelo, API, invariantes de dados, o gesto dos cinco cliques da marca
(`RevelacaoFraus`) — a marca continua respondendo a gesto, só herda os tokens.

## Fechamento

Um redesign só termina com: revisão de acabamento, DESIGN.md/PRODUCT.md
atualizados a partir do construído (não da intenção), e todo raster novo com
proveniência registrada. "Sem revisão e sem documentação é inacabado."
