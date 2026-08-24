# Fraus — Design System

Contrato visual da interface. Quem escrever UI neste projeto segue este
documento. Ele não descreve como as telas estão hoje: descreve como elas devem
ser.

**Mundo:** *Pauta* — a conversa notada como partitura.
**Chassi:** shadcn/ui sobre Tailwind v4, tokens em OKLCH, **dois temas, ambos
escuros** — grafite (padrão de fábrica) e chuva de neon (ver seção 8).

---

## 1. A tese, e por que ela governa a composição

Um atendimento é uma **sequência temporal de turnos com duração**. Isso é o que
a notação musical resolve há quatrocentos anos, e resolve melhor do que a
fileira de cartões que a categoria entrega.

A notação faz uma coisa que nenhum dashboard genérico faz: ela **separa o que
está acima e o que está abaixo da linha**. Acima vai o articulado — letra,
dinâmica, expressão. Abaixo vai o medido — cifra, andamento, baixo contínuo.

> **Acima da linha é o que foi DITO. Abaixo da linha é o que foi MEDIDO.**

Essa é a regra mestra da interface, e ela é **estrutural antes de ser cromática**.
A metáfora de cor (âmbar/azul) permanece e passa a ter uma casa: âmbar mora
acima, azul mora abaixo. Quando alguém precisa quebrar a regra de posição, a cor
ainda desambigua — mas quebrar a posição é a exceção que se justifica no código.

### 1.1 O que é notação e o que é decoração

**Nenhum glifo musical é desenhado.** Sem clave, sem semínima, sem pentagrama de
cinco linhas. A gramática entra como **estrutura e ritmo**, não como fantasia:

| Elemento da notação | O que ele é aqui | Por quê |
|---|---|---|
| a linha | régua horizontal de referência que divide dito e medido | dá eixo comum a séries de escalas diferentes |
| a barra de compasso | filete vertical marcando a virada do dia | agrupa o tempo sem legenda |
| a pausa | intervalo proporcional à latência | silêncio com duração notada é exatamente a espera |
| a ligadura | marcação do trecho que puxou a nota | atribuição por sentença |
| a dinâmica | peso e tamanho do tipo, não cor | intensidade sem gastar canal de cor |
| **a cabeça vazada** | atendimento **sem sinal** | ocupa o tempo e não soa: a regra "ausência não é zero" vira forma |

A cabeça vazada é a peça mais importante desta lista. O princípio de produto
"ausência de dado não é insatisfação" deixa de ser nota de rodapé e passa a ser
**notação**: o marcador existe, ocupa a posição temporal, e é oco.

Se em algum momento ler esta interface exigir saber solfejo, a regra foi
aplicada errado. O modo é **Operate**: expressão nunca obscurece a tarefa.

---

## 2. Composição

### 2.1 O que sai

- **A fileira de cartões-KPI no topo.** É o "template de métrica-herói", e ele
  empurra a tese da tela para baixo da dobra.
- **O cartão como estrutura de página.** Painel com borda e fundo próprio deixa
  de ser o agrupador padrão; agrupa-se por **espaço e régua**.

  > **Emenda de 21/08/2026.** O painel voltou a ter fundo e borda próprios ao
  > adotar o vidro líquido (ver seção 7). A regra original continua valendo no
  > que ela realmente defendia — a página é uma pilha de sistemas, não uma
  > grade de cartões, e quem agrupa continua sendo espaço mais régua. O que
  > mudou é que o sistema agora tem **material**, e material precisa de
  > superfície. Registrado como custo assumido, não como regra revogada.
- **O parágrafo explicativo acima de cada painel.** A prosa metodológica não
  some — muda de lugar (ver 4).

### 2.2 O que entra

**O sistema é a unidade de composição.** Como numa partitura, um *sistema* é uma
faixa horizontal de largura total que carrega uma linha de tempo e tudo que a
anota. A página é uma pilha de sistemas, não uma grade de cartões.

**A armadura.** Os indicadores agregados (NPS, CSAT, contenção, latência) vivem
à esquerda do primeiro sistema, empilhados e compactos — como a armadura de
clave, que se lê de uma vez e não se relê a cada compasso. Eles são **rótulo
mais número tabular**, sem barra de progresso decorativa e sem cartão.

**Ritmo vertical.** Densidade varia entre sistemas: um sistema denso ganha o
direito de um respiro depois. Mais espaço acima de um título do que abaixo.

