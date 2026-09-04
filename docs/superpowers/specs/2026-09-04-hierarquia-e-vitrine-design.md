---
title: "Hierarquia na ferramenta, cena na vitrine — desenho"
date: 2026-09-04
tags: [fraus, design, dashboard, lp, pauta]
---

# Hierarquia na ferramenta, cena na vitrine

Evolução do mundo **Pauta**, não substituição dele. O `DESIGN.md` continua sendo
o contrato; este documento propõe emendas a ele e diz por quê.

## O pedido

"Que fique à altura das referências." As referências deixadas pelo dono do
projeto se dividem em duas famílias, e a divisão é exatamente a fronteira que o
`DESIGN.md` já traça entre modo Operate e vitrine:

| Família | Referências | Território |
|---|---|---|
| produto, densidade, uso diário | Cloudflare, Stripe, Revolut | as seis telas da ferramenta |
| experiência, scroll autorado | cornrevolution.resn.global, Personaal Studio, landonorris.com | `app/page.tsx`, a LP |

Duas direções, uma por território. A terceira direção considerada — fazer a
régua virar espinha estruturante da interface inteira — foi **recusada como
programa** e teve duas peças aproveitadas (§3.3 e §3.4 abaixo). O motivo da
recusa está em §7.

---

## 1. O levantamento

Feito em 04/09/2026, com Playwright contra o servidor de demonstração
(`FRAUS_DEMO_DUBLE=1`), oito rotas nos dois temas, 1600×1000.

**Duas armadilhas de instrumento que valem para a próxima vez:**

1. **`fullPage` do Playwright não dispara `whileInView`.** A primeira rodada
   devolveu 6111px de página quase toda preta, e a leitura ingênua seria "a LP
   está quebrada". Captura por viewport, rolando de tela em tela, é o que
   corresponde ao que o visitante vê.
2. **`127.0.0.1:3000` leva 403 nos chunks do Next 16 dev; `localhost:3000`
   não.** Sem os chunks não há hidratação, e sem hidratação o `initial="oculto"`
   do `Revelar` fica em opacidade zero para sempre — a página renderiza no
   servidor e nunca revela. O sintoma é idêntico ao de um bug de animação.

O círculo com "N" no canto superior esquerdo das capturas é o indicador de dev
do Next 16, não a marca do projeto.

### 1.1 O que está bom e não pode ser quebrado

A densidade. Atendimentos e Modelo são telas fortes: numeral tabular, "sem
sinal" tratado como categoria e nunca como zero, "Ironia · não entra no fusor"
impresso onde o usuário lê. O gráfico sobreposto de NPS × latência cumpre o
compromisso vinculante do `PRODUCT.md`. A vitrine anuncia 39 features — a
guarda da PR #29 está de pé.

### 1.2 Os quatro defeitos

1. **Tudo tem o mesmo peso.** Todo painel usa a mesma superfície, o mesmo raio,
   o mesmo espaçamento. Não existe primário → secundário → terciário legível de
   longe. Na tela Modelo, o fato mais importante — as métricas estão marcadas
   como suspeitas, a ironia saiu do vetor, o corpus é sintético — está em corpo
   de texto no meio da página, com o mesmo peso do lexicon de emoji.
2. **`Método e ressalvas` aparece de quatro a seis vezes por tela**, sempre
   idêntico. A §4.1 mandou a prosa metodológica para o aparato e isso funcionou;
   o que não foi resolvido é que seis aparatos iguais viram ruído. A honestidade
   fica com forma de repetição, não de rigor.
3. **A Visão geral tem cerca de 600px de vazio** entre a última linha de
   conteúdo e a nota metodológica do rodapé. Não é o respiro de ritmo vertical
   da §2.2; é buraco. A barra lateral tem o mesmo sintoma: termina por volta de
   1000px e deixa o ateliê como tira nua ao lado da tabela.
