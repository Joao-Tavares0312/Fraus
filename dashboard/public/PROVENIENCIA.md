# Proveniência dos ativos visuais

## Direção FR — 16/10/2026

| Ativo | Origem e uso |
|---|---|
| `identidade/fundo-pincel.svg` | Composição vetorial autoral de traços diagonais. Uma camada cobre toda a LP; sem scripts, animação, filtros ou recursos externos. |
| `identidade/chakra-petch-{400,500,600}.woff2` | Chakra Petch, Google Fonts, convertida para WOFF2 com FontTools, preservando os glifos recebidos, incluindo português. SIL OFL em `identidade/OFL-Chakra-Petch.txt`. Servida localmente por `next/font/local`. |
| `identidade/fr-lp-{0,1,2,3}.webp` | Capturas transparentes da própria escultura WebGL, regeneradas em 16/10: Chromium, redução para 1280×1024 e WebP qualidade 82 via FFmpeg. Desktop sem JS, com reduce, sem contexto elegível ou em backend de software; também antes do primeiro draw interativo. |
| `identidade/fr-lp-{0,1,2,3}-compacto.webp` | As mesmas poses em 800×640; selecionadas por `picture` abaixo de 900px, sem baixar a variante desktop. |
| `lib/lp-nova/escultura.ts` | Contornos do F e R derivados de `fraus-logo.svg`, com a fenda diagonal subtraída, ilhas separadas e arestas extrudadas. Arte de marca, não representação de features ou famílias. |
| `lib/lp-nova/renderizador-fr.ts` | Renderizador WebGL nativo dos mesmos contornos, poses e materiais. Um buffer estático; não contém modelo de IA nem executa inferência. |

Fontes originais: [Chakra Petch](https://fonts.google.com/specimen/Chakra+Petch)
e [licença/família no repositório Google Fonts](https://github.com/google/fonts/tree/main/ofl/chakrapetch).
Os arquivos foram obtidos das variantes 400, 500 e 600 da família; o produto
não consulta esses endereços ao abrir a página.

Para regenerar os WebP, com a dashboard em execução:

```bash
npm run arte:lp
# LP_URL seleciona outra prévia local. Argumentos 0 1 2 3 selecionam poses.
# Só na captura offline sem aceleração; não é configuração do produto:
LP_GL_SOFTWARE=1 npm run arte:lp
```

O exportador usa os componentes, poses e materiais do produto; não mantém uma
segunda geometria. A caixa de captura tem margem para a pose aberta, sem cortar
a ponta do R. Reiniciar uma prévia de produção após criar arquivos públicos.
A captura em SwiftShader requer autorização explícita no exportador. O driver
continua sendo software; os pixels vêm do mesmo GL real, sem forjar um perfil
de hardware ou medir produção nessa condição.

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
