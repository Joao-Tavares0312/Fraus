# Fraus — Design System

Contrato visual da interface. Quem escrever UI neste projeto segue este
documento. Ele não descreve como as telas estão hoje: descreve como elas devem
ser.

**Mundo:** *Pauta* — a conversa notada como partitura.
**Chassi:** shadcn/ui sobre Tailwind v4, tokens em OKLCH, tema escuro único.

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

Tema escuro único. Tokens em `app/globals.css`; consumo via classes utilitárias.
Nada de hex solto em componente.

### 3.1 O fundo é papel, não vazio

O fundo não é preto: é **papel de ensaio grafite**. Preto puro faz a régua
flutuar no vácuo e transforma dado em néon. A superfície precisa parecer estoque
de papel sob luz de escritório — o analista fica horas nela.

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

### 3.3 A cor da marca: o dourado do monograma

`--primary` é o **dourado do R da logo**, medido do próprio arquivo
(`public/fraus-logo.png`): a letra vai de `oklch(0.514 0.066 84)` no pé a
`oklch(0.824 0.079 76)` no topo, e o token é o meio dessa rampa —
`oklch(0.78 0.085 80)`.

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

`--radius` é `0.375rem`, e era `0.625rem`. O F e o R são chanfrados a 45° e
não têm uma curva de canto sequer; o raio antigo arredondava o controle a
ponto de ele não ter parentesco nenhum com a marca. Não vai a zero porque
botão e campo totalmente quadrados brigariam com o chassi inteiro — cartão,
popover, sheet — por causa de um detalhe.

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

Sem sequência orquestrada de entrada: o analista chega para trabalhar, não para
assistir a página carregar.
