# Mona Sans no display e o herói de quinas — plano de implementação

> **Para trabalhadores agênticos:** SUB-SKILL OBRIGATÓRIA: use
> superpowers:subagent-driven-development (recomendado) ou
> superpowers:executing-plans para implementar tarefa a tarefa. Os passos usam
> caixa (`- [ ]`) para acompanhamento.

**Objetivo:** trocar a família de display da vitrine por Mona Sans e reancorar o
herói nas quinas, executando as frentes §2.2 e §1.2 da nota de reformulação
visual.

**Arquitetura:** a fonte entra por `next/font/local` a partir de `.woff2`
versionados no repo, expondo `--fonte-mona`, que governa apenas duas classes de
display no `globals.css`. O herói vira uma coluna que distribui conteúdo entre
topo e base, com a manchete ancorada embaixo. Nenhum token de cor, tema ou
componente da ferramenta é tocado.

**Stack:** Next.js 16 (App Router), Tailwind v4 com tokens em `@theme` no
`globals.css`, `next/font/local`, vitest para os testes de lógica.

**Spec:** [`docs/superpowers/specs/2026-09-04-tipografia-e-heroi-design.md`](../specs/2026-09-04-tipografia-e-heroi-design.md)

## Restrições globais

Valem para **todas** as tarefas abaixo, sem exceção:

- **Zero chamada de rede em runtime.** A fonte é baixada uma vez agora, commitada
  e servida do próprio deploy — como Inter e JetBrains já são.
- **Nenhuma dependência nova de npm.** Nem para teste, nem para build.
- **Identificadores e nomes de arquivo em português, sem acento nos símbolos.**
  Texto de interface leva acento normal.
- **Commits em português, sem acento, no formato `tipo(escopo): resumo`.**
- **Fonte de display é proibida em rótulo e dado.** A exceção nomeada é a vitrine
  (`app/page.tsx`), e ela não se estende à ferramenta.
- **`--primary`, os tokens de cor, os dois temas e o encoding âmbar/azul não são
  tocados** por nenhuma tarefa deste plano.
- **Nada que carrega dado é translúcido nem animado.**
- Todo comando roda de dentro de `dashboard/` — não há `package.json` na raiz.

---

## Estrutura de arquivos

| Caminho | Responsabilidade | Tarefa |
|---|---|---|
| `dashboard/app/fontes/MonaSansVF[opsz,wght].woff2` | arquivo da fonte variável, versionado | 1 |
| `dashboard/app/fontes/LICENSE.md` | licença da Mona Sans, ao lado do binário | 1 |
| `dashboard/app/layout.tsx` | carregar a fonte e expor `--fonte-mona` no `<html>` | 1 |
| `dashboard/app/globals.css` | ligar `--fonte-mona` às duas classes de display | 1 |
| `dashboard/lib/tipografia.test.ts` | guarda de regressão do escopo da fonte | 1 |
| `dashboard/DESIGN.md` | emenda à §4 nomeando a família e o escopo | 1 |
| `dashboard/app/page.tsx` | herói de quinas; parágrafo migra de seção | 2 |

---

## Tarefa 1: Mona Sans no display

**Arquivos:**
- Criar: `dashboard/app/fontes/MonaSansVF[opsz,wght].woff2`
- Criar: `dashboard/app/fontes/LICENSE.md`
- Criar: `dashboard/lib/tipografia.test.ts`
- Modificar: `dashboard/app/layout.tsx` (bloco de fontes, linhas 1–24; `<html>`, ~linha 70)
- Modificar: `dashboard/app/globals.css` (bloco `@theme`, ~linhas 231–237; `.display-vitrine` ~1009; `.titulo-vitrine` ~1016)
- Modificar: `dashboard/DESIGN.md` (§4, ~linhas 342–360)

**Interfaces:**
- Produz: a variável CSS `--fonte-mona`, e o token `--fonte-display` que a
  empilha com fallback de sistema. A Tarefa 2 não os usa diretamente — ela usa
  as classes `.display-vitrine` e `.titulo-vitrine`, que já existem.

- [ ] **Passo 1: baixar a fonte e a licença**

O release oficial é `github/mona-sans`, v2.0.27, conferido em 04/09/2026. O asset
é o **`webfonts`** — os nomes exatos foram levantados em 04/09/2026, depois de a
primeira tentativa deste passo bater em 404 num nome inventado.

