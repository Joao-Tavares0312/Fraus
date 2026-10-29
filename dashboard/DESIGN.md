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
chanfro:
  botao-lp: "12px"
  card-lp: "18px"
  botao: "9px"
  botao-pequeno: "7px"
  controle: "7px"
  card: "12px"
  etiqueta: "6px"
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
moram em `dashboard/app/globals.css`; a forma das camadas (canto, placas, fio,
fenda e pincelada) mora em `dashboard/app/camadas.css`; a LP tem seu escopo em
`dashboard/app/lp.css`.
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
- Controles e regiões com **canto cortado** na diagonal da fenda, superfície
  opaca e borda simples que continua nas duas diagonais. Na LP a peça entra
  inteira (placas que se abrem); na dashboard, contida (placas só no botão
  primário).
- Uma região dominante por tela; apoio não disputa o mesmo peso visual.

### Camadas do FR

Botões, cards e títulos repetem o monograma: placas empilhadas como a extrusão
do FR e o canto cortado da fenda. **Uma fonte só:** o polígono do canto e as
cores das placas existem apenas em `app/camadas.css`, em `@layer camadas`
(acima dos utilitários, para `rounded-*`, `bg-*` e `outline-none` não apagarem
o canto nem o foco). A API pública são classes e variáveis; nenhuma classe
define as variáveis PÚBLICAS (`--chanfro`, `--placa-*`, `--cor-*`), só lê com
valor de reserva; as internas (`--camada-*`, `--traco-cor`) são definidas pelas
classes.

| Classe | O que desenha |
|---|---|
| `.chanfro` | canto cortado no topo-esquerdo e no inferior-direito, com o traço de 1px da borda nas diagonais (`--cor-borda-chanfro`; elemento sem borda usa `transparent`) |
| `.placas` | face no `::before`, placa 2 no `::after`, placa 3 no `drop-shadow`; no hover a face sobe e as placas abrem |
| `.placas-so-hover` | as mesmas placas, planas em repouso |
| `.fio` | 2px de ouro no topo à direita, 40% da largura |
| `.fio-hover` | sublinhado de 2px que cresce no hover e no foco |
| `.fenda` | risco diagonal pequeno no canto superior direito |
| `.pincel` | pincelada inclinada (`skewX(-24deg)`) atrás da palavra-chave |
| `.chanfro-marco` | o canto no `::before` de um marcador (o ponto do `.step`) |

- Fio, fenda e o traço do canto **compõem** por variáveis numa única
  `background-image`: `superficie fio`, `stat placas fio fenda` funcionam
  juntos. Por isso `.superficie` usa `background-color`, nunca o atalho
  `background`.
- **Placas são pseudo-elementos, nunca filhos:** `data-embaralhar` reescreve o
  `textContent` do botão da LP. A camada anula `border`, `ring`, `shadow`, `bg` e
  `rounded` do próprio elemento, que deve tirar essas classes; a borda da face
  vem de `--placa-borda`. A transição das placas não inclui `opacity`: o GSAP
  lê o valor final de `.rv` e o botão nasceria invisível.
- **Foco visível por dentro.** O `clip-path` corta anel externo: em `.chanfro`
  e `.superficie` o anel é `outline` com deslocamento −2px; em `.placas`, sem
  clip-path, o anel fica a 6px, longe da face que sobe. CSS sem camada com
  `outline-offset` positivo vence essa regra; a LP repete o −2px em
  `.lp .chanfro:focus-visible`.
- `.superficie` tem `clip-path`: conteúdo absoluto que não seja portal e
  transborde a região é cortado.
- `filter` em `.placas` cria bloco de contenção para `position: fixed`:
  sobreposição dentro de algo com placas vai por portal.
- **Tokens das placas:** `--placa-2/3` e `--placa-card-2/3` seguem o tema
  (`#a8904f`, `#6f5f36`, `#34302a`, `#2a2621` no escuro; no claro, derivados
  dos tokens do claro por `color-mix`, sem hexadecimal do escuro). A LP é
  sempre escura e lê `--placa-escuro-*`; o fecho dourado lê `--placa-fecho-*`
  (face grafite `#171819`, placas `#3a3326` e `#7a6532`, texto ouro).
- Ouro continua sendo ação e marca: o fio, a fenda e a pincelada são
  identidade, não valor.

## Cor e significado