4. **O ateliê só existe no herói.** É o defeito mais grave da vitrine. As três
   referências experimentais são scroll autorado — a cena evolui conforme se
   desce. Aqui a grade, o sol e o campo de estrelas ocupam a primeira tela e a
   página vira preto chapado por cerca de 5.600px. A tese "espaço profundo"
   evapora exatamente onde a rolagem passa o tempo todo.

---

## 2. Arquitetura da mudança

Três camadas, com dependências em um sentido só:

```
tokens e vocabulario          globals.css, lib/movimento.ts
        ↓
componentes de composicao     Painel (nivel), Aparato (por tela),
                              CabecaVazada (nova), Atelier (cena)
        ↓
telas                         as seis da ferramenta + a LP
```

Nenhuma tela ganha regra própria de hierarquia. Quem decide peso é o
componente de composição, por parâmetro — pelo mesmo motivo que cor mora em
token: regra digitada de novo em outro lugar diverge, e a invariante 4 do
`CLAUDE.md` existe porque isso já aconteceu neste projeto.

---

## 3. Ferramenta — hierarquia por peso

### 3.1 Três níveis, um parâmetro

`Painel` passa a aceitar `nivel: "dominante" | "apoio"`. O nível decide
superfície, escala tipográfica do título e espaço ao redor — **não** decide cor,
e não inventa material: as três espessuras de vidro da §7 já existem e hoje são
consumidas quase indistintamente.

| Nível | Superfície | Papel |
|---|---|---|
| dominante | vidro médio, régua própria, mais alto | um por tela; é a resposta à pergunta que levou o analista ali |
| apoio | vidro fino, título menor, sem elevação própria | detalha ou desdobra o dominante |
| armadura | sem superfície | indicadores; rótulo mais número tabular, como a §2.2 já mandava |

A armadura **deixa de ser painel**. Isso não é regra nova: é a §2.2 sendo
cumprida.

### 3.2 O dominante de cada tela

| Tela | Dominante | Apoio |
|---|---|---|
| Visão geral | gráfico NPS × latência, largura cheia | distribuição de notas, piores atendimentos |
| Atendimentos | a tabela | faixa de resumo, que vira armadura |
| Modelo | **o veredito sobre o estado do modelo** | pesos, métricas, léxico de emoji, léxico curado |
| Grafo | o canvas | legenda das duas famílias |
| Integrações | lista de fontes | exemplo de `curl`, entregas |
| Configurações | faixas de NPS | limiares de latência |

O caso da tela Modelo é o que mais muda. Hoje a tela abre pelo simulador e
enterra no meio o que o avaliador precisa ler primeiro: métricas medidas em
corpus sintético, F1 de ironia marcado como suspeito, ironia fora do vetor. Esse
conjunto vira um bloco de veredito no topo, em nível dominante. É a aplicação
direta do princípio de produto 1 — a tela nomeia o que falta antes de mostrar
número.

### 3.3 Um aparato por tela

`Aparato` deixa de pendurar em cada painel e passa a existir **uma vez por
tela**, ancorado no pé, recolhendo as ressalvas dos sistemas acima. Cada painel
mantém uma âncora curta para a entrada correspondente.

O que **não** se mexe: os rótulos curtos `estimativa`, `observado` e
`sem sinal` continuam colados ao número e sempre visíveis. A §4.1 é explícita —
eles não são aparato. Nenhum texto de honestidade sai da tela; ele para de ser
dito seis vezes.

### 3.4 A cabeça vazada passa a existir

A §1.1 do `DESIGN.md` promete: atendimento sem sinal é **cabeça vazada** —
"o marcador existe, ocupa a posição temporal, e é oco". A interface imprime a
string "sem sinal". A notação nunca foi implementada; `CabecasDeLeitura.tsx` é
outra coisa (emoção e ironia por frase).

Componente novo `CabecaVazada`: anel oco, sem preenchimento, ocupando a posição
na tabela, na distribuição e na série. **Sempre acompanhado do rótulo textual** —
o `PRODUCT.md` exige que categoria nunca seja comunicada só por cor, e a mesma
disciplina vale para forma.

