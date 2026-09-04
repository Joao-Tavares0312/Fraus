---
title: "Nota de design — a reformulação visual do Fraus"
date: 2026-09-04
tags: [fraus, design, vitrine, dashboard, referencias]
---

# Nota de design — a reformulação visual

**Isto é nota de design, e só. Não há decisão de implementação aqui, nem
proposta de código.** Ela existe para preparar uma reformulação **completa** do
visual, e não a evolução incremental que a PR #31 entregou.

**O que mudou de intenção.** Em 04/09/2026 a escolha foi *evoluir* o mundo
*Pauta* — e foi o que se fez: hierarquia por peso na ferramenta, cena
acompanhando a rolagem na vitrine, cinco emendas ao `DESIGN.md`. Aquele trabalho
continua valendo e não é desperdício: ele consertou defeitos que existiriam em
qualquer desenho (aparato repetido seis vezes, cabeça vazada que o documento
prometia e a tela não entregava, vazio de 600px, coreografia vazando para o
Operate). Mas a decisão agora é **reformular por completo**, e esta nota é o
levantamento que essa decisão precisa.

---

## 1. O que as referências realmente fazem

Levantamento feito em 04/09/2026, visitando os seis sites e medindo — não de
memória.

| Referência | Fundo | Tipografia | Altura do documento | Camada ambiente |
|---|---|---|---|---|
| cornrevolution.resn.global | preto | Manifold CF Extra Bold + Gilroy | **0px** | 1 canvas (WebGL) |
| Personaal Studio | preto | Neue Haas Grotesk Display + PP Neue Montreal | **1.000px** | 2 vídeos |
| landonorris.com | off-white quente (`rgb(244,244,237)`) | Mona Sans Variable + Brier | 15.087px | **21 canvas** |
| Cloudflare | branco | FT Kunst Grotesk | 6.861px | 2 canvas + 1 vídeo |
| Stripe | branco | sohne-var | 15.101px | 2 canvas |
| Revolut | — | — | — | — |

**Revolut não pôde ser observado**: o site respondeu com uma verificação de bot
("Just a quick security check"), e contorná-la não é coisa que se faça. Fica
como lacuna declarada — se ele importa para a direção, a leitura tem que ser
feita à mão, num navegador de gente.

### 1.1 A descoberta que reorganiza tudo

**As duas famílias não diferem em aparência. Diferem no que "rolar" significa.**

- **Nas experimentais**, o documento praticamente **não tem altura**: 0px na
  corn, 1.000px na Personaal. A rolagem foi *sequestrada* — o gesto entra como
  entrada de uma cena em WebGL ou de um vídeo, e a página não percorre um
  documento, percorre um **tempo**. A corn tem uma única `<canvas>` e quatro
  `<section>`; a página inteira é a cena.
- **Nas de produto**, o documento é longo e honesto: 6.861px na Cloudflare,
  15.087px na landonorris, 15.101px na Stripe. A rolagem é rolagem. O canvas,
  quando existe, é **ornamento local** dentro de uma seção — não o meio de
  navegação.

A landonorris é o caso mais instrutivo dos seis, porque **fica dos dois lados**:
21 canvas espalhados por 15.000px de documento convencional. Ela usa a técnica
experimental como *material* dentro de uma estrutura de produto. É provavelmente
o ponto mais próximo do que o Fraus poderia ser sem virar outro produto.

### 1.2 Três padrões concretos que valem roubar

**O herói vazio (landonorris).** A primeira tela é quase inteiramente espaço
negativo: um padrão topográfico em traço finíssimo, e o conteúdo ancorado nas
**quinas** — a marca em cima à esquerda, o cartão da próxima corrida embaixo à
esquerda. Não há manchete centralizada. A confiança está em não preencher.

O herói do Fraus hoje faz o contrário: manchete grande, centralizada, com o
argumento inteiro. Não é pior por definição — mas é a escolha convencional, e é
por isso que ele lê como "landing page de produto" e não como as referências.

**A hierarquia dentro do parágrafo (Stripe).** A manchete é uma frase só, em
peso 300 a 44px, com o **início em tom escuro e a continuação em azul
dessaturado**. A hierarquia acontece por **cor dentro do mesmo bloco de texto**,
sem mudar tamanho nem peso.