---

## 3. Tokens

Tokens em `app/globals.css`; consumo via classes utilitárias. Nada de hex solto
em componente.

Os valores abaixo são os do tema **grafite**, o padrão de fábrica. O tema chuva
de neon sobrepõe apenas o chassi e não encosta na camada de dado — ver seção 8.

### 3.1 O fundo é papel, não vazio

O fundo não é preto: é **papel de ensaio grafite**. Preto puro faz a régua
flutuar no vácuo e transforma dado em néon. A superfície precisa parecer estoque
de papel sob luz de escritório — o analista fica horas nela.

> **Emenda de 24/08/2026 — o papel é pautado.** A regra acima dizia papel liso.
> O fundo passou a carregar **linhas horizontais de ritmo constante**, nos dois
> temas, por decisão do dono do projeto.
>
> O que **não** mudou, e é o que a regra original defendia de verdade: o fundo
> continua sendo papel e não vazio, continua sem preto puro, e continua sem
> competir com o dado — as linhas moram no ateliê, a camada que não carrega
> informação, e passam **por baixo** da luz.
>
> **Elas não são um pentagrama.** A §1.1 proíbe desenhar glifo musical e manda a
> gramática entrar como estrutura e ritmo; agrupar em cincos seria desenhar a
> pauta, ritmo constante é papel pautado. A régua do sistema (`--linha`) segue
> sendo a única linha que **afirma** alguma coisa.
>
> O custo veio na hora e está pago: a textura levantou o pior caso das
> superfícies translúcidas nos dois temas. Os pisos foram **remedidos** (o
> grafite saiu de 0,25/0,24/0,23 para 0,309/0,28/0,246) e o vidro fino da chuva
> precisou engrossar de novo — 68% → 71% —, porque `--destructive` sobre ele
> havia caído para 4,46:1. A ordem de sempre: a espessura cede, o portão não.

> **Emenda de 24/08/2026 (segunda) — a marca é impressa no papel, e o papel
> ficou forte.** A emenda anterior autorizou o papel pautado, mas a
> implementação entregou grafite a 5,5% de opacidade: 1px a cada 13px, a 5,5%,
> sobre fundo escuro, **não chega a ser visto**. A peça existia no código e não
> na tela. A contenção já tinha sido negociada e perdida; foi a implementação
> que continuou protegendo o contrato antigo. Corrigido: **0,055 → 0,12** no
> grafite e **0,13 → 0,22** na chuva.
>
> O fundo passou também a carregar o **monograma da marca**, sangrando pela
> quina inferior direita, nos dois temas.
>
> **É máscara, não imagem de fundo**, e a distinção é o inteiro da peça.
> O arquivo da logo **carrega um fundo opaco** — o PNG era RGB sem canal alfa,
> e o SVG que o substituiu traz um `<rect>` preto cobrindo os 640×640. Usar
> qualquer um dos dois como `background-image` pintaria um quadrado opaco por
> cima do ateliê, que é exatamente o bug que o `SidebarInset` com
> `bg-background` já causou. `public/fraus-marca.svg` é o mesmo desenho **sem
> esse fundo** e com as duas letras forçadas a branco: quem pinta é o
> `background` do elemento, via `--marca-cor`. É isso que entrega "a logo com
> o tema respectivo aplicado" — dourada no grafite, magenta na chuva — sem
> gerar dois arquivos e sem tema novo pedir asset novo.
>
> O "fade + gradiente" é uma **segunda camada de máscara** cortada por
> `mask-composite: intersect`: a marca nasce sólida onde sai da tela e se
> dissolve subindo. Sem isso ela leria como adesivo colado.
>
> O que **não** mudou: nada disso carrega dado. É a mesma camada do ateliê, o
> único lugar onde cor saturada não inventa canal de significado, e a §1.1
> continua valendo — o monograma é a marca, não um glifo musical.
>
> O custo, de novo pago na hora: `--muted-foreground` e `--destructive` sobre
> vidro fino caíram para 4,25 e 3,86. A espessura cedeu — 45% → 55% no fino e
> 62% → 72% no médio no grafite, 71% → 81% e 75% → 85% na chuva. Ver §8.6.