Esta é a peça de C que sobrevive, e ela é barata porque não pede tese nova:
transforma um princípio já escrito em forma já especificada.

### 3.5 A régua ancora o dominante

Onde o dado **de fato** se divide em dito e medido, o sistema dominante ganha a
régua (`--linha`), com o dito acima e o medido abaixo. Onde não se divide, a
régua não aparece.

Esta é a segunda peça de C, e o limite dela é a §1.1: forçar a metáfora onde ela
não cabe é decorar com notação, que é justamente o que aquela seção proíbe. A
transcrição já faz isso naturalmente; o gráfico de NPS × latência **não** faz
(as duas séries são medidas), e ali a régua não entra.

### 3.6 Fechar os dois buracos

O vazio da Visão geral fecha porque o dominante passa a ocupar o que sobrava. A
barra lateral encosta no rodapé.

---

## 4. Vitrine — o ateliê acompanha a rolagem

### 4.1 A cena deixa de ser pano de fundo do herói

Grade, planeta e campo de estrelas ganham estado ligado à posição de rolagem, e
cada seção da LP recebe âncora visual própria em vez de repetir a mesma caixa
escura por 5.600px. É o que separa esta LP das três referências experimentais.

Restrições que continuam valendo sem emenda:

- a cena mora **no ateliê**, a camada que não carrega dado — é por não carregar
  dado que ela pode ter croma alto sem inventar canal sem rótulo (§8.2);
- a cena passa **por baixo** da luz e do vidro;
- nada que carrega dado é translúcido nem animado.

### 4.2 O terceiro momento autorado, e o argumento que a §6 exige

A §6 declara que a interface se permite **dois** momentos autorados e que um
terceiro "precisa de argumento novo". Coreografia de rolagem é o terceiro.

O argumento proposto: **a §6 governa o modo Operate**, e a LP é vitrine
declarada. O `DESIGN.md` já abriu exatamente essa exceção uma vez, na §8.7, para
o campo de partículas em WebGL — "a ferramenta é lida por horas e não pode ter
GPU girando atrás do dado; a vitrine é visita de 40 segundos". A conta continua
em **dois na ferramenta**, e a vitrine passa a ter licença nomeada, com a mesma
fronteira de contrato.

Se o dono do projeto recusar esse desmembramento, o caminho honesto é o outro:
a conta vai a três e fica registrada como custo assumido. **A decisão é dele**,
e este documento não a toma sozinho.

### 4.3 Movimento reduzido

`prefers-reduced-motion` desliga a coreografia **inteira** e a LP cai no ateliê
estático de hoje — não numa versão lenta. É a mesma regra da §8.7 sobre o campo
de partículas: quem pede menos movimento recebe `null`, não um efeito devagar.

Duas frentes, porque uma não alcança a outra: o bloco do `globals.css` zera
transição de CSS, e o `MotionConfig reducedMotion="user"` cobre o que Motion
anima em JS.

---

## 5. Estados, erro e vazio

A §5 do `DESIGN.md` continua inteira, e a mudança de hierarquia cria um caso
novo que precisa de resposta declarada:

- **o dominante falha e o apoio carrega.** Falha isolada já é regra; o que muda
  é que um dominante quebrado deixa um buraco maior. O erro ocupa a caixa do
  dominante, com o mesmo peso visual dele, e os apoios continuam de pé.
- **o dominante está vazio.** Estado vazio nomeia o que falta e qual etapa
  resolveria. Numa tela cuja resposta principal não existe, o vazio é o
  dominante — não um aviso pequeno num painel grande.
- **a API está fora.** `AvisoApiFora` já existe e sobe de nível: é o dominante
  da tela enquanto durar.

---

## 6. Verificação

Os cinco comandos da §9, e a razão de nenhum bastar:

| Comando | Quando |
|---|---|
| `npm run pisos` | qualquer mudança no `Atelier.tsx` ou em opacidade de camada |
| `npm run contraste` | qualquer mudança de token de cor ou de espessura de vidro |
| `npx tsc --noEmit` | sempre |
| `npm run lint` | sempre |
| `npm run build` | sempre, antes de dar qualquer coisa por pronta |

E a regra que os cinco não cobrem: **conferir olhando**, nos dois temas, numa
tela cheia e numa vazia. A §9 lista três defeitos que passaram verdes pelos
cinco gates — o papel pautado invisível a 5,5%, a grade colapsada em 30px e o
portão medindo uma superfície que não existia.

**Alerta de contraste herdado, e ele é o primeiro a reprovar:** a §8.6 registra
`--detrator-texto` sobre o piso do vidro fino como o par mais apertado da
interface — **4,54** na chuva, contra um limiar de 4,5. Qualquer luz nova no
ateliê derruba esse par, e ele é **cor de dado** (categoria de NPS), não cromo:
a §8.6 já declara que mexer nele é decisão de outra ordem.

Duas ressalvas sobre esse número, e as duas mandam **remedir antes de confiar**:

1. o segundo valor registrado naquela seção é do tema **grafite**, que foi
   descartado na §8. O par equivalente no **espaço profundo** — o padrão de
   fábrica de hoje, cujo vidro é o mais fino dos três, a 56% — nunca foi
   registrado no documento;
2. como §4.1 acende a cena ao longo da rolagem, o pior caso deixa de ser um
   ponto e passa a ser uma trajetória. A conta precisa ser refeita **para o
   estado mais claro que a cena atinge em qualquer ponto da rolagem**, não para
   o estado inicial. Piso otimista é pior que piso nenhum — a §8.6 registra que
   isso já aconteceu duas vezes neste projeto.

A ordem de resolução não muda: a espessura cede, o portão não.

---

## 7. Escopo — o que este trabalho não faz

- **Não encosta na camada de dado.** Matiz de família de sinal, cores de
  categoria e `--primary` fora de dado ficam como estão.
- **Não recalcula nada.** Score, nota e categoria são derivados no servidor
  (invariante 3). Nenhuma composição nova lê ou repete essa regra.
- **Não toca no fusor, no notebook nem nos artefatos.** O retreino do
  `02_treino_fusor.ipynb` continua sendo a pendência que bloqueia a API, e é
  independente desta frente.
- **Não vira mundo novo.** A direção C — a régua como espinha estruturante da
  interface inteira — foi recusada como programa por dois motivos: ela obriga a
  reescrever o `DESIGN.md` e a refazer a conta de pisos e contraste do zero, e o
  risco dela é ler a tela passar a exigir entender a metáfora, que a §1.1
  proíbe. Duas peças foram aproveitadas (§3.4 e §3.5) justamente por não
  custarem tese nova.

**Ressalva de dado:** o levantamento foi feito com o motor dublê, cujos números
são sintéticos. A composição precisa aguentar os números reais depois do
retreino, e por isso é dimensionada pelos casos extremos — nota 0, "sem sinal",
métrica ausente, texto longo de transcrição —, não pelo que o dublê produziu.

---

## 8. Emendas que este trabalho propõe ao `DESIGN.md`

Registradas aqui para serem escritas lá quando a implementação fechar:

1. **§2.2** — a armadura deixa de ser painel, cumprindo o que a seção já dizia;
   `Painel` ganha nível.
2. **§4.1** — o aparato passa a ser um por tela, e não um por painel. Os rótulos
   curtos continuam fora do aparato.
3. **§1.1** — a cabeça vazada sai do papel e vira componente.
4. **§6** — a coreografia de rolagem da vitrine, com o argumento da §4.2 deste
   documento, ou a conta subindo para três, conforme a decisão do dono do
   projeto.
5. **§8.6** — pisos remedidos para o estado mais claro da cena ao longo da
   rolagem.