```bash
cd dashboard && mkdir -p app/fontes && cd app/fontes
curl -sL -o mona-sans.zip https://github.com/github/mona-sans/releases/download/v2.0.27/Mona-Sans-Webfonts.zip
unzip -l mona-sans.zip          # confira os nomes ANTES de extrair
unzip -o -j mona-sans.zip '*MonaSansVF[opsz,wght].woff2' -d .
unzip -o -j mona-sans.zip '*LICENSE*' -d .
rm mona-sans.zip
```

**O corte é o de dois eixos, `[opsz,wght]`, ~137 KB** — e não o
`MonaSansVF[wdth,opsz,wght].woff2` de ~308 KB, que também existe no zip. O eixo
`wdth` não é acionado por nenhuma regra que este plano cria: as duas classes de
display só definem `font-family`, e `.display-vitrine` trava `font-weight: 500`.
Pagar 2,2× o peso por um eixo que ninguém usa é peso morto. O `opsz` do corte
menor, ao contrário, serve exatamente ao caso — é fonte de display em corpo
grande, e o ajuste óptico vem de graça.

**Não renomeie o arquivo.** Um nome que anuncia eixos que o binário não tem é uma
mentira que a próxima pessoa paga. Se a licença vier com outro nome, essa sim
renomeie para `LICENSE.md`.

Se o `.woff2` variável não estiver no zip, **pare e escale** — não substitua por
outra fonte, não improvise com pesos estáticos, e não carregue por URL.

- [ ] **Passo 2: escrever o teste que falha**

Este teste é a guarda do que a spec chama de escopo exato: a fonte manda em duas
classes e em mais nenhuma. Ele lê o CSS de verdade, no molde do
`scripts/contraste.mjs`, então não há lista duplicada para desatualizar.

Crie `dashboard/lib/tipografia.test.ts`:

```ts
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * O DESIGN.md §4 proíbe fonte de display em rótulo e dado, e a vitrine é a
 * única excecao nomeada. Este teste le o globals.css de verdade: se alguem
 * ligar a Mona Sans no corpo, num rotulo ou num dado, ele cai.
 */
const CSS = readFileSync(join(__dirname, "..", "app", "globals.css"), "utf8");

/** Toda regra do arquivo, como par (seletor, corpo). */
function regras(): Array<{ seletor: string; corpo: string }> {
  const encontradas: Array<{ seletor: string; corpo: string }> = [];
  const padrao = /([^{}]+)\{([^{}]*)\}/g;
  let achado: RegExpExecArray | null;
  while ((achado = padrao.exec(CSS)) !== null) {
    encontradas.push({ seletor: achado[1].trim(), corpo: achado[2] });
  }
  return encontradas;
}

describe("a familia de display", () => {
  it("define --fonte-mona uma vez", () => {
    expect(CSS).toContain("--fonte-mona");
  });

  it("governa .display-vitrine e .titulo-vitrine", () => {
    for (const alvo of [".display-vitrine", ".titulo-vitrine"]) {
      const regra = regras().find((r) => r.seletor === alvo);
      expect(regra, `regra ${alvo} nao existe`).toBeDefined();
      expect(regra!.corpo).toContain("var(--fonte-display)");
    }
  });

  it("nao vaza para nenhuma outra regra", () => {
    const vazamentos = regras()
      .filter((r) => r.corpo.includes("var(--fonte-display)"))
      .map((r) => r.seletor)
      .filter((s) => s !== ".display-vitrine" && s !== ".titulo-vitrine");
    expect(vazamentos).toEqual([]);
  });

  it("nao troca a sans nem a mono do resto do produto", () => {
    expect(CSS).toContain("--fonte-sans: var(--fonte-inter)");
    expect(CSS).toContain("--fonte-mono: var(--fonte-jetbrains)");
  });
});
```

- [ ] **Passo 3: rodar o teste e confirmar que falha**

```bash
cd dashboard && npm test -- tipografia
```

Esperado: FALHA. A primeira asserção já quebra, porque `--fonte-mona` ainda não
existe no `globals.css`.

- [ ] **Passo 4: carregar a fonte no layout**

Em `dashboard/app/layout.tsx`, acrescente o import ao lado dos existentes:

```ts
import localFont from "next/font/local";
```

Depois do bloco de `jetbrains`, acrescente:

```ts
/**
 * A DISPLAY DA VITRINE, e só dela — DESIGN.md §4. Mona Sans variável, a mesma
 * da landonorris.com, escolhida em 04/09/2026 pelo diagnóstico da nota de
 * reformulação: as seis referências usam grotescas de autoria, e a Inter
 * carrega a memória de "aplicação moderna bem-feita".
 *
 * `next/font/local` a partir do arquivo VERSIONADO no repo, e não
 * `next/font/google`: o binário está em app/fontes/, servido do próprio
 * deploy. Nenhuma chamada de rede, nem no build nem em runtime.
 */
const mona = localFont({
  src: "./fontes/MonaSansVF[opsz,wght].woff2",
  variable: "--fonte-mona",
  display: "swap",
  weight: "200 900",
});
```

E no `<html>`, acrescente a variável à lista que já existe:

```tsx
className={`dark ${inter.variable} ${jetbrains.variable} ${mona.variable}`}
```

- [ ] **Passo 5: ligar a fonte às duas classes**

Em `dashboard/app/globals.css`, no bloco onde `--fonte-sans` e `--fonte-mono` são
montadas (~linha 234), acrescente logo abaixo delas:

```css
  /* A display da vitrine. Ela NAO entra em --fonte-sans: quem manda no corpo,
     no rotulo e no dado continua sendo a Inter, e a fonte de display segue
     proibida ali (DESIGN.md secao 4). O fallback e a propria pilha de sistema,
     para o caso de o .woff2 falhar em carregar. */
  --fonte-display: var(--fonte-mona), ui-sans-serif, system-ui, sans-serif;
```

Em `.display-vitrine` (~linha 1009) e `.titulo-vitrine` (~linha 1016), acrescente
como primeira declaração de cada uma:

```css
    font-family: var(--fonte-display);
```

- [ ] **Passo 6: rodar o teste e confirmar que passa**

```bash
cd dashboard && npm test -- tipografia
```

Esperado: PASSA, as quatro asserções.

- [ ] **Passo 7: emendar o DESIGN.md §4**

Em `dashboard/DESIGN.md`, na §4 (~linhas 356–358), o texto hoje diz que a exceção
da LP "usa a própria Inter em corpo grande com tracking até −0.02em". Substitua a
menção pela família nova, mantendo o resto da frase:

```markdown
> rótulo e dado, e fonte de display segue proibida — a exceção nomeada é a
> **LP** (`app/page.tsx`), vitrine fora do modo Operate, onde o display usa
> **Mona Sans** variável em corpo grande com tracking até −0.02em. Ela entra
> por `next/font/local` a partir de `app/fontes/`, versionada no repo, e
> governa exatamente duas classes: `.display-vitrine` e `.titulo-vitrine`.
> `lib/tipografia.test.ts` é o juiz desse escopo — nenhuma terceira regra pode
> usá-la, porque rótulo e dado continuam sendo território da Inter.
```

- [ ] **Passo 8: rodar os gates**

```bash
cd dashboard && npm test && npm run contraste && npm run lint && npm run build
```

Esperado: tudo verde. O `contraste` não deveria mudar de resultado — nenhum par
de cor nasceu aqui —, e é justamente por isso que ele roda: para provar.

- [ ] **Passo 9: commit**

```bash
git add dashboard/app/fontes dashboard/app/layout.tsx dashboard/app/globals.css dashboard/lib/tipografia.test.ts dashboard/DESIGN.md
git commit -m "feat(vitrine): mona sans na display, e so nas duas classes dela"
```

---

## Tarefa 2: o herói de quinas

**Arquivos:**
- Modificar: `dashboard/app/page.tsx` (herói, linhas 327–405; seção do artefato, a partir de 436)

**Interfaces:**
- Consome: as classes `.display-vitrine` e `.etiqueta-vitrine`, que a Tarefa 1 já
  reapontou para a Mona Sans. Nada mais.
- Produz: nada que outra tarefa consuma. É a última.

Não há teste automatizado nesta tarefa, e isso é declarado de propósito: o
projeto não tem harness de teste de componente (só testes de lógica em `lib/`,
sem `@testing-library`), e a restrição global proíbe dependência nova. A
verificação é o Passo 4, a olho, por viewport.