> **Emenda de 24/08/2026 (terceira) — o fundo ganha grade e sol.** O fundo
> passou a carregar uma **grade em perspectiva** (linhas convergindo para um
> horizonte a 320px, espaçadas a 44px, `--grade-op` em 0,1 no grafite e 0,2 na
> chuva) e um **sol listrado** no horizonte (`--sol-op` em 0,16 no grafite e
> 0,3 na chuva), nos dois temas.
>
> O que **não** mudou: as duas peças moram no ateliê, a mesma camada do papel
> pautado e da marca impressa, não carregam dado, e passam **por baixo** da
> luz — a mesma garantia das duas emendas acima, agora estendida a mais duas
> peças.
>
> O custo, de novo em pisos e espessura de vidro: o vidro fino da chuva foi
> de 71% para **74%**, e o vidro médio da chuva **recuou** de 75% para 74% —
> ele havia subido para 81%/85% no meio do trabalho da Task 8 e voltou quando
> um bug de medição foi corrigido. O saldo desta sessão contra o início dela:
> fino subiu 3 pontos, médio caiu 1. No grafite, o vidro fino foi de 55% para
> **64%**; médio (72%) e denso (82%) da chuva (86%) ficaram como estavam.

| Token | Papel |
|---|---|
| `--background` | estoque de papel; grafite neutro, nunca `#000` |
| `--card` | segunda camada de papel, para o que precisa de leve elevação |
| `--linha` | a régua do sistema; meio ponto, sempre visível e nunca dominante |
| `--compasso` | filete de virada de dia; mais fraco que `--linha` |
| `--foreground` | tinta |
| `--muted-foreground` | **piso de cor de texto** — nada mais claro que ele carrega texto |

### 3.2 As duas vozes

| Token | Voz | Onde mora |
|---|---|---|
| `--dito` | âmbar — fala, texto, emoji, o que o cliente articulou | **acima** da linha |
| `--medido` | azul — score, probabilidade, latência, tendência | **abaixo** da linha |

Cada uma tem variante `-texto` com contraste verificado. Cor de marcação e cor
de tipo não são a mesma coisa: `npm run contraste` é o juiz, e todo par que
carrega texto cruza AA (4.5:1).

#### 3.2.1 No grafo, as duas vozes viram duas *famílias*

O canvas do grafo da memória é a única tela com **nove tipos de nó**, e duas
cores não distinguem nove coisas: `categoria`, `canal`, `fonte` e `feature`
saíam todas do mesmo azul, e quem olhava não separava o eixo aprendido pelo
fusor de um canal de atendimento.

A regra não foi trocada — ela subiu de nível. **A família continua dizendo
dito/medido; o matiz dentro dela passou a dizer o tipo:**

| Família | Faixa de matiz | Tipos |
|---|---|---|
| **dito** (quente) | 30–95 | `emoji` 30, `conversa` 60, `termo` 95 |
| **medido** (frio) | 150–340 | `fonte` 150, `canal` 195, `feature` 265, `categoria` 305, `desfecho` 340 |

Tokens `--no-<tipo>`, todos em **L 0.75 / C 0.14**. Claridade e croma iguais são
deliberados: matiz distingue o tipo, e claridade não pode virar hierarquia
acidental — um nó mais claro pareceria mais importante, e nenhum tipo é mais
importante que outro.

`--no-importacao` é a exceção, e ela é semântica: cinza acromático, porque
importação é um nó **solto** cuja origem o schema não rastreia, e cinza é a
ausência de afirmação — a mesma disciplina da cabeça vazada do `sem_sinal`.

A leitura de longe ("isto é fala ou é medida?") sobrevive intacta; a de perto
("que coisa é esta?") passa a existir. E porque essas nove cores só existem
nesta tela, ela carrega **legenda própria** agrupada pelas duas famílias:
nove matizes sem legenda seriam o grafo afirmando uma distinção que o leitor
não tem como ler.

### 3.3 A cor da marca: o dourado do monograma

`--primary` é o **dourado do R da logo**, medido do próprio arquivo: a letra é
um gradiente, e o token é o meio da rampa dele — `oklch(0.78 0.085 80)`.

