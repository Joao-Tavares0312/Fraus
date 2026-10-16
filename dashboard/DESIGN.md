---
name: Fraus — Contexto, não certeza
description: Grafite, monograma FR em camadas e tipografia quadrada. Uma chegada expressiva e uma ferramenta de leitura calma, com temas escuro e claro.
colors:
  background: "#171819"
  foreground: "#F3F4F5"
  card: "#222426"
  muted-foreground: "#B3B9C0"
  border: "#454B52"
  primary: "#D6BA72"
  dito: "#EDB466"
  medido: "#8DC8F5"
typography:
  display:
    fontFamily: "Chakra Petch, system-ui, sans-serif"
    fontWeight: 500
    lineHeight: 1.06
    letterSpacing: "-0.025em"
  prosa:
    fontFamily: "Chakra Petch, system-ui, sans-serif"
    fontWeight: 400
    lineHeight: 1.75
  dado:
    fontFamily: "Chakra Petch, system-ui, sans-serif"
    fontFeature: "tabular-nums"
rounded:
  controle: "8px"
  regiao: "12px"
spacing:
  sidebar: "224px"
  sidebar-recolhida: "64px"
  gutter-lp-desktop: "64px"
  gutter-lp-mobile: "24px"
---

# Design da interface — Contexto, não certeza

Direção aprovada no protótipo v3 e implementada em 16/10/2026. Este documento
substitui as regras visuais do **Instrumento / Chuva de neon**; não é uma camada
adicional sobre elas. A comparação histórica está em
[Antes e depois da interface](redesign-2026-10-16.md).

A verdade de produto continua em `dashboard/PRODUCT.md`. Tokens executáveis
moram em `dashboard/app/globals.css`; a LP tem seu escopo em `dashboard/app/lp.css`.
Os valores abaixo documentam o código, não constituem uma segunda configuração.

## Direção

**A marca tem matéria; a ferramenta tem clareza.** A LP combina o monograma FR,
camadas com profundidade, tipografia angular e pinceladas diagonais. A dashboard
usa a mesma família tipográfica e as mesmas vozes de cor, mas não recebe uma cena
atrás dos dados. A fenda do monograma reaparece como pequeno detalhe de identidade,
não como recorte que prejudica texto ou alvo de clique.

- Grafite, branco mineral e ouro fosco na chegada.
- Cabeçalhos e navegação em caixa normal; sem telemetria numerada decorativa.
- Números como texto legível, não polígonos de sete segmentos.
- Controles de 8px e regiões de 12px; borda simples e superfície opaca.
- Uma região dominante por tela; apoio não disputa o mesmo peso visual.

## Cor e significado

| Papel | Escuro | Claro |
|---|---|---|
| Fundo | `#171819` | `#F3F4F5` |
| Superfície / popover / sidebar | `#222426` | `#FFFFFF` |
| Texto principal | `#F3F4F5` | `#202326` |
| Texto secundário | `#B3B9C0` | `#565D65` |
| Ação e foco | `#D6BA72` | `#735713` |
| Dito | `#EDB466` | `#8A4B00` |
| Medido | `#8DC8F5` | `#165E9D` |
| Borda | `#454B52` | `#D5D9DE` |

**Âmbar é dito; azul é medido.** Fala, texto e emoji pertencem ao primeiro.
Probabilidade, nota, tempo e tendência pertencem ao segundo. Uma régua entre os
dois só aparece quando existe essa divisão real; NPS × latência são duas medidas,
não uma fala confrontada com uma medida.

**Ouro não é dado.** Pertence a marca, ação, foco e seleção. Não colore série,
barra, categoria ou valor de indicador para parecer bom resultado.

Categorias, famílias, emoções e tipos de nó conservam seus significados. No tema
claro, a luminância se adapta ao fundo, não se troca a família de matiz. Toda
categoria leva rótulo; cor não é o único canal. Os validadores medem texto e marcas
nos dois temas, inclusive as cores do grafo.

## Tipografia e ícones

**Chakra Petch local**, pesos 400, 500 e 600, com licença SIL OFL em
`dashboard/public/identidade/`. `next/font/local` serve os arquivos do próprio
produto; não há busca de fonte no Google no build ou no navegador.