| Papel | Escuro | Claro |
|---|---|---|
| Fundo | `#171819` | `#F3F4F5` |
| Superfície / popover / sidebar | `#222426` | `#FFFFFF` |
| Texto principal | `#F3F4F5` | `#202326` |
| Texto secundário | `#B3B9C0` | `#565D65` |
| Ação e foco | `#D6BA72` | `#735713` |
| Dito | `#EDB466` | `#8A4B00` |
| Medido — marcas gráficas | `#8DC8F5` | `#165E9D` |
| Texto de medidas | `#F3F4F5` | `#202326` |
| Borda | `#454B52` | `#D5D9DE` |

**Âmbar é dito; azul identifica as marcas gráficas do medido.** Fala, texto e
emoji pertencem ao primeiro; probabilidade, nota, tempo e tendência, ao segundo.
Por decisão de 22/10/2026, os textos antes azuis usam branco mineral no escuro e
grafite no claro (`--medido-texto` acompanha `--foreground`). Na LP, sempre escura,
o token acompanha `--texto`. Números, títulos e legendas ficam neutros; séries,
bordas e marcadores continuam com suas cores semânticas.
Uma régua entre dito e medido só aparece quando existe essa divisão real;
NPS × latência são duas medidas, não uma fala confrontada com uma medida.

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

A LP segue o mockup GSAP + 3D aprovado em 19/10/2026, que **substituiu** as
regras de movimento anteriores (palco sticky, troca de pose em 650ms, sem
partículas nem laço). O conteúdo continua SSR e completo sem JS; a coreografia
inteira mora em `components/lp-nova/Coreografia.tsx`, o único componente cliente.

### Estrutura e conteúdo

1. **Abertura:** “O atendimento termina. A análise começa.”, ação para conhecer
   o método e quatro fatos do motor: 7 famílias, 39 features, 3 BERTimbau,
   0 LLM. Vêm de `FATOS_LP`; `tests/test_lp_fatos.py` falha se o fusor divergir.
   O servidor já entrega o número final; o contador só anima por cima.
2. **Letreiro** “Contexto · não certeza · Dito · Medido”, decorativo (`aria-hidden`).
3. **Contexto:** “Ok, obrigado.” identificado como **exemplo de linguagem**;
   pedido, resposta e desfecho dizem o que conferir.
4. **Sinais:** leitura da mensagem, contribuição dos sinais e tempos; as
   leituras gravadas seguem em expansão nativa logo abaixo.
5. **Faixa:** TEXTO, EMOJIS e TEMPO, fixada e rolada na horizontal.
6. **Uso:** panorama → recorte → conversa, com destino real para `/dashboard`.
7. **Limites:** estimativa, não pesquisa; não avalia atendentes; tempo treinado
   com dados sintéticos; sem sinal não é zero.
8. **Fecho:** o mundo vira ouro; entrar e criar conta.

O rodapé diz “toda **nota** é inferida”: os contadores do topo são fatos do
código, não estimativas. `carregarLeituras` valida o snapshot; sem snapshot
válido a LP nomeia a ausência e não publica resultado do dublê. Nenhuma análise
é executada ao abrir a LP.

### Céu

O fundo da LP é o céu da arte do João, em movimento: `<Ceu />` (`.lp-ceu`),
fixo atrás de tudo (`z-index: 0`, abaixo do palco WebGL) e sem ponteiro. São
140 pontos dourados (`#e9cf8e`, 8% grandes; 60% piscam em ciclos de 2,5 a 7 s)
e 26 riscos finos a −22° da vertical, que descem em 14 a 30 s.

- **Só CSS:** sem canvas e sem script por quadro; anima apenas `opacity` e
  `transform`/`translate`. As posições saem de um PRNG de semente fixa
  (`lib/lp-nova/ceu.ts`), renderizadas no servidor: sem `Math.random()` no
  render, a hidratação bate.
- **Fecho:** com `.lp.inv` o ouro entra por opacidade do `::before` em 0,6 s
  (gradiente não interpola), os pontos somem e os riscos escurecem, como na
  arte dourada. Nenhum código da coreografia muda.
- **O fecho dourado só existe com JS e movimento ligados** (`.inv` vem do
  ScrollTrigger); em reduce ou sem JS o fecho continua escuro.
- **Reduce:** o céu fica parado, com os riscos visíveis e a mesma cara da arte.
- **Sem JS:** o céu é HTML do servidor com animação em CSS; chega completo.

- **Camadas de 29/10/2026** (linguagem do filme “A fenda”): `.lp-nevoa` (placa
  de névoa gerada no Higgsfield, `public/lp-nova/nevoa.webp`, 3 KB, a 32%),
  `.lp-grade` (grade a −32,8°, o ângulo da fenda) e `.lp-feixe` (feixe dourado
  ao longo da fenda). Névoa e feixe **respiram sozinhos** por decisão do João;
  os três planos de pontos (`.lp-plano`, `--z` 0–2) fazem parallax pela linha
  do tempo da rolagem em CSS (`animation-timeline: scroll(root)`), sem script.
  Sem suporte, ficam parados. No fecho dourado as camadas somem.