> **Nota de 24/08/2026 — a rampa deixou de ser amostrada e passou a ser lida.**
> A medição original saiu do PNG por amostragem de pixel: `oklch(0.514 0.066 84)`
> no pé a `oklch(0.824 0.079 76)` no topo. Com a marca vetorial
> (`public/fraus-logo.svg`), a rampa vem das próprias paradas do gradiente e é
> exata: `oklch(0.642 0.084 76)` a `oklch(0.832 0.071 78)`. **O token não
> mudou** — `0.78 0.085 80` já caía dentro dela, e o argumento do croma fosco
> (0,085 contra os 0,15 do âmbar do "dito") sobrevive intacto. Registrado
> porque a fonte da verdade mudou de arquivo, não porque a cor mudou.

**Por que deixou de ser lime.** O `--primary` era `oklch(0.843 0.179 134)`,
herdado do chassi. Nenhum pixel da logo é verde: a identidade é um monograma
**F branco + R dourado sobre quase-preto**, e uma dashboard cuja cor de ação
não existe na marca é uma identidade aplicada pela metade. O fundo grafite já
concordava com o `#070707` do arquivo; faltava a cor de ação.

**Por que isso não colide com o âmbar do “dito”**, que é semântico e
intocável: o que separa os dois **não é o matiz, é o croma**. O dourado da
marca é fosco (`0.085`) e o âmbar do dito é saturado (`0.15`) — metálico
contra pigmento. Some-se a isso que eles nunca dividem superfície:
`--primary` preenche **controle**, `--dito` marca **dado**.

**A regra que sustenta essa convivência, e que não pode ser afrouxada:**
nenhuma série, categoria ou barra usa `--primary`. A única exceção nomeada é
**o cursor de leitura** — o filete vertical que marca onde você está na linha
do tempo, como no editor de partitura —, e mesmo ele não codifica valor
nenhum. Fora disso, `--primary` só aparece em ação primária e foco de teclado.
Por isso **promotor é teal, não verde**: precisa estar longe do cursor.

`--warning` (`oklch(0.8 0.14 80)`) compartilha o matiz do dourado. Ele
sobrevive porque é **texto** (`--warning-rich-text`, o rótulo “suspeito” das
métricas) e nunca preenchimento — e porque o croma o separa, pelo mesmo
argumento acima. Se um dia surgir um botão de alerta preenchido, este é o par
que precisa ser repensado primeiro.

### 3.3.1 O raio acompanha os cortes do monograma

`--radius` era `0.375rem`, e antes disso `0.625rem`. O F e o R são chanfrados a
45° e não têm uma curva de canto sequer; o raio de 0,625rem arredondava o
controle a ponto de ele não ter parentesco nenhum com a marca. Em 0,375rem não
ia a zero porque botão e campo totalmente quadrados brigariam com o chassi
inteiro — cartão, popover, sheet — por causa de um detalhe.

> **Emenda de 24/08/2026 — o chassi endureceu, e a objeção caiu.**
> `--radius` foi de `0.375rem` para **0.125rem** (2px), por decisão do dono do
> projeto. O argumento que segurava o raio em 0,375rem era o chassi arredondado
> ao redor — cartão, popover, sheet, sidebar; era essa vizinhança que um botão
> quase quadrado brigaria com. Essa vizinhança não existe mais: os painéis
> grandes (`Painel.tsx`, `FaixaIndicadores.tsx`) passaram a ser chanfrados a
> 45° via `clip-path`, no mesmo desenho do F e do R, e a sombra migrou de
> `box-shadow` para `filter: drop-shadow()` porque `clip-path` descarta
> `box-shadow`. Com o chassi cortado a 45° em vez de arredondado, um raio quase
> reto deixou de ser a peça fora do lugar — passou a ser a única consistente.

### 3.3.2 O rótulo dentro do botão é verificado

`scripts/contraste.mjs` checava texto sobre fundo e **não checava texto sobre
superfície preenchida** — ou seja, não checava o par mais clicado da
interface. A lacuna apareceu justamente ao trocar o lime pelo dourado, que é
o tipo de mudança capaz de derrubar a legibilidade do botão sem nenhum aviso.
O script passou a cobrir `--primary-foreground` sobre `--primary` (hoje
**9,64:1**) e o par equivalente da sidebar.

### 3.4 Categorias

Detrator, neutro e promotor mantêm cores distintas e **nunca** são comunicadas
só por cor — sempre acompanham rótulo textual.

---

## 4. Tipografia

Uma família só, sans de sistema. O modo Operate tem permissão para isso, e o
analista lê em DPI consistente: fonte de display em rótulo e dado é proibida.

