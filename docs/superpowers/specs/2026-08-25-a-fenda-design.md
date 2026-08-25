# A fenda — a marca que racha

**Data:** 2026-08-25
**Escopo:** `dashboard/public/fraus-logo.svg`, `dashboard/public/fraus-marca.svg`,
`dashboard/components/shell/MarcaFraus.tsx` (novo),
`dashboard/components/shell/NavegacaoLateral.tsx`, `dashboard/DESIGN.md`, `README.md`.

---

## 1. O problema

Três coisas separadas que moram no mesmo arquivo:

1. **A logo não fala o tema.** `fraus-logo.svg` traz o gradiente dourado
   **hardcoded** (`rgb(170,134,80)` → `rgb(226,195,148)`). Quando a chuva de neon
   está ligada, a sidebar mostra uma marca dourada num tema magenta.
   `fraus-marca.svg` já resolveu isso para o fundo do Ateliê — a logo da
   navegação ficou para trás.
2. **A marca é inerte.** Ela não responde a gesto nenhum. Não é bug, mas é a
   única peça de identidade da interface e ela não tem nada a dizer.
3. **A citação está errada.** A nota `[^4]` do README credita a Virgílio a
   presença de Fraus no vestíbulo do Orco (*Eneida* VI.273-281). **Ela não está
   naquela lista.** Detalhe de rigor num trabalho que vai a banca.

## 2. A mitologia — o que é verificável

**O que a *Eneida* VI.273-281 realmente lista:** Luctus, Curae ultrices, pallentes
Morbi, tristis Senectus, Metus, malesuada Fames, turpis Egestas, Letum, Labos,
Sopor, gaudia mala mentis, mortifer Bellum, as Eumênides e Discordia. **Fraus não
aparece.**

**A fonte que serve:** Cícero, *De Natura Deorum* **III.17**. Ele enumera, para
argumentar contra, a prole de **Érebo e Noite**: *Amor, Dolus, Metus, Labor,
Invidentia, Fatum, Senectus, Mors, Tenebrae, Miseria, Querella, Gratia, **Fraus**,
Pertinacia*, as Parcas, as Hespérides e os Sonhos.

Isto é mais forte que a citação que substitui, por três razões:

- é **nominal** — Fraus está lá, escrita;
- dá **genealogia**, não só localização: filha do Escuro e da Noite;
- e nomeia **Dolus** como irmão dela — que é o nome antigo deste projeto, nas
  specs de 13/08. A coincidência não foi planejada, mas é verdadeira, e uma
  banca que a perceba encontra coerência em vez de licença poética.

## 3. O desenho

### 3.1 Tokenização — e por que ela obriga o SVG a virar componente

**Um `<img>` não recebe cor da página.** Hoje a logo entra por
`next/image` (`<Image src="/fraus-logo.svg">`), e um SVG referenciado assim é um
**documento externo**: `currentColor` não resolve, e `var(--marca-cor)` não
atravessa a fronteira. Não existe tokenizar o arquivo e continuar servindo-o como
imagem — a única saída é o desenho virar **SVG inline** dentro de
`MarcaFraus.tsx`. É o que o componente da §4 já faz por outra razão, e é o que
torna a fenda animável: `<img>` também não deixa animar parte do desenho.

Inline, o `<linearGradient>` **é preservado** — a rampa de dois tons é a marca, e
achatá-la em `currentColor` empobreceria o desenho. O que muda são as **paradas**,
que passam a sair de dois tokens (`--marca-cor-pe` e `--marca-cor-topo`), com os
valores atuais do dourado como padrão do tema grafite. A chuva de neon redefine os
dois e a marca inteira a acompanha.

**O arquivo `public/fraus-logo.svg` continua existindo**, com o gradiente dourado
literal: ele é o asset de `og:image`, do README e de qualquer consumo fora do
React, onde token nenhum alcança. A duplicação é real e é o preço de a marca
existir dentro e fora da aplicação; fica registrada aqui para não ser "consertada"
por engano.