- **Custo medido** (headless, CPU 4×): o feixe com `mix-blend-mode` custava
  ~60 ms por quadro, então ele é alfa puro; a grade é um segundo fundo da
  própria `.lp-nevoa`, não uma camada. No celular (< 900 px) o feixe some e o
  parallax para. Nada de blend nem de camada de tela inteira nova sem medir.

É a **única animação contínua permitida** fora do palco, e só porque é CSS e
fica atrás dele. A dashboard não recebe o céu.

### Widgets da LP

Botão primário `btn placas` com três placas (face ouro, `#a8904f` e
`#6f5f36`), canto de 12px; no hover a face sobe 3px e a placa de trás desce.
Botão secundário `btn o chanfro fio-hover`: contorno e fio que cresce embaixo.
`.card` e `.stat` têm face com canto de 18px, duas placas que se abrem no hover
e fio no topo; a `.stat` leva a fenda no canto e o rótulo reserva espaço para
ela. `.ck li`, abas e o resumo das leituras têm canto e contorno, sem placas;
`.tag` tem canto de 6px; o `.step` muda só o marcador, um quadrado cortado.
A palavra “análise” do título da abertura leva a pincelada, dentro de uma
máscara com folga para não sair cortada. No fecho as placas viram grafite com
texto ouro. Os espaços de `.stats`, `.grid` e `.card` são de 16px, para as
placas abertas não encostarem na vizinha.

### Tipografia da LP

Unbounded (títulos, letreiro, preloader) e Space Grotesk (corpo), variáveis,
locais em `public/identidade/` com SIL OFL, carregadas por `next/font/local`
**só em `app/page.tsx`**: a dashboard não baixa nenhuma delas. Rótulos, botões
e números seguem em Chakra Petch.

### Coreografia

- **Preloader** dourado com contador, **uma vez por sessão**: o script do
  `<head>` (`SCRIPT_PRELOADER`) marca `data-lp-pre="visto"` antes do paint;
  quem volta de `/entrar` não espera de novo.
- **Lenis** no ticker do GSAP, âncoras pelo próprio Lenis. Títulos sobem palavra
  a palavra (quebradas no SSR, nunca `innerHTML`), revelações em lote, frase
  letra a letra com o texto inteiro para leitor de tela, régua e linha dos
  passos por scrub, botões magnéticos, cursor próprio só com `hover: hover`,
  texto embaralhado com nome acessível fixo, índice lateral `01 / 07`.
- O letreiro só anima dentro da viewport; ao voltar de baixo ele retoma em
  reverso sem parar no início da timeline. Cursor e magnetismo só registram
  ponteiro com `hover: hover` e `pointer: fine`.
- **Desmontagem**: cada listener, tween, ticker e o Lenis são revertidos; o QA
  confere que nada sobra em `/entrar`.

### FR e palco

O **modelo é intocável**: contornos de `escultura.ts` (do SVG oficial, com a
fenda) e o material do shader. Câmera, poses e coreografia são livres. As cinco
placas **não representam** famílias, features ou contribuições do modelo.

- Um canvas WebGL fixo de tela cheia (`lib/lp-nova/palco-fr.ts`): câmera de
  35°, dois programas (FR e 700 partículas em disco, PRNG fixo), dois draws por
  quadro, DPR até 1,5 e no máximo 2,2 megapixels.
- Geometria e shaders carregam no primeiro respiro do navegador, não no bundle
  inicial da coreografia. O WebP SSR permanece disponível enquanto o palco
  prepara; formato, material, partículas e poses não foram simplificados.
- Cada quadro reutiliza o mesmo estado numérico. Perder o contexto destrói a
  instância anterior antes de restaurar; listeners não se acumulam a cada ciclo.
- Cada pose de `POSES_POR_SECAO` chega com a própria seção (`fromTo` com
  scrub). Uma timeline única sobre o `<main>` desalinhava por causa da faixa.
- Pulso entre placas, giro e letreiro leem a velocidade do Lenis **suavizada**
  a cada quadro. A velocidade crua chega em degraus pela roda do mouse e fazia
  o FR pular. Passos usam `deltaRatio`, então 120 Hz não gira em dobro.
- No fecho o FR vira relevo do próprio ouro, um tom abaixo. Grafite apagava o
  título escuro por cima.