- **Escala fixa em rem**, razão apertada (1.125–1.2). Nada fluido.
- **Numeral tabular e monoespaçado em todo número que se compara** (`.num`).
  Número que dança ao atualizar é ruído, não dado.
- **Dinâmica por peso e tamanho.** Ênfase não gasta cor — a cor está reservada
  para dito/medido.
- Medida de prosa 65–75ch.

### 4.1 A prosa metodológica vira aparato

Os textos de honestidade **permanecem, todos**. O que muda é a posição: eles
saem de cima do dado e vão para o **aparato** — o rodapé do sistema, na tipografia
menor, onde a partitura põe nota de editor.

Regra: o dado aparece primeiro, a explicação fica a um gesto de distância e
**nunca** empurra o dado para baixo da dobra. Recolher é permitido; remover não.

Os rótulos curtos — `estimativa`, `observado`, `sem sinal` — não são aparato:
ficam colados ao número, sempre visíveis.

---

## 5. Estados

Todo componente interativo tem: padrão, hover, foco, ativo, desabilitado,
carregando, erro e vazio. Não se entrega metade.

- **Carregando** é esqueleto com a forma do resultado, nunca roda girando.
- **Vazio** nomeia o que falta e qual etapa ou endpoint resolveria.
- **Falha isolada:** um sistema que não carrega mostra o próprio erro no lugar
  dele, e os vizinhos continuam de pé.
- **Sem sinal** é cabeça vazada, nunca zero, nunca cinza dentro da escala.

## 6. Movimento

150–250 ms, e **um momento autorado** em vez de efeitos espalhados: o cursor de
leitura deslizando ao percorrer a linha do tempo. Movimento comunica estado,
não decora. `prefers-reduced-motion` desliga o deslize e mantém o cursor
estático.

**Emenda de 24/08/2026 — a entrada dos sistemas.** A regra original desta seção
era "sem sequência orquestrada de entrada: o analista chega para trabalhar, não
para assistir a página carregar". Ela foi afrouxada num ponto e mantida no
resto, e a distinção é a seguinte:

- **continua proibido** animar na carga da página. Nada anima por ter montado;
- **passa a ser permitido** um sistema subir 8 px ao **entrar em cena pela
  rolagem**, uma única vez (`whileInView` + `once`). Isso não é abertura de
  cortina: é a mesma resposta que o olho já espera de algo que aparece por
  rolagem, e ela diz *de onde o bloco veio*.

A armadura de indicadores escalona os quatro filhos em 40 ms. O intervalo é
curto de propósito: os 80–100 ms de praxe fariam o quarto indicador chegar
quase meio segundo depois do primeiro, e aí o analista **espera** — que é
exatamente o que a regra original proíbe. 40 ms lê como um gesto só.

O custo declarado: esta é a segunda peça de movimento da interface, e a seção
dizia "um momento autorado". São dois agora — o cursor de leitura na linha do
tempo e a entrada dos sistemas. Um terceiro precisa de argumento novo.

O vocabulário (duração, curva, distância) mora em `lib/movimento.ts`, um lugar
só, pelo mesmo motivo que a cor mora em token. `prefers-reduced-motion` é
respeitado em duas frentes, porque uma não alcança a outra: o bloco no fim do
`globals.css` zera transição de CSS, e o `<Movimento>` no layout raiz passa
`reducedMotion="user"` ao Motion, que anima em JS e não obedeceria ao CSS.

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

---

## 8. Os dois temas

**Emenda de 24/08/2026.** Até aqui este documento dizia "tema escuro único, sem
alternador", e a §3.1 chama o fundo de *papel de ensaio*, com o argumento
explícito de que preto puro "transforma dado em neon". Passa a haver um segundo
tema, **chuva de neon**, por decisão do dono do projeto — e ele é exatamente a
estética que aquele parágrafo recusava.

O grafite continua sendo o **padrão de fábrica** e a posição de projeto. A chuva
é opção, não substituição.

### 8.1 A tese do tema chuva

Rua molhada à noite: neon frio de fachada refletido no asfalto, e a luz de
**sódio** do poste — que é âmbar-dourada. É isso que resolve o conflito entre
vaporwave e a marca: numa cena de chuva noturna, luz quente de poste ao lado de
neon frio não é contradição, é o retrato. O dourado do monograma deixa de ser um
metal solto sobre roxo e passa a ser a lâmpada da rua.