- Texto, títulos, controles e valores usam a família quadrada.
- Valores comparáveis usam algarismos tabulares. Código, `pre` e `kbd` mantêm
  pilha monoespaçada de sistema.
- Piso de texto: 11px. Não diminuir procedência ou ressalva para fazê-la caber.
- Títulos grandes fecham o tracking; não aplicar caixa alta e tracking de
  telemetria a toda a interface.
- Lucide com ícones contextuais. Ação usa o desenho do verbo; seleção é
  identificada pelo estado, não por um ícone arbitrário.
- Ícone decorativo leva `aria-hidden`; texto ou nome acessível diz a ação.

## LP

### Estrutura e conteúdo

1. **Abertura:** “O atendimento termina. A análise começa.” e ação para conhecer
   o método. O FR é arte da marca, não um gráfico de resultados.
2. **Contexto:** “Ok, obrigado.” vem identificado como **exemplo de linguagem**.
   Pedido, resposta e desfecho explicam o que conferir; cortesia isolada não
   comprova satisfação ou insatisfação.
3. **Sinais:** detalhes nativos separam leitura textual da mensagem,
   contribuições dos sinais e horários da conversa. Probabilidade textual não
   vira causa isolada da nota fundida.
4. **Uso:** panorama → recorte → conversa, com destino real para `/dashboard`.
5. **Limites:** estimativa, não pesquisa; não avalia atendentes; tempo treinado
   com dados sintéticos; sem sinal não é zero.
6. **Fecho:** entrar e criar conta, sem links ou rótulos de prancha de estudo.

As leituras gravadas permanecem em expansão nativa. `carregarLeituras` valida o
snapshot; seletor, transcrição, data, API e hash parcial acompanham resultados
válidos. O hash das importâncias **não** identifica todos os checkpoints nem o
pipeline. Sem snapshot válido, a LP nomeia a ausência; não publica resultado do
dublê nem apresenta escolhas fictícias. Nenhuma análise é executada ao abrir a LP.

### Fundo contínuo

Uma única camada SVG de pincel cobre **a raiz inteira da LP**, do cabeçalho ao
fecho. A raiz é posicionada e isolada; o pseudo-elemento usa `inset: 0`. Sua altura
deve acompanhar a página, inclusive quando detalhes alteram o conteúdo. Não
voltar a prender o fundo ao palco do FR ou a um viewport de altura fixa.

O SVG é estático, local e sem filtros, scripts ou recursos externos. Não recebe
interação. Widgets têm superfície opaca; a textura não atravessa o texto deles.
A dashboard não herda o pincel.

### FR e orçamento de renderização

A geometria deriva do **SVG oficial**, incluindo a fenda diagonal. F claro e R
champanhe, cinco camadas extrudadas. Essas cinco camadas **não representam**
famílias, features ou contribuições do modelo.

- Desktop a partir de 900px, sem movimento reduzido: **um canvas WebGL nativo**
  quando o contexto é elegível, importado sob demanda. O HTML inicial contém
  a própria arte pré-renderizada; centenas de faces CSS não permanecem no DOM.
- Produção pede `failIfMajorPerformanceCaveat` e recusa backends CPU conhecidos,
  como SwiftShader/llvmpipe. Nesse caso as poses continuam em WebP, sem replay,
  triangulação ou upload de buffers. Identificação ocultada não prova hardware;
  a decisão restante depende do caveat do navegador.
- A seção com maior porção visível escolhe a pose. Nova direção parte da
  interpolação atual e substitui o alvo; não existe fila nem sequestro da rolagem.
- Com GL ativo, transições de 650ms; replay reexecuta a entrada sem mover o documento.
- Mobile: imagens WebP transparentes das mesmas poses, sem iniciar WebGL.
  `picture` seleciona a variante de 800×640; desktop usa 1280×1024. As imagens
  inferiores usam carregamento preguiçoso, sem baixar as duas variantes.
- Sem JS ou com `prefers-reduced-motion`: arte estática e conteúdo completo,
  sem importar o renderizador nem oferecer replay.