- [ ] **Passo 1: reancorar o herói**

Em `dashboard/app/page.tsx`, substitua o `<section>` do herói (linhas 327–405)
mantendo o `CampoDeParticulas`, o `Revelar` e o `GlitchText` como estão. A
mudança é de composição:

```tsx
        {/* O HEROI DE QUINAS, 04/09/2026.

            O QUE ELE ERA: manchete grande alinhada a esquerda, o argumento
            inteiro embaixo dela, dois botoes e uma seta de rolagem, tudo
            centrado verticalmente. Nao estava errado -- estava CONVENCIONAL, e
            era por isso que a pagina lia como landing de produto e nao como as
            referencias fixadas pelo dono do projeto.

            O QUE ELE E AGORA: o centro fica VAZIO, com so o campo de
            particulas, e o conteudo ancora nas quinas -- a licao da
            landonorris.com, onde a primeira tela e quase toda espaco negativo.
            A confianca esta em nao preencher.

            A MARCA NAO SE REPETE AQUI. O <header> fixo logo acima ja a mantem
            na quina superior esquerda durante toda a rolagem, e duplicar seria
            o aparato repetido que a PR #31 acabou de remover em outro lugar.

            A SETA DE ROLAGEM SAIU: ela vivia centralizada na base, onde agora
            esta a acao primaria. Um centro vazio ja convida a rolar. */}
        <section className="relative flex min-h-[92svh] flex-col justify-between">
          <div className="pointer-events-none absolute inset-0 -z-10">
            <CampoDeParticulas />
          </div>

          {/* QUINA SUPERIOR DIREITA. O ponto NAO pisca: indicador pulsante sem
              mudanca de estado por tras e ruido com cara de alerta -- §6. */}
          <div className={`${COLUNA} flex justify-end pt-8 lg:pt-12`}>
            <p className="etiqueta-vitrine inline-flex items-center gap-2.5 text-right text-muted-foreground">
              <span aria-hidden className="size-1.5 rounded-full bg-primary" />
              satisfação inferida · sem pesquisa
            </p>
          </div>

          {/* A BASE. Em telas estreitas as quinas se desfazem numa pilha:
              quina em 390px de largura e um empilhamento com nome pomposo, e o
              espaco negativo que da o efeito nao existe ali para ser gasto. */}
          <div className={`${COLUNA} pb-14 lg:pb-20`}>
            <Revelar className="flex flex-col gap-8 sm:flex-row sm:items-end sm:justify-between sm:gap-12">
              {/* O GLITCH, e so nesta frase. `enableOnHover` porque glitch
                  perpetuo atras de um <h1> e a decoracao-pela-decoracao que o
                  DESIGN.md §6 proibe -- e porque no repouso a frase precisa ser
                  lida sem esforco, ja que ela E a manchete. E <span> dentro do
                  <h1> com texto real, entao busca e leitor de tela recebem a
                  manchete inteira.
                  SEM `.display-aurora` AQUI: background-clip: text recorta TODO
                  o conteudo do elemento, inclusive os filhos -- transformava o
                  🙂 numa bolha branca e apagava o ambar do text-dito-texto, que
                  e o encoding do PRODUCT.md e nao decoracao. */}
              <h1 className="display-vitrine max-w-3xl">
                O cliente escreve{" "}
                <GlitchText
                  enableOnHover
                  speed={0.4}
                  corAntes="var(--medido)"
                  corDepois="var(--emocao)"
                  className="inline text-dito-texto"
                >
                  {"“ok, obrigado 🙂”"}
                </GlitchText>{" "}
                e sai insatisfeito.
              </h1>

              <div className="flex shrink-0 flex-wrap items-center gap-3 sm:pb-2">
                <BotaoEstelar href={acaoPrimaria.href}>
                  {acaoPrimaria.rotulo}
                </BotaoEstelar>
                {!usuario && temLogin && (
                  <Link href="/cadastrar" className={botaoVitrineContorno}>
                    Criar conta
                  </Link>
                )}
              </div>
            </Revelar>
          </div>
        </section>
```

- [ ] **Passo 2: mudar o parágrafo de argumento de seção**