Isso é diretamente aplicável ao Fraus, e de um jeito que quase nenhum produto
pode copiar: o Fraus já tem duas cores semânticas — **âmbar para o dito, azul
para o medido**. Uma manchete que troca de cor no meio da frase, exatamente onde
o assunto passa do que o cliente disse para o que o sistema mediu, seria a tese
do produto virando tipografia. A LP atual já flerta com isso ("o que foi *dito*"
/ "o que foi *medido*"), mas em blocos separados, não dentro da frase.

**A cor de acento única e ácida (landonorris).** Um verde-limão, usado
**exclusivamente** no botão de loja, contra uma paleta inteira de neutros
quentes. Uma cor, um trabalho.

O Fraus tem regra equivalente e mais rigorosa (`--primary` nunca codifica valor,
só ação e foco), mas o dourado é **fosco** (croma 0,085) e some contra o fundo
escuro. A referência mostra o que a regra pode render quando o acento é
**ácido** em vez de metálico.

---

## 2. As três tensões com o que existe hoje

Uma reformulação completa precisa decidir estas três antes de qualquer
composição. Elas não são detalhe: cada uma é premissa de tudo que vem depois.

### 2.1 Escuro por decreto, contra três das seis referências

O Fraus tem **dois temas, ambos escuros**, e a §3.1 do `DESIGN.md` argumenta o
fundo como "papel de ensaio grafite", com o motivo declarado de que o analista
fica horas nele.

Só que **Cloudflare, Stripe e landonorris são claras** — e são exatamente as
três referências de uso prolongado. As três escuras são as de visita curta.

A correlação é forte demais para ser coincidência: **fundo claro é o que as
interfaces lidas por horas escolhem**. Se a reformulação quer a legibilidade
diária de Stripe e Cloudflare, o compromisso de escuro-único é a **primeira**
coisa a interrogar, não a última.

Isso não é recomendação de trocar. É a constatação de que a decisão nunca foi
tomada contra alternativa — o escuro veio junto com o mundo *Pauta*, e o mundo
inteiro está em revisão agora.

**O que está em jogo se mudar:** os dois temas, a camada de ateliê inteira, os
pisos de vidro, e boa parte da §8. É a mudança mais cara desta lista, e a mais
estruturante.

### 2.2 A tipografia é a única peça que grita "padrão"

As seis referências usam grotescas licenciadas ou próprias: FT Kunst Grotesk,
sohne-var, Mona Sans Variable, Neue Haas Grotesk Display, PP Neue Montreal,
Manifold CF, Gilroy. **Nenhuma usa uma fonte que o leitor reconheça de outro
lugar.**

O Fraus usa **Inter**. Inter é excelente e foi escolha correta para o modo
Operate — mas é a tipografia que mais aparece em produto digital nesta década, e
ela carrega essa memória. Uma interface em Inter lê como "aplicação moderna
bem-feita"; nenhuma das seis referências lê assim.

**Esta é provavelmente a maior mudança por menor custo desta nota.** Trocar a
família de display — mantendo Inter no dado, se for o caso — muda a impressão de
autoria mais que qualquer outra decisão isolada, e não encosta em contraste,
piso ou arquitetura.

Duas restrições que a escolha precisa respeitar, e as duas já estão escritas no
projeto: numeral **tabular** em todo número que se compara, e **zero chamada de
rede em runtime** — a fonte entra por `next/font`, baixada no build e servida do
próprio deploy, como Inter e JetBrains Mono já entram.

### 2.3 O que acontece com a tese *Pauta*

O mundo atual tem uma tese forte: **acima da linha é o que foi dito, abaixo é o
que foi medido**. Ela é boa, é rara, e a PR #31 finalmente a executou na tela
(na seção dito × medido da vitrine).

Uma reformulação completa tem três saídas, e a escolha entre elas define o
resto:

1. **Manter a tese e trocar só a linguagem visual.** É a mais barata e a menos
   arriscada; o produto continua inimitável pelo mesmo motivo de hoje.