- Um buffer estático e um draw por quadro, culling de faces traseiras e placas
  próximas primeiro. rAF existe apenas durante transições; resize redesenha sob
  demanda. Limites: DPR 1,5 e 1,6 megapixel.
- O raster só sai após o primeiro draw válido. WebGL indisponível ou contexto
  perdido mantém a marca estática e remove replay; restauração recria recursos.
  Desmontar libera buffers, programa, shaders, observadores e rAF.
- Não há device WebGPU, partículas ou laço permanente na LP. O WebGL serve
  somente à arte da marca, não à inferência. Motion fica no layout da dashboard.
- Links para conta e ferramenta não antecipam o download dessas rotas na LP.

`npm run arte:lp`, com o produto local aberto, gera os WebP da própria escultura.
`LP_URL` seleciona a prévia; o exportador usa Chromium e FFmpeg. Não recriar a
geometria num segundo gerador. Depois de gerar novos arquivos públicos, reiniciar
a prévia de produção antes de conferir as imagens.
Em ambiente de captura sem aceleração, `LP_GL_SOFTWARE=1 npm run arte:lp`
autoriza GL em software **somente no Playwright de exportação**. Não falsifica o
driver nem habilita um modo oculto na LP. Isso produz arte real, não evidência
de desempenho de hardware.


## Dashboard

Sidebar de **224px**, recolhida em um rail de **64px**, com ícones e nomes em
caixa normal. Três grupos organizam tarefas: **Acompanhar** (visão geral e
atendimentos), **Investigar** (analisar, grafo e operação) e **Configurar**
(integrações, modelo e configurações, apenas para `dev`). Destinos, ícones,
grupos e visibilidade têm uma fonte única em `lib/navegacao.ts`.

- Página atual usa `aria-current="page"`; sua seção ancestral usa `"location"`.
  Links recolhidos mantêm nome acessível e tooltip por foco ou ponteiro.
- Somente `de` e `ate` acompanham a troca de tarefa. Busca, paginação e outros
  parâmetros locais não vazam para a próxima seção.
- Recolhimento é restaurado no servidor pelo cookie de preferência. Ctrl/Meta+B
  alterna a navegação sem interceptar input, textarea, select ou contenteditable.
- Ação de recolher/expandir fica junto à marca no desktop. No celular, o
  cabeçalho abre a gaveta; fechamento explícito e Escape devolvem o foco.
  Navegação comum fecha a gaveta; clique modificado para nova aba não a fecha.
- Marca interativa e link para a visão geral são controles separados. Tema,
  documentação, sessão e saída permanecem disponíveis; o rodapé compacto não
  trunca o aviso real de motor sintético.

Permissões continuam sendo contratos do servidor, não consequência de mostrar
ou esconder links. Não converter ausência de papel em permissão administrativa.

A visão geral abre com título e filtro, faixa compacta de quatro indicadores e
NPS × latência como região dominante. A faixa usa quatro colunas em telas largas
e duas em larguras menores. Informação de amostra e incerteza continua próxima
do NPS, sem transformar ressalva em rodapé invisível.

`Painel` preserva dominante/apoio, erros locais, vazios e aparato metodológico.
Superfície opaca, borda simples; nenhum ateliê, brilho especular, vidro ou fundo
animado interfere nos gráficos. `EstadoVazio` nomeia o que falta e a etapa ou o
endpoint que pode resolver.

### Números, ausência e proveniência

`ValorNumerico` recebe uma string já formatada, rótulo e ausência explícita.
Não calcula score, nota ou categoria. `NotaInferida` apresenta a nota recebida.
Zero observado continua zero; `null` continua ausência.

- NPS e CSAT carregam **estimativa**. Contenção e latência são observadas.
- Amostra insuficiente não ganha ponto de NPS; o intervalo amostral não mede o
  erro do modelo.
- `sem sinal`, `sem estimativa` e `sem dados` não são sinônimos; a região nomeia
  a condição correta.
- Categoria medida: cabeça cheia; evidência fraca: tracejada com motivo;
  ausência: cabeça vazada cinza e texto. Cinza fica fora da escala.
- Erro de uma consulta não apaga indicadores que responderam.
- O segredo da marca nunca modifica indicadores, gráficos ou transcrições.