- Celular: o mesmo palco, centralizado, escala 0,55 e opacidade 0,38.
- Reduce: um quadro parado, opacidade 0,3, sem preloader, pin, Lenis ou letreiro.
- Backend de software (SwiftShader, llvmpipe...), contexto recusado ou perdido:
  `fr-lp-0.webp` (ou a variante compacta) no lugar. O WebP é captura do mesmo
  modelo; o exportador antigo saiu com a narrativa sticky.

## Dashboard

Sidebar de **224px**, recolhida em um rail de **64px**, com ícones e nomes em
caixa normal. Dois grupos organizam o dia a dia: **Acompanhar** (visão geral e
atendimentos) e **Investigar** (analisar, grafo e modelo, este só para `dev`).
Gestão e configuração moram no **menu da conta** (`MenuDoUsuario`, `Menu` do
Base UI), aberto pelo nome no rodapé: Operação, Integrações e Configurações
(as duas últimas só `dev`), documentação, tema claro/escuro e sair. Destinos,
ícones, grupos e visibilidade têm uma fonte única em `lib/navegacao.ts`
(`gruposDoPapel` para a lateral, `telasDaConta` para o menu).

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

A visão geral abre com título e filtro, faixa de quatro indicadores e
NPS × latência como região dominante. A faixa são **quatro cards separados**
(`.superficie`, canto de 12px, espaço entre eles), em quatro colunas em telas
largas e duas em larguras menores; o NPS leva o fio dourado. O resumo do
atendimento e o esqueleto de carregamento usam o mesmo card, sem fio: uma
linguagem só de indicador. Informação de amostra e incerteza continua próxima
do NPS, sem transformar ressalva em rodapé invisível.

A dashboard recebe as camadas **contidas**:

- **Canto cortado** em botões (9px; `sm`/`xs` 7px), campos, `select`,
  `textarea`, gatilhos de abas (7px), badges (6px) e regiões com caixa própria
  (`.superficie` e `alert`, 12px). `.superficie` já é cortada; o tooltip usa
  `superficie-flutuante`, e a gaveta móvel da sidebar não leva `.superficie`.
- **Placas só onde se clica:** o botão `default` tem as placas da LP, menores.
  `outline` e `secondary` têm canto, contorno e fio no hover; `destructive`, só
  canto (ouro é ação, não alerta). `ghost`, `link` e botões de ícone não têm
  canto nem placa: num quadrado de 24 a 36px o corte vira ruído. Card que não é
  clicável não ganha placa, porque a placa avisa “isso é clicável”.
- **Fio dourado** no NPS da faixa e no painel `dominante` (`superficie fio`).
  O `apoio` continua só com a linha no topo, sem caixa.
- Sobreposições (tooltip, popover, sheet e menus) não mudam. O tema claro usa
  as mesmas formas com placas derivadas dos tokens do claro.

`Painel` preserva dominante/apoio, erros locais, vazios e aparato metodológico.
Superfície opaca, borda simples; nenhum ateliê, brilho especular, vidro ou fundo
animado interfere nos gráficos. `EstadoVazio` nomeia o que falta e o próximo
passo; o endpoint de origem fica em **Método e ressalvas**, não na face do painel.

### Leitura progressiva — 22/10/2026

- **Analisar:** mantém “arrastar e pronto”. Depois da leitura, a confirmação de
  gravação e o resumo vêm primeiro; a conversa fica legível sem marcações.
  Probabilidades, sinais por mensagem e contribuições só aparecem quando pedidos.
  Apenas o primeiro resumo do lote é dominante; os demais são apoio.
- **Vazios confirmados:** sem histórico disponível, orientar ao primeiro arquivo
  e, com permissão, à integração. Com histórico fora do filtro, oferecer limpar
  período. Falha de leitura da API não pode virar convite para importar.
- **Período:** datas manuais e atalhos de 7 dias, 30 dias e todo o período
  compartilham `de`/`ate` na URL. O fim dos atalhos é o último dia com dados,
  explicitado junto aos controles; não é a data de hoje.
- **Apoio legível:** descrições de indicadores, períodos, vazios, método e drivers
  usam 14px (`text-sm`) com entrelinha confortável. Eixos e outras marcas densas
  preservam a escala própria, sem aumentar toda a interface indiscriminadamente.
- **Honestidade não recolhe:** estimativa, sem sinal, limitações do tempo
  sintético e avisos sobre o arquivo permanecem visíveis. Endpoints, definições
  técnicas e escala logit entram no aparato existente, sem um segundo sistema
  de notas explicativas.

### Atividade e carregamento — 22/10/2026

- A conferência de colunas carrega apenas quando solicitada; a espera tem
  `role="status"`. Não adicionar uma segunda chamada de leitura ou inferência
  para preparar os seletores.
