# Proveniência dos ativos visuais

## LP coreografada — 19/10/2026

| Ativo | Origem e uso |
|---|---|
| `identidade/unbounded-variavel.woff2` | Unbounded, Google Fonts, fonte variável (500–700), subconjunto latin com os acentos do português. SIL OFL em `identidade/OFL-Unbounded.txt`. Títulos da LP, por `next/font/local` só em `app/page.tsx`. |
| `identidade/space-grotesk-variavel.woff2` | Space Grotesk, Google Fonts, fonte variável (400–500), subconjunto latin. SIL OFL em `identidade/OFL-Space-Grotesk.txt`. Corpo de texto da LP. |
| `lib/lp-nova/palco-fr.ts` | Palco WebGL nativo do mockup GSAP + 3D: os mesmos contornos e o mesmo material da escultura, com câmera de perspectiva e poeira de 700 pontos (PRNG fixo). Não contém modelo de IA nem executa inferência. |

Os arquivos foram baixados uma vez de `fonts.gstatic.com`; o produto não
consulta esses endereços no build nem ao abrir a página. Licenças obtidas do
repositório `google/fonts` (`ofl/unbounded`, `ofl/spacegrotesk`).

## Direção FR — 16/10/2026

| Ativo | Origem e uso |
|---|---|
| `identidade/chakra-petch-{400,500,600}.woff2` | Chakra Petch, Google Fonts, convertida para WOFF2 com FontTools, preservando os glifos recebidos, incluindo português. SIL OFL em `identidade/OFL-Chakra-Petch.txt`. Servida localmente por `next/font/local`. |
| `identidade/fr-lp-0.webp` | Captura transparente da própria escultura WebGL (16/10): Chromium, 1280×1024, WebP qualidade 82 via FFmpeg. Desde 19/10 é o fallback do palco: sem JS, sem contexto elegível, backend de software ou contexto perdido. As poses 1–3 saíram com a narrativa sticky. |
| `identidade/fr-lp-0-compacto.webp` | A mesma pose em 800×640, escolhida por `picture` abaixo de 900px. |
| `lib/lp-nova/escultura.ts` | Contornos do F e R derivados de `fraus-logo.svg`, com a fenda diagonal subtraída, ilhas separadas e arestas extrudadas. Arte de marca, não representação de features ou famílias. **O modelo não muda**; câmera e poses, sim. |

Fontes originais: [Chakra Petch](https://fonts.google.com/specimen/Chakra+Petch)
e [licença/família no repositório Google Fonts](https://github.com/google/fonts/tree/main/ofl/chakrapetch).
Os arquivos foram obtidos das variantes 400, 500 e 600 da família; o produto
não consulta esses endereços ao abrir a página.

O exportador `npm run arte:lp` saiu junto com a narrativa sticky, porque
dependia do DOM dela. O WebP continua fiel: o modelo e o material são os
mesmos. Para gerar uma pose nova, um exportador precisa ler o palco atual, sem
criar uma segunda geometria.

Os ícones de interface vêm de `lucide-react`, já dependência do projeto.

## Ícones, banner e cartão de compartilhamento — Instrumento, 30/09/2026

Todo raster novo do redesign Instrumento (30/09/2026) sai de **um script**,
`docs/assets/fonte/gerar-assets-instrumento.mjs`. Nenhum foi editado à mão, e
nenhum vem de gerador de imagem por IA: são páginas HTML/CSS estáticas
renderizadas pelo Chromium via Playwright.

```
node docs/assets/fonte/gerar-assets-instrumento.mjs   # da raiz do repositório
```

O monograma **não foi redesenhado**: os três caminhos (F, R e a fenda) são os
literais de `public/fraus-logo.svg`. Muda só o recorte e o fundo. As páginas
temporárias ficam no diretório temporário do sistema e não são versionadas.

| Arquivo | O que é | Como foi gerado |
|---|---|---|
| `app/icon.svg` | ícone vetorial, 520×520, fundo `#070707` (o preto da marca) | o script escreve o SVG; é o que o Next serve em `<link rel="icon">` |
| `app/favicon.ico` | 16, 32 e 48 px | cada tamanho renderizado **do SVG** (não reduzido de um maior), PNG RGBA embalado num ICO montado pelo script |
| `app/apple-icon.png` | 180×180 | renderização do mesmo SVG |
| `public/icon-32.png`, `public/icon-512.png` | 32 e 512 px | idem |
| `public/og-fraus.png` | 1200×630, cartão de link (`og:image` e `twitter:image`) | página HTML: telemetria, orbe estático (três manchas em `mix-blend-mode: screen`), monograma, headline, chip "estimativa · sem LLM em runtime" |
| `docs/assets/banner-instrumento.png` | 1280×320, topo do README | mesma página-base, em outro recorte |

**RGBA.** O Chromium devolve PNG RGB (tipo 2) quando a página é opaca. O Next
recusa RGB em favicon e ícone (`The PNG is not in RGBA format!`, ver
`docs/design.md`), então o script reescreve os ícones como tipo 6 (alfa 255).
`og-fraus.png` e o banner ficam RGB; não passam pelo processador de ícones.

**Texto e números.** Só fatos que o projeto afirma em outro lugar (7 famílias,
39 features, 0 LLM, NPS estimado). Nenhuma métrica de desempenho, nenhum cliente,
nenhuma captura de dado real.

**Fontes destes rasters.** Martian Mono e Bricolage Grotesque, carregadas do Google
Fonts só ao gerar a imagem. A interface atual usa Chakra Petch local, não essas famílias.

## Removidos

- `public/fraus-logo.png` (640×640, RGB): só o `og:image` antigo o usava. Substituído
  por `og-fraus.png`.
- `public/assets/hdri/studio_small_06_1k.hdr` e `public/assets/ATTRIBUTION.md`: o
  mapa de ambiente CC0 da cena 3D da LP antiga. A cena saiu em `61db71d` (30/09) e
  nenhum código os citava mais; removidos na limpeza de 14/10/2026.

## Não é desta rodada

- `docs/assets/fraus.css` (tema do site MkDocs) ainda descreve o mundo visual
  anterior.