### Encaixe secreto

Cinco cliques consecutivos na marca, com até dois segundos entre eles, abrem
um quebra-cabeça do FR. Três fragmentos da arte pré-renderizada deslizam em
trilhos nativos; o centro de cada trilho recompõe o monograma. A conclusão
é uma brincadeira visual, não score, leitura psicológica ou resultado do modelo.

O componente carrega apenas ao descobrir o segredo. Não usa canvas, áudio,
relógio de jogo, API ou persistência; não fecha sozinho. Embaralhar oferece
outro arranjo. `prefers-reduced-motion` elimina transições sem retirar o jogo.
O diálogo contém foco, fecha por Escape/botão/clique fora e devolve foco à
marca. No celular, fechar o segredo não fecha a gaveta que o abriu.

A antiga revelação vaporwave, a pontuação do ritmo e o contexto que falsificava
indicadores foram removidos, não mantidos como um segundo modo.

### Temas

**Escuro** é o padrão; **Claro** é alternativa da dashboard. Preferência fica no
navegador e acompanha abas e navegação. Valores legados Instrumento/Chuva não são
aliases: retornam ao padrão. LP e acesso ficam escuros, sem apagar a preferência
da ferramenta; voltar à dashboard restaura a escolha.

O script inicial evita flash; `TemaDaRota` trata transições do App Router. O
canvas do grafo invalida a paleta ao trocar tema sem recriar dados ou física.

## Acesso, acessibilidade e estados

O acesso mantém o FR pré-renderizado de luz de corte: uma passagem curta, sem
loop, interrompida ao operar o formulário. Não carrega motor 3D no navegador.
Convite, código administrativo, erros, disponibilidade de login e navegação são
contratos do servidor, não efeitos visuais.

- Teclado: pular conteúdo, foco visível, abas com setas/Home/End e `details`
  nativo com Enter. Controles da LP têm alvo mínimo de 44px.
- Carregamento: esqueleto com forma do resultado e estado ocupado, nunca zero ou
  “sem sinal” antes da resposta.
- Erro: causa visível e ação real, sem ocultar os vizinhos que funcionam.
- Movimento reduzido remove deslocamento; não apenas o torna mais lento.
- Não pontuar atendentes, não alegar leitura de pensamentos e não apresentar
  números de demonstração como resultados de clientes reais.

## Verificação e manutenção

`npm test`, `npm run lint`, `npm run build`, `npm run contraste` e `npm run pisos`
cobrem contratos diferentes. Nenhum substitui olhar e operar o produto.

`npm run test:lp` exercita desktop/mobile, teclado, snapshots/ausência, fundo com
altura integral, pixels do FR, retarget/retorno, replay sem scroll, reduce
inicial/dinâmico, resize, sem JS, indisponibilidade/perda/restauração de WebGL,
ausência de draws ociosos, acesso e redirect de `/leitura`. `LP_EVIDENCIAS`
guarda capturas e resultados fora do código.
O relatório distingue GL exercitado de cenários não elegíveis. Para conferir
geometria, retarget e ciclo de contexto sem uma GPU disponível,
`LP_GL_SOFTWARE=1 npm run test:lp` autoriza renderização real em software apenas
no navegador de QA; não é benchmark do caminho padrão.


`node scripts/validar-navegacao-playwright.mjs` opera rotas reais, período,
recolhimento/reload, atalhos durante edição, tooltip por foco, tema, marca e
gaveta móvel. `DASHBOARD_URL` aponta para o produto já iniciado; exige sessão
válida ou o modo local aberto. Também conferir dashboard vazia, atendimento sem
sinal, temas, grafo e navegação LP ↔ ferramenta.

`node scripts/validar-segredo-playwright.mjs` resolve o jogo por teclado,
confere mudança dos pixels, reinício, embaralhar, foco e modais aninhados.
Compara os quatro indicadores antes/durante/depois em desktop e celular,
incluindo Claro e reduce. `SEGREDO_EVIDENCIAS` guarda as capturas opcionais.


A documentação MkDocs mantém sua aparência própria nesta entrega; não presumir
que o CSS do site foi redesenhado junto com o produto.
