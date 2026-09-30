# Proveniência dos rasters

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

**Fontes.** Martian Mono e Bricolage Grotesque, carregadas do Google Fonts **só
na hora de gerar** a imagem. O produto em si serve as duas por `next/font`.

## Removidos

- `public/fraus-logo.png` (640×640, RGB): só o `og:image` antigo o usava. Substituído
  por `og-fraus.png`.

## Não é desta rodada

- `public/assets/hdri/` (mapa de ambiente CC0 da cena 3D da LP antiga): continua
  referenciado enquanto a LP nova não o substitui. Quando a cena 3D sair, ele e o
  `public/assets/ATTRIBUTION.md` ficam órfãos.
- `docs/assets/fraus.css` (tema do site MkDocs) ainda descreve o mundo visual
  anterior.