### 8.2 O que o tema NÃO toca

Três regras, e elas eram o que separava "segundo tema" de "outro produto":

1. **A camada de dado inteira fica como está.** `--dito` continua âmbar,
   `--medido` continua azul, e as sete famílias de sinal mantêm os matizes. O
   magenta e o violeta do vaporwave vivem **só no ateliê**, que é a única
   camada que não carrega dado — e é por não carregar dado que ela pode ter
   croma alto sem inventar canal sem rótulo.
2. **O dourado continua fora de dado**, só em controle e marca.
3. **Todo par de texto continua cruzando AA por cálculo**, agora medido nos dois
   temas.

> **Emenda de 24/08/2026 — a regra 1 deixa de valer, e a atribuição dela
> estava errada.** A regra 1 acima ("a camada de dado inteira fica como
> está") deixou de valer por decisão do dono do projeto: as sete famílias de
> sinal, as três categorias de NPS e os oito nós coloridos do grafo subiram
> croma e claridade.
>
> **O que continua de pé:** o matiz de cada família ficou **congelado** — só
> saturação e claridade mudaram, e o matiz é o canal que carrega o encoding;
> saturação nunca carregou significado nenhum. `--no-importacao` continua
> cinza. `--primary` continua fora de dado, regra 2 intacta. Categoria
> continua nunca comunicada só por cor, sempre com rótulo textual — regra 3
> intacta.
>
> **A correção de rota, e é a parte que importa:** o texto acima chamava essa
> regra de "compromisso vinculante do `PRODUCT.md`". **Não é, e nunca foi.**
> Fomos reler o `PRODUCT.md`: ele exige duas coisas, e só duas — que todo par
> de cor que carrega texto cruze AA por cálculo, e que categoria nunca seja
> comunicada só por cor. Ambas continuam valendo e não foram violadas por
> esta emenda. "A camada de dado inteira fica como está" nunca esteve no
> `PRODUCT.md`; era decisão de design tomada pelo dono do projeto, e foi o
> mesmo dono do projeto que a revogou agora. Atribuir a um documento de
> produto uma regra que era decisão de design é o tipo de erro que este
> projeto não pode se dar ao luxo de deixar impresso.

### 8.3 O gate passou a ser ciente de tema

`scripts/contraste.mjs` mantinha **um mapa único** de tokens para o arquivo
inteiro. Com dois temas declarando `--background`, o segundo sobrescreveria o
primeiro e o relatório sairia verde tendo medido um tema só — falha silenciosa,
que é o modo de falha que este gate existe para evitar.

Ele agora recorta o bloco de cada tema, **sobrepõe à base como a cascata do CSS
faz** (um tema só declara o que muda) e roda a matriz inteira por tema. Tema
novo entra sem tocar no script: basta o seletor começar com `.tema-`.

### 8.4 Onde a escolha mora

No `<html>`, como classe, e no `localStorage` — não em contexto de React. Quem
precisa saber o tema é o CSS, e o CSS já sabe ler classe.

O grafite é a **ausência** de classe, não uma classe própria: ele é o `:root`, e
um tema padrão que precisasse se declarar para funcionar quebraria em toda tela
renderizada antes do JavaScript. Um script inline no `<head>` aplica a classe
antes da primeira pintura; sem ele, quem escolheu a chuva veria a tela pintar em
grafite e trocar depois da hidratação, a cada navegação.

### 8.5 Onde a chuva pode gritar

O tema foi empurrado para ser chamativo em 24/08/2026, e o empurrão respeita a
regra de 8.2: **só o que não carrega dado ganhou saturação.**

> **Nota de 24/08/2026 — a tabela vale para os dois temas.** O título desta
> seção pressupõe um tema só, e não é bem assim: a decisão de 24/08/2026 foi
> **estrutura igual nos dois temas** — cada peça abaixo existe no componente
> tanto no grafite quanto na chuva, e é o tema, não o componente, quem decide
> cor e intensidade. No grafite **só asfalto e chuva ficam em zero**; as
> outras seis estão acesas, apenas contidas — marca impressa em 0,15, grade
> a laser em 0,1, sol listrado em 0,16, papel pautado em 0,12, e quina e
> sombra ativas com suas próprias cores. É a chuva que grita, não o grafite
> que apaga.

| Peça | O que faz | Por que pode gritar |
|---|---|---|
| **quina do vidro** | ciano na aresta de cima, magenta na de baixo | é tubo de neon: a luz da fachada bate em cima, o reflexo do chão sobe embaixo. Toda superfície tem quina, então acender a aresta acende a interface inteira **sem uma célula de dado mudar de cor** |
| **sombra** | deixa de ser preta e vira derrame violeta | preto sob um painel apoiado em asfalto molhado lê como buraco; o halo lê como a luz do próprio painel vazando para o chão |
| **especular** | tingido de magenta | realce branco no meio de uma paleta tingida lê como falha de renderização |
| **reflexo no asfalto** | faixa de luz subindo do rodapé | é o que separa "fundo roxo com manchas" de "fachada espelhada em chão molhado" |
| **chuva** | riscos diagonais finos, **estáticos** | dá textura para o vidro refratar sem gastar quadro |
| **marca impressa** | o monograma sangrando pela quina inferior direita, em magenta | é máscara pintada pelo tema, não imagem: mora no ateliê, não codifica valor nenhum, e o magenta é o mesmo par de néon da quina do vidro |
| **grade a laser** | grade em perspectiva convergindo para um horizonte | é o piso do vaporwave clássico: converte o ateliê em cenário de fuga, sem tocar dado |
| **sol listrado** | sol com faixas horizontais no horizonte | a segunda peça do mesmo cenário; nos dois temas, com intensidade decidida por tema |

**A chuva não cai**, e isso é decisão: a §6 já gastou os dois momentos de
movimento que a interface se permite, e chuva animada seria um terceiro que não
comunica estado nenhum — decoração rodando atrás de tabela e gráfico o tempo
todo.

As duas peças novas existem no componente nos **dois** temas; o grafite as
mantém em opacidade zero. Um segundo componente de ateliê só para a variante
custaria mais do que dois tokens.

### 8.6 O preço: o vidro da chuva é mais grosso

Acender o ateliê levantou o piso das superfícies translúcidas, e o portão
reprovou três pares — `--destructive` sobre vidro fino caiu para **3,53:1**.

A resolução seguiu a regra da seção 7: **a espessura ganha opacidade até
passar.** 45% → 68% no fino, 62% → 74% no médio, 82% → 86% no denso. Baixar a
luz para salvar o contraste teria sido resolver pelo lado errado, ainda mais num
tema cujo pedido era justamente ficar mais chamativo.

Os pisos deste tema são **medidos, não estimados**: as camadas do ateliê
compostas no mesmo ponto (pior caso, ainda que geometricamente impossível — a
mancha da marca fica no alto à esquerda e a fria embaixo à direita), cada
espessura por cima, e a luminância resultante convertida de volta para OKLCH.
Piso otimista é pior que piso nenhum: ele faz o portão devolver verde medindo
uma superfície que não existe.

> **Emenda de 24/08/2026 — a medição virou script, e ela estava errada.**
>
> Esta conta já tinha sido feita três vezes à mão, e nas duas primeiras morreu
> num scratchpad. Agora é `dashboard/scripts/pisos.mjs` (`npm run pisos`): ele
> lê o `globals.css`, compõe o ateliê, aplica cada espessura e imprime o piso
> que cada uma deveria ter. Medição sem instrumento versionado vira chute na
> terceira rodada — e virou.
>
> Refeita a conta com o script, os pisos da chuva registrados aqui
> (0,307/0,294/0,257) eram **otimistas mesmo para o ateliê daquela época**: o
> vidro fino dava 0,333. O portão vinha medindo uma superfície mais escura que
> a real, ou seja, devolvendo verde com folga que não existia. É exatamente o
> modo de falha que o parágrafo acima descreve, e ele aconteceu aqui. Os
> valores vigentes estão no `globals.css` e batem com o script.
>
> **Um pessimismo a menos, e ele é lido da geometria.** O papel pautado **não
> soma** com as peças do rodapé: a máscara dele
> (`radial-gradient(140% 100% at 50% -10%, black 15%, transparent 70%)`) zera
> por volta de 60% da altura da tela, então onde ele tem força as outras ainda
> não começaram. O script disputa "papel pautado" contra "marca impressa +
> grade a laser" e fica com a composição mais clara. O resto do pior caso segue
> impossível de propósito (as manchas de luz no mesmo ponto), porque ali a
> impossibilidade é barata.
>
> **Correção da revisão final (24/08/2026) — a marca e a grade NÃO eram
> disjuntas, e esta emenda afirmava que eram.** A versão anterior deste
> parágrafo dava como prova a máscara antiga da marca
> (`radial-gradient(120% 120% at 100% 100%, ..., transparent 72%)`), estreita o
> bastante para deixar massa só num raio pequeno. Essa máscara foi **alargada
> depois**, de propósito, para a marca ficar visível: hoje é
> `radial-gradient(150% 150% at 100% 100%, black 34%, transparent 96%)` num
> elemento de 115vmin ancorado na quina inferior direita — e a grade ocupa a
> faixa `bottom-0 h-[45vh]` de largura total, mais forte justamente colada no
> rodapé. O pixel "linha da grade sobre traço do monograma" existe. O modelo de
> medição não acompanhou a mudança de geometria, e por isso os seis pisos
> ficaram otimistas. Corrigido: **marca e grade somam**; só o papel pautado
> continua disjunto. Premissa de disjunção é afirmação sobre geometria — quem
> mexer numa máscara do `Atelier.tsx` reconfere a lista em `pisos.mjs`.
>
> **O que continua sendo julgamento de olho.** O ateliê só aparece nas calhas
> entre painéis e **através** do vidro; numa tela cheia, engrossar o vidro
> apaga a luz que a emenda acabou de acender. A intensidade da marca foi posta
> no teto em que ela ainda **não** é a camada que manda no piso — 0,15 no
> grafite, 0,22 na chuva —, e a presença dela veio de **escala** (115vmin), que
> é de graça: o pior caso já assume a cor da marca em algum pixel, então o
> tamanho não custa contraste nenhum.

> **Emenda de 24/08/2026 (segunda) — os números finais, e um par sem folga
> nenhuma.** A grade, o sol e a marca impressa (0,12/0,22) levantaram o piso
> de novo, e a resolução foi a mesma de sempre: a espessura cede. Vidro fino
> do grafite foi de 55% para **64%**; médio (72%) e denso (82%) do grafite
> ficaram como estavam. Na chuva, vidro fino foi de 71% para **74%** e vidro
> médio **recuou** de 75% para **74%** — ele chegou a subir para 81%/85% no
> meio do caminho e voltou quando um bug de medição foi corrigido; denso
> (86%) não mudou. Contra o início desta sessão, o saldo da chuva é: fino
> subiu 3 pontos, médio caiu 1.
>
> **Um par ficou exatamente no fio.** `--destructive` sobre o piso do vidro
> fino do grafite fecha em **4,50:1** — o limiar do WCAG AA, não um número
> acima dele. Zero folga: qualquer luz nova no ateliê do grafite — mais uma
> peça, mais opacidade em alguma das que já existem — derruba esse par sem
> precisar de erro nenhum no cálculo. Fica registrado como o candidato mais
> provável a reprovar na próxima rodada.
>
> **As nove cores que carregam texto foram convertidas de `hsl()` para
> `oklch()`.** É conversão matematicamente equivalente, não repintura — o
> motivo foi o portão: `scripts/contraste.mjs` precisava enxergá-las para
> medir, e três delas nunca tinham sido medidas em tema nenhum antes desta
> sessão. As nove passam AA nos dois temas, incluindo essas três.

> **Emenda de 24/08/2026 (terceira) — os números depois de consertar a
> disjunção.** Com marca e grade somadas (ver a correção acima), os seis pisos
> ficaram otimistas e o portão reprovou: `--destructive` × vidro fino caiu para
> **4,29** no grafite e **4,39** no fino e no médio da chuva. A regra de sempre:
> a espessura cede, a luz não. Vidro fino do grafite subiu de 1 em 1 —
> 64% → 65% → 66% → 67% → 68% → **69%** —, remedindo o piso a cada passo; médio
> (72%) e denso (82%) do grafite não mudaram. Na chuva, fino e médio subiram
> juntos de 74% para **76%**; denso (86%) não mudou.
>
> O par crítico deixou o fio: `--destructive` × piso do vidro fino fecha em
> **4,54** no grafite e **4,52** na chuva. Continua sendo o par mais apertado
> da interface e o primeiro candidato a reprovar se o ateliê ganhar luz nova.