- A sonda de saúde fica suspensa com a aba oculta e consulta ao voltar.
  Polling e tentativa manual compartilham somente a Promise em curso na mesma
  instância do provider. Isso não é cache de indicadores, sessão ou credencial;
  a cadência visível e os estados real/dublê/frio/erro permanecem os mesmos.

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

### Fraus-chan atrás da logo

Cinco cliques consecutivos na marca, com até dois segundos entre eles, revelam
a Fraus-chan. Quatro sprites novos compõem a entrada: espiar, puxar a fenda,
dar um passo e acenar. A coreografia dura cerca de três segundos, com
deslocamento do corpo, peso no passo e uma cortina diagonal que se abre.
Cada fase avança pelo `animationend` da personagem, sem temporizadores
paralelos ao CSS. A personagem e “Dar um oi” percorrem as mesmas três reações:
saudação, piscadinha cúmplice e comentário sobre a curiosidade de quem clicou.
“Rever entrada” remonta o palco e reinicia a coreografia mesmo na mesma fase.

As quatro poses de entrada foram geradas pelo gerador nativo do Codex,
solicitando `gpt-image-2` e usando a folha da Fraus-chan do `fraus-video` como
referência. Vieram numa folha única, recortada em quatro WebP transparentes
de 480×720, com escala e base dos pés alinhadas. Os prompts acompanham as
artes nos arquivos `.webp.json`; `face` e `wink` preservam as reações anteriores.
A pose antiga de puxar foi removida. Há seis imagens em `public/fraus-chan/`.
Componente e imagens carregam só depois de descobrir o segredo; a entrada
espera todas as imagens. Falha de imagem é explícita.
Não há geração de imagem em runtime, LLM, leitura de conversas,
áudio, canvas, persistência ou chamada de API dentro da brincadeira. As falas
são fixas; não são respostas de um assistente nem resultados do modelo.

Grafite, ouro e Chakra Petch seguem a ferramenta; o tema claro também é
respeitado. No celular, a personagem fica acima da fala e dos controles.
`prefers-reduced-motion` pula a entrada espacial e mantém todas as reações em
corte seco, inclusive ao ativar a preferência durante a animação. Não há
movimento em loop nem fechamento automático.
O diálogo Base UI contém foco, fecha por Escape/botão/clique fora e devolve
foco à marca. No celular, fechar o segredo não fecha a gaveta que o abriu.
O quebra-cabeça de fragmentos foi substituído, não conservado como outro modo.

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

`npm run test:lp` exercita sem JS, reduce, preloader por sessão, pin, índice,
inversão do fecho, ida e volta para `/entrar` sem sobras, sem WebGL, celular sem
rolagem lateral e o redirect de `/leitura`. `LP_EVIDENCIAS` guarda capturas.
Sem GPU o Chrome headless usa SwiftShader e o palco cai no WebP, de propósito;
`LP_GPU=1` pede GPU real para exercitar o WebGL. O vídeo do acesso derruba a GPU
do headless com Vulkan, por isso o QA bloqueia mídia: é artefato do teste.

`DASHBOARD_URL=http://127.0.0.1:3017 npm run test:atividade` verifica pausa de
sondas ocultas, reconsulta ao voltar, concorrência com tentativa manual e
recuperação da disponibilidade. Só aceita host local; controla visibilidade e
falhas HTTP no navegador, sem gravar dados nem provar inferência real.
O QA da LP também confere o letreiro ao voltar do fecho e sua pausa fora da tela;
com `LP_GPU=1`, inclui ciclos de perda/restauração sem acumular listeners.

`node scripts/validar-navegacao-playwright.mjs` opera rotas reais, período,
recolhimento/reload, atalhos durante edição, tooltip por foco, tema, marca e
gaveta móvel. `DASHBOARD_URL` aponta para o produto já iniciado; exige sessão
válida ou o modo local aberto. Também conferir dashboard vazia, atendimento sem
sinal, temas, grafo e navegação LP ↔ ferramenta.

`node scripts/validar-segredo-playwright.mjs` opera a entrada, as reações por
teclado/toque, replay na mesma fase, reabertura, foco e modais aninhados.
Confere mudança real dos pixels nas reações, carregamento sob demanda,
indicadores intactos e ativação de reduce durante a entrada, além de
desktop/celular/paisagem e temas claro/escuro.
`SEGREDO_EVIDENCIAS` guarda as capturas opcionais; `DASHBOARD_URL` aceita só host local.


A documentação MkDocs mantém sua aparência própria nesta entrega; não presumir
que o CSS do site foi redesenhado junto com o produto.