**`fraus-marca.svg` NÃO é tokenizado, e isso é decisão, não esquecimento.** Ele é
consumido como **máscara CSS** no `Atelier.tsx` (`mask-image`), onde só o canal
alfa é lido — cor ali é descartada pelo navegador. As letras continuam forçadas a
branco puro, porque branco é alfa 1. Tokenizar aquele arquivo seria escrever
código que não tem efeito observável.

O `<rect>` preto opaco de `fraus-logo.svg` **permanece**. É ele que separa os dois
arquivos, e o `DESIGN.md` já registra o bug que a remoção reintroduziria.

### 3.2 A fenda

Um `<path id="fenda">` diagonal de ~1,5px atravessa o `F` e o `S`. Parada, lê como
detalhe de desenho — invisível a 28px, evidente ampliada.

Ela não é ornamento: é a **junta por onde a marca se abre**. Sem ela, a animação
da revelação seria um efeito colado por cima do desenho; com ela, o desenho se
abre pela própria costura. **Os dois arquivos recebem a fenda**, para continuarem
sendo o mesmo desenho — a marca do Ateliê a ganha como recorte de alfa.

## 4. A interação

Componente novo: `dashboard/components/shell/MarcaFraus.tsx`, dono do desenho e do
contador. `NavegacaoLateral` passa a renderizá-lo no lugar do `<Image>`. **O
`<Link>` de navegação é preservado** — o primeiro clique continua indo para a
visão geral, e o easter egg não pode custar navegação.

| gesto | resposta |
|---|---|
| parada | **nada.** Imóvel. |
| hover | varredura do dourado de baixo para cima, **pela fenda**, 220 ms |
| clique 1–4 | tremor crescente (1 px → 3 px); o dourado esquenta a cada clique |
| clique 5 | a fenda abre (§5) |
| 2 s sem clique | o contador zera |

O estado vive **só na memória do componente**. Nada em `localStorage`, nada no
banco, nada na URL — um easter egg que persiste vira configuração, e configuração
tem painel.

### 4.1 Por que isto não emenda a §6 do DESIGN.md

A §6 proíbe **animar na carga** ("nada anima por ter montado") e diz que um
terceiro momento autorado precisa de argumento novo. Nenhuma das duas é violada:

- **parada, a marca é imóvel** — não há animação ociosa, de entrada, ou de
  respiro. A carga da página não move um pixel dela;
- **momento autorado é o que a interface executa por conta própria** — o cursor
  de leitura, a entrada dos sistemas. Isto é **resposta a gesto do usuário**, a
  mesma categoria dos `transition-colors` de 150 ms que a interface inteira já
  usa em hover. Se hover de botão contasse como momento autorado, a §6 já estaria
  violada em cada linha da navegação.

O `DESIGN.md` recebe essa nota **por escrito**, para que a próxima sessão não
releia a §6 e conclua que a fenda a quebrou.

## 5. A revelação

As metades se afastam ~14 px pela fenda, o dourado vira `--destructive` por
200 ms, e por dentro aparece a Noite:

> **FRAVS**
> *Erebo et Nocte nata* — filha do Escuro e da Noite,
> irmã de **Dolus** e de **Metus**.
> Cícero, *De Natura Deorum* III.17

Fecha por clique fora, `Esc`, ou 8 s — o que vier primeiro.

`role="dialog"`, `aria-modal`, foco preso enquanto aberto e devolvido ao gatilho
no fechamento, `aria-label` descrevendo o conteúdo. Easter egg não é licença para
quebrar acessibilidade.

### 5.1 `prefers-reduced-motion`

Varredura, tremor e afastamento morrem. **Os cinco cliques continuam contando** e
a revelação vira **corte seco** — aparece e some, sem transição. O segredo não é
privilégio de quem tolera movimento.

Respeitado nas duas frentes que o `DESIGN.md` §6 exige: o bloco do `globals.css`
zera as transições de CSS, e qualquer animação em JS passa pelo `<Movimento>` com
`reducedMotion="user"`.

## 6. Testes

- **Contador:** cinco cliques dentro da janela abrem a revelação; quatro cliques
  seguidos de 2,5 s de silêncio zeram o contador e o quinto clique posterior conta
  como primeiro.
- **Navegação preservada:** o primeiro clique continua disparando a navegação para
  a visão geral.