O parágrafo saiu do herói no passo anterior. Ele **não** é descartado: vira a
abertura da seção do artefato, onde passa a legendar a peça que está sendo
mostrada. Na `<section className="relative py-28 lg:py-36">` (linha 436), como
primeiro conteúdo dentro da coluna, antes do que já existe:

```tsx
            {/* O ARGUMENTO, que ate 04/09/2026 morava no heroi. Ele saiu de la
                porque o heroi de quinas vive do espaco negativo -- e ganhou
                com a mudanca: aqui ele LEGENDA o cartao que aparece logo
                abaixo, em vez de disputar largura com a manchete. */}
            <p className="mb-14 max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground">
              A nota declarada mente. O Fraus lê o atendimento inteiro — o que
              foi <span className="text-dito-texto">dito</span> e o que pôde ser{" "}
              <span className="text-medido-texto">medido</span> — e estima a
              satisfação sem perguntar nada.
            </p>
```

Se a seção do artefato não tiver um wrapper com a classe `COLUNA` como primeiro
filho, envolva o parágrafo em `<div className={COLUNA}>` para ele respeitar a
mesma medida do resto da página.

- [ ] **Passo 3: limpar o que ficou órfão**

O `ArrowDown` era usado só pela seta de rolagem removida. Confirme e remova o
import:

```bash
cd dashboard && grep -n "ArrowDown" app/page.tsx
```

Se não houver mais uso, tire `ArrowDown` da lista de imports de `lucide-react` no
topo do arquivo. Se houver, deixe como está.

- [ ] **Passo 4: conferir a olho, por viewport**

```bash
cd dashboard && npm run dev
```

Abra **`http://localhost:3000`** — nunca `127.0.0.1:3000`, que leva 403 nos
chunks do Next 16 em dev; sem chunks não há hidratação, e o estado inicial dos
componentes congela com sintoma idêntico ao de um bug de animação.

Capture **por viewport**, nunca `fullPage`: ele não dispara `whileInView` e não
dá conta de página alta — já devolveu a vitrine em branco uma vez e um vazio
fantasma de ~2.900px em outra. Confira em três larguras:

1. **1440×900** — a manchete ancora embaixo à esquerda, a ação embaixo à direita,
   a etiqueta em cima à direita, e o meio da tela está de fato vazio.
2. **768×1024** — as quinas ainda funcionam, a manchete não colide com a ação.
3. **390×844** — as quinas viraram pilha, a manchete cabe sem estourar, e a ação
   primária está acima da dobra.

Em todas: a Mona Sans está desenhando a manchete (compare com o antes — o `a` e
o `g` mudam de forma), o âmbar da frase citada continua âmbar, e o 🙂 continua
colorido e não virou bolha branca.

- [ ] **Passo 5: rodar os gates**

```bash
cd dashboard && npm test && npm run contraste && npm run lint && npm run build
```

Esperado: tudo verde.

- [ ] **Passo 6: commit**

```bash
git add dashboard/app/page.tsx
git commit -m "feat(vitrine): heroi ancorado nas quinas, com o centro vazio"
```

---

## Auto-revisão

**Cobertura da spec.** §1 (tipografia) → Tarefa 1, passos 1–7, incluindo a emenda
ao `DESIGN.md` que a spec pede nominalmente. §2 (herói) → Tarefa 2: composição de
quinas no passo 1, migração do parágrafo no passo 2, remoção da seta no passo 1
com a limpeza do import no passo 3, telas estreitas no passo 1 (`sm:` na pilha) e
conferidas no passo 4. §3 (invariantes) → o `<h1>` continua texto real e sem
`background-clip`, e nenhum passo toca token de cor. §4 (verificação) → passo 8
da Tarefa 1 e passos 4–5 da Tarefa 2.

**Placeholders.** Nenhum TBD, nenhum "similar à tarefa anterior", nenhum passo
sem o código que ele pede. Os dois pontos de incerteza real estão nomeados com o
que fazer em cada ramo: o nome interno do zip da fonte (Tarefa 1, passo 1) e o
wrapper de coluna da seção do artefato (Tarefa 2, passo 2).

**Consistência de nomes.** `--fonte-mona` é a variável que o `next/font/local`
expõe; `--fonte-display` é o token que a empilha com fallback; as duas classes
são `.display-vitrine` e `.titulo-vitrine`, escritas assim no teste, no CSS, no
`DESIGN.md` e nos dois passos que as editam.