2. **Trocar a tese.** Aí é preciso ter outra que sustente o mesmo peso — a
   *Pauta* não é decoração, ela resolve a pergunta de como mostrar duas
   grandezas de escalas diferentes no mesmo eixo temporal. Substituir sem
   resposta equivalente é perder o que o produto tem de próprio.
3. **Abandonar a tese e assumir a convenção** (dashboards de produto, no molde
   Cloudflare/Stripe). Legítimo, e provavelmente o mais confortável para uma
   banca ler — ao custo de o produto parecer com todos os outros.

**Três compromissos sobrevivem a qualquer das três**, porque são do
`PRODUCT.md` e não do sistema de design: os textos de honestidade
("estimativa", "sem sinal", nota metodológica, estados vazios que nomeiam o que
falta); o encoding **âmbar = dito / azul = medido**; e o **gráfico sobreposto de
NPS × latência** — pode mudar de forma, a sobreposição fica, porque é o
trade-off que cartão isolado esconde.

---

## 3. O que a reformulação não pode quebrar

Independente da direção, estas continuam sendo verdade, e nenhuma delas é
questão de gosto:

- **Ausência de dado não é insatisfação.** "Sem sinal" nunca vira 0 — nem em
  célula, gráfico, ordenação, export ou agregado.
- **Nunca inventar número.** Onde falta dado, a tela nomeia o que falta e qual
  etapa resolveria. Numa ferramenta batizada com o nome do daemon do engano,
  dado plausível inventado é a pior falha possível.
- **Score, nota e categoria são derivados no servidor.** A interface apresenta,
  não recalcula.
- **Categoria nunca é comunicada só por cor** — nem só por forma.
- **Todo par de cor que carrega texto cruza AA por cálculo**, nos temas que
  existirem. `npm run contraste` é o juiz.
- **Nada que carrega dado é translúcido nem animado.**
- **Sem LLM em runtime**, e nenhuma chamada de rede no caminho de predição —
  o que inclui fonte, ícone e asset.

---

## 4. As perguntas que precisam de resposta antes de desenhar

Em ordem de consequência. Nenhuma delas é minha para responder.

1. **Claro ou escuro?** Decide ateliê, pisos, vidro e metade da §8.
2. **A tese *Pauta* fica, muda ou sai?** Decide a composição inteira.
3. **A ferramenta e a vitrine continuam sendo dois territórios com contratos
   diferentes**, ou passam a ser um sistema só? Hoje o `DESIGN.md` os separa, e
   foi essa separação que organizou a PR #31.
4. **A vitrine vai ao território experimental de verdade** — rolagem
   sequestrada, cena em WebGL como meio de navegação — ou fica no molde de
   documento longo com ornamento local, que é o da landonorris?
5. **Qual família tipográfica**, e ela cobre display e dado ou só display?
6. **Quanto tempo há até a banca?** Uma reformulação completa com fundo claro é
   trabalho de semanas, não de uma sessão — e existe uma pendência que bloqueia
   a API real (o retreino do `02_treino_fusor.ipynb`) que não tem nada a ver com
   design e continua aberta.

---

## 5. Um aviso de método, pago em dinheiro nesta sessão

Trabalho visual **se confere olhando**, e o instrumento mente. Nesta sessão, três
vezes:

- `fullPage` do Playwright **não dispara `whileInView`** e não dá conta de página
  alta — devolveu a vitrine em branco uma vez, e um vazio de ~2.900px na outra,
  que o DOM desmentiu. Capturar **por viewport**.
- `127.0.0.1:3000` leva **403 nos chunks** do Next 16 dev, enquanto
  `localhost:3000` não. Sem chunks não há hidratação, e o estado inicial dos
  componentes fica congelado — sintoma idêntico ao de um bug de animação.
- Um elemento `position: fixed` **parece curto** numa captura de documento
  inteiro. Foi assim que eu "descobri" uma barra lateral quebrada que estava
  perfeita.

A §9 do `DESIGN.md` já avisa que nenhum dos cinco gates vê a tela. O
complemento, aprendido aqui: **a captura também não é a tela** — ela é outro
instrumento, com os próprios modos de falha.