- **Fechamento:** `Esc` fecha e devolve o foco ao gatilho.
- **Build da dashboard verde** e `npm run contraste` continuando a passar — o
  vermelho da revelação sobre o vidro é a superfície que a emenda de 24/08 já
  mediu como pior caso.

## 7. Documentação

- **`DESIGN.md`**: a fenda entra na seção da marca; a nota da §4.1 registra por que
  a §6 continua intacta.
- **`README.md`**: a nota `[^4]` troca Virgílio por Cícero III.17, com o texto da
  §2 deste documento. A menção a Virgílio no corpo (§ *O problema*) é reescrita
  pela mesma razão.

## 8. Fora de escopo — por decisão

- **Tema claro** (pendência 4 do README): sessão própria.
- **A marca de fundo do Ateliê como alvo de clique**: continua decorativa, sem
  `pointer-events`. Um segundo gatilho seria um segundo contador para manter em
  sincronia, sem ganho.
- **Persistência do easter egg** entre sessões: ver §4.
- **Revisão de segurança da API**: trabalho separado, nesta mesma sessão, depois
  desta entrega.

---

# Emenda de 25/08/2026 — a revelação era paia

A §5 entregava um cartão com uma citação. Diagnóstico do que estava errado, nos
termos que importam:

1. **A recompensa era um `<div>` com texto.** Cinco cliques para ganhar um
   tooltip com pretensão.
2. **Contava um fato em vez de provocar uma sensação.** "Fraus é filha da Noite"
   é trivia. A tese do projeto é *o cliente mente*; o easter egg devia fazer
   sentir isso, não informar sobre mitologia.
3. **Não usava nada que o Fraus é.** Podia estar em qualquer projeto. Um easter
   egg bom usa a máquina do próprio produto contra quem o encontrou.

## E1. Ele analisa QUEM clicou

Os cinco cliques têm timestamps: são uma conversa. `lib/pontuarCliques.ts` —
função pura, testada — extrai as latências, acha a hesitação e devolve uma
leitura 0–100.

**A trava de honestidade, e ela não é negociável:** o painel declara em texto
visível que a leitura sai **só do sinal de tempo — sem texto, sem emoji, sem
modelo**. O front não carrega BERTimbau. Apresentar isso como "o score do Fraus"
seria o projeto mentindo sobre a própria metodologia dentro de uma piada, que é
o pior lugar concebível para fazê-lo.

**Não há `nota` nem categoria de NPS.** A invariante 3 proíbe derivar as duas no
cliente, e o README registra que duplicar essa regra em TypeScript já produziu
divergência de arredondamento nas fronteiras 6/7 e 8/9. A leitura 0–100 não é a
escada do NPS e não vira uma; o desfecho do painel é a acusação, não um rótulo
de categoria.

## E2. E a dashboard mente enquanto o painel está aberto

`CartaoIndicador` é o único lugar onde os números-manchete renderizam — um
contexto (`MentiraProvider`) alcança os quatro sem caçar número por sete telas.

**As quatro travas que separam isto do que a invariante 2 condena:**

| trava | por quê |
|---|---|
| **Nada sai da memória** | zero escrita no banco, zero chamada à API. É render-time, e some no fechamento |
| **Leitor de tela recebe a VERDADE** | o número falso é `aria-hidden`; o `sr-only` diz que o valor foi falsificado e qual é o real. Mentir para quem depende de leitor de tela não tem piada nenhuma |
| **O selo é inescapável** | `FRAUS ESTÁ MENTINDO` fixo, em `--destructive`, no mesmo quadro dos números — não existe captura de tela da dashboard mentindo sem o aviso dentro dela |
| **Volta sozinha** | 8 s, `Esc` ou clique fora, o que vier primeiro |

## E3. Fora de escopo, e por decisão

**Gráficos e tabela não mentem.** Só os quatro indicadores. Espalhar a mentira
pelo Recharts é onde ela deixa de ser contida e passa a arriscar sobrar na tela
depois do fechamento — e uma dashboard que continua mentindo sem o selo é
exatamente o defeito que as travas acima existem para impedir.

O que a §5 tinha e **sobrevive**: a fenda como junta, o tremor dos quatro
primeiros cliques, a varredura no hover, e Cícero III.17 no pé do painel.
