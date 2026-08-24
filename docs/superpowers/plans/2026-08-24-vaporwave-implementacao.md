# Vaporwave assumido — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levar os dois temas do Fraus a um vaporwave assumido — grade a laser e sol listrado no ateliê, chanfro e glow no chassi, camada de dado em neon com matiz travado — sem afrouxar o portão de contraste.

**Architecture:** Três camadas, na ordem em que o custo de contraste sobe. O ateliê (papel de parede) ganha peças novas em `Atelier.tsx`, cada uma com seu par de tokens por tema. O chassi muda por token único (`--radius`) e por classe de vidro. A camada de dado é repintada com o matiz de cada família congelado e o croma/claridade subindo até onde `npm run contraste` deixar. Toda luz nova obriga a remedir os pisos de vidro com `npm run pisos` — é a última tarefa antes das emendas de documento, de propósito.

**Tech Stack:** Next.js + Tailwind v4 (tokens em `app/globals.css`), CSS puro para toda a decoração (zero dependência nova, zero animação), Node para os dois gates (`scripts/contraste.mjs`, `scripts/pisos.mjs`).

## Global Constraints

Copiadas da spec e das invariantes do `CLAUDE.md`. Valem para **toda** tarefa.

- **Sem animação.** A §6 do `DESIGN.md` já gastou os dois momentos de movimento da interface. Toda peça nova é estática.
- **Zero dependência nova.** Tudo em CSS puro.
- **Identificadores e nomes de token em português sem acento** (`--grade-horizonte`, `--sol-faixa`). Texto de interface leva acento normal.
- **Commits em português, sem acento, no formato `tipo(escopo): resumo`.**
- **O matiz de cada família de dado NÃO se move.** Só croma e claridade.
- **`--primary` nunca toca dado.** Regra da §3.3.
- **O portão nunca é afrouxado.** Par que reprova faz a espessura do vidro ganhar opacidade — nunca o contrário. Teto de 90%: passou disso, quem cede é a peça nova (spec §6).
- **Piso otimista é pior que piso nenhum.** `npm run pisos` manda; o valor no CSS tem que ser `>=` o medido.
- **O `globals.css` está em CRLF.** Casar seletor por string literal falha; use regex ou `Edit` com contexto exato.
- **A cada tarefa que acende luz:** rodar `npm run pisos` e `npm run contraste` antes do commit.

**Verificação padrão de fim de tarefa** (referida adiante como *o ciclo*):

```bash
cd dashboard
npm run pisos          # nenhum "OTIMISTA -- corrigir"
npm run contraste      # verde nos dois temas
npx tsc --noEmit       # limpo
npm run lint           # limpo
```

---

## Estrutura de arquivos

| Arquivo | Responsabilidade | Tarefas |
|---|---|---|
| `dashboard/app/globals.css` | todos os tokens dos dois temas | 1–8 |
| `dashboard/components/shell/Atelier.tsx` | camada 0: toda a decoração de fundo | 1, 2 |
| `dashboard/scripts/pisos.mjs` | medição do pior caso; ganha as camadas novas | 1, 2 |
| `dashboard/scripts/contraste.mjs` | o portão; ganha os três tokens `-rich-text` | 6 |
| `dashboard/DESIGN.md` | emendas §3.1, §3.3.1, §8.2, §8.5 | 9 |

Nenhum arquivo novo. Nenhum componente de dado é tocado — a repintura da §5 é toda por token.

---

### Task 1: A grade a laser

**Files:**
- Modify: `dashboard/app/globals.css` (bloco `:root, .dark` e bloco `.tema-chuva`)
- Modify: `dashboard/components/shell/Atelier.tsx` (nova camada, depois do reflexo no asfalto)
- Modify: `dashboard/scripts/pisos.mjs` (a grade entra na lista de alternativas do terço de baixo)

**Interfaces:**
- Consumes: nada de tarefas anteriores.
- Produces: os tokens `--grade-cor`, `--grade-op`, `--grade-espaco`, `--grade-horizonte`, declarados nos dois temas. A Task 2 e a Task 8 dependem de `--grade-op` existir e ser lido por `pisos.mjs`.

**Contexto que o implementador precisa:** o ateliê é `Atelier.tsx`, um `fixed inset-0 -z-10` com camadas empilhadas na ordem do DOM. O padrão estabelecido é: **a peça existe no componente nos dois temas e o TEMA decide a opacidade.** O grafite zera o que não quer — mas nesta spec ele NÃO zera a grade, porque a decisão foi estrutura igual nos dois.

- [ ] **Step 1: Declarar os tokens no tema grafite**

Em `app/globals.css`, no bloco `:root, .dark`, logo depois do bloco `--marca-cor` / `--marca-op`:

```css
  /* --- A GRADE A LASER ---------------------------------------------------
     O chão da cena: linhas fugindo ao ponto de fuga mais linhas horizontais
     comprimindo com a distância. É o elemento mais reconhecível do
     vocabulário synthwave, e é CSS puro -- dois `repeating-linear-gradient`
     num plano rotacionado, não mil elementos.

     ESTÁTICA, pelo mesmo motivo que a chuva não cai: a seção 6 do DESIGN.md
     já gastou os dois momentos de movimento da interface, e grade animada
     seria um terceiro que não comunica estado nenhum.

     Mora no TERÇO DE BAIXO, e isso é o que a torna barata: a máscara do papel
     pautado já zerou ali. Ver o comentário de `scripts/pisos.mjs` sobre
     alternativas disjuntas.

     Emenda de 24/08/2026 à seção 3.1 -- ver DESIGN.md. */
  --grade-cor: oklch(0.81 0.1 82);
  --grade-op: 0.1;
  --grade-espaco: 44px;
  --grade-horizonte: 320px;
```

- [ ] **Step 2: Declarar os tokens no tema chuva**

No bloco `.tema-chuva`, logo depois de `--marca-cor` / `--marca-op`:

```css
  /* A GRADE vira tubo de ciano, o par do magenta da marca. Mais forte que no
     grafite pelo mesmo motivo de todas as luzes deste tema: ela compete com
     um ateliê aceso. */
  --grade-cor: oklch(0.85 0.16 205);
  --grade-op: 0.2;
```

- [ ] **Step 3: Desenhar a camada no Atelier.tsx**

Em `components/shell/Atelier.tsx`, **depois** do bloco do reflexo no asfalto e **antes** do bloco da chuva diagonal. Cole exatamente:

```tsx
      {/* A GRADE A LASER: o chão da cena.

          A perspectiva é o truque inteiro. Um plano com duas famílias de
          linha -- uma correndo para o fundo, outra atravessando -- rotacionado
          em `rotateX` com `transformOrigin` no rodapé. As linhas que correm
          para o fundo CONVERGEM sozinhas, porque a projeção em perspectiva faz
          isso; não há gradiente cônico nem SVG envolvido.

          `inset-x-[-50%]` e não `inset-x-0`: rotacionado, o plano encolhe na
          horizontal perto do horizonte e mostraria borda se tivesse a largura
          da tela. Sangrar meia tela para cada lado resolve sem custo.

          A máscara apaga a grade subindo, para ela virar horizonte em vez de
          parar numa linha reta -- que leria como o fim de uma textura, e não
          como distância.

          ESTÁTICA. Ver o comentário da chuva logo abaixo sobre por que. */}
      <div
        className="absolute inset-x-[-50%] bottom-0 h-[55vh]"
        style={{
          opacity: "var(--grade-op)",
          background:
            "repeating-linear-gradient(to right, var(--grade-cor) 0 1px, transparent 1px var(--grade-espaco))," +
            "repeating-linear-gradient(to bottom, var(--grade-cor) 0 1px, transparent 1px var(--grade-espaco))",
          transform:
            "perspective(var(--grade-horizonte)) rotateX(74deg)",
          transformOrigin: "bottom center",
          maskImage: "linear-gradient(to top, black 0%, transparent 92%)",
          WebkitMaskImage: "linear-gradient(to top, black 0%, transparent 92%)",
        }}
      />
```

- [ ] **Step 4: Ensinar o pisos.mjs a ver a grade**

Em `scripts/pisos.mjs`, dentro do laço `for (const tema of temas)`, o array `alternativas` hoje tem duas entradas. Ele passa a ter três:

```js
  const alternativas = [
    ["papel pautado", cor("--pauta-cor"), op("--pauta-op")],
    ["marca impressa", cor("--marca-cor"), op("--marca-op")],
    ["grade a laser", cor("--grade-cor"), op("--grade-op")],
  ];
```

O resto do arquivo não muda: ele já compõe cada alternativa e escolhe a mais clara. Atualize o comentário logo acima do array para nomear a grade junto com as outras duas — o comentário explica que as máscaras são disjuntas, e agora são três.

- [ ] **Step 5: Medir**

Run: `cd dashboard && npm run pisos`

Esperado: a linha `atelie composto (pior caso, com "...")` continua dizendo **"papel pautado"** nos dois temas. Se disser "grade a laser", a grade passou do teto de graça — **baixe `--grade-op`** em passos de 0,01 até o papel voltar a vencer, e registre no comentário do token qual foi o teto encontrado.

- [ ] **Step 6: Rodar o ciclo**

Run: `npm run pisos && npm run contraste && npx tsc --noEmit && npm run lint`
Esperado: nenhum `OTIMISTA`, portão verde nos dois temas, tsc e lint limpos.

- [ ] **Step 7: Ver no navegador**

Suba `npm run dev` e abra `http://localhost:3000/configuracoes` (tela com calhas de fundo visíveis). Alterne o tema pelo seletor no rodapé da sidebar. A grade tem que **ler como chão**, não como tabela: as linhas verticais convergem, as horizontais adensam subindo. Se ler como grade chapada, `--grade-horizonte` está alto demais — baixe para 240px.

- [ ] **Step 8: Commit**

```bash
git add dashboard/app/globals.css dashboard/components/shell/Atelier.tsx dashboard/scripts/pisos.mjs
git commit -m "feat(atelie): a grade a laser vira o chao da cena nos dois temas"
```

---

### Task 2: O sol listrado

**Files:**
- Modify: `dashboard/app/globals.css` (os dois blocos de tema)
- Modify: `dashboard/components/shell/Atelier.tsx:85-93` (a mancha quente vira o sol)
- Modify: `dashboard/scripts/pisos.mjs` (o sol substitui a mancha quente na composição)

**Interfaces:**
- Consumes: da Task 1, `--grade-horizonte` — o sol é posicionado para nascer na linha do horizonte da grade.
- Produces: `--sol-cor-alta`, `--sol-cor-baixa`, `--sol-op`, `--sol-faixa` nos dois temas. A Task 8 depende de `--sol-op` ser lido por `pisos.mjs`.

**Contexto:** hoje existe uma "mancha quente fraca" em `Atelier.tsx` — um círculo borrado em `left-[45%] top-[55%]`, cuja função declarada é *quebrar a simetria das outras duas manchas*. **Ela não é apagada: ela vira o sol.** Isso preserva a função original (quebra de simetria) e evita somar uma camada nova ao pior caso.

- [ ] **Step 1: Declarar os tokens no tema grafite**

No bloco `:root, .dark`, depois dos tokens da grade:

```css
  /* --- O SOL LISTRADO ----------------------------------------------------
     O retrosun: disco com faixas horizontais, nascendo na linha do horizonte
     da grade.

     NÃO É PEÇA NOVA. É a "mancha quente fraca" que já existia no ateliê --
     cuja função declarada era quebrar a simetria das outras duas manchas --
     ganhando borda e faixas. A função antiga sobrevive; o que muda é a forma.
     Peça nova somaria luz ao pior caso; esta não soma.

     No grafite ele é a lâmpada de SÓDIO do poste, que a seção 8.1 já
     estabeleceu como a leitura que reconcilia o dourado da marca com o neon
     frio -- e é por isso que ele é âmbar aqui e magenta na chuva. */
  --sol-cor-alta: oklch(0.86 0.11 88);
  --sol-cor-baixa: oklch(0.7 0.13 52);
  --sol-op: 0.16;
  --sol-faixa: 9px;
```

- [ ] **Step 2: Declarar os tokens no tema chuva**

No bloco `.tema-chuva`, depois dos tokens da grade:

```css
  /* O RETROSUN canônico: amarelo-coral em cima, magenta embaixo. */
  --sol-cor-alta: oklch(0.85 0.17 75);
  --sol-cor-baixa: oklch(0.66 0.25 350);
  --sol-op: 0.3;
```

- [ ] **Step 3: Trocar a mancha quente pelo sol**

Em `components/shell/Atelier.tsx`, substitua **todo** o bloco da mancha quente (o comentário `{/* quente fraca -- quebra a simetria das outras duas */}` mais o `<div>` que o segue) por:

```tsx
      {/* O SOL LISTRADO: o retrosun, nascendo no horizonte da grade.

          Herda o posto da antiga "mancha quente fraca", e de propósito: a
          função dela era quebrar a simetria das outras duas manchas, e um
          disco fora do eixo faz isso melhor que um borrão. Peça nova somaria
          luz ao pior caso das superfícies translúcidas; esta apenas troca de
          forma.

          As faixas são `repeating-linear-gradient` sobre o gradiente do
          disco, cortadas pelo `rounded-full` -- o disco é a máscara, as
          faixas são o preenchimento. Elas ENGROSSAM descendo porque é assim
          que o retrosun se lê: sol se pondo, não bola listrada.

          Fica ATRÁS da grade na ordem do DOM: o sol se põe no horizonte, e o
          chão está na frente dele. */}
      <div
        className="absolute bottom-[26vh] left-[52%] h-[38vmin] w-[38vmin] -translate-x-1/2 rounded-full blur-[2px]"
        style={{
          opacity: "var(--sol-op)",
          background:
            "repeating-linear-gradient(to bottom, transparent 0 var(--sol-faixa), oklch(0 0 0 / 0.85) var(--sol-faixa) calc(var(--sol-faixa) * 1.5))," +
            "linear-gradient(to bottom, var(--sol-cor-alta), var(--sol-cor-baixa))",
          maskImage: "linear-gradient(to bottom, black 55%, transparent 96%)",
          WebkitMaskImage:
            "linear-gradient(to bottom, black 55%, transparent 96%)",
        }}
      />
```

**Atenção à ordem:** este bloco tem que ficar **antes** do bloco da grade a laser criado na Task 1. Se a Task 1 já foi aplicada, mova o bloco do sol para cima dela.

- [ ] **Step 4: Ensinar o pisos.mjs a ver o sol**

Em `scripts/pisos.mjs`, dentro de `compor`, a linha da mancha quente:

```js
      ["mancha quente", cor("--atelie-quente"), op("--atelie-op-quente")],
```

vira:

```js
      // O sol listrado herdou o posto da mancha quente (ver Atelier.tsx). A
      // cor medida e a ALTA do gradiente: e a mais clara das duas, e piso
      // otimista e pior que piso nenhum.
      ["sol listrado", cor("--sol-cor-alta"), op("--sol-op")],
```

- [ ] **Step 5: Rodar o ciclo**

Run: `npm run pisos && npm run contraste && npx tsc --noEmit && npm run lint`

Se `npm run contraste` reprovar, **não mexa no portão**: vá para a Task 8 mentalmente — a espessura do vidro é quem cede. Mas registre aqui qual par caiu e para quanto, porque a Task 8 vai precisar do número.

- [ ] **Step 6: Ver no navegador**

Alterne os dois temas em `/configuracoes`. O sol tem que ler como **disco listrado se pondo**, com as faixas se apagando para baixo. Se as faixas sumirem, `--sol-faixa` está pequeno demais para o tamanho do disco — suba para 12px.

- [ ] **Step 7: Commit**

```bash
git add dashboard/app/globals.css dashboard/components/shell/Atelier.tsx dashboard/scripts/pisos.mjs
git commit -m "feat(atelie): a mancha quente vira o sol listrado no horizonte"
```

---

### Task 3: Os cantos duros

**Files:**
- Modify: `dashboard/app/globals.css:199` (`--radius`)

**Interfaces:**
- Consumes: nada.
- Produces: nada que outras tarefas consumam. Independente — pode ser aceita ou rejeitada sozinha.

**Contexto que decide esta tarefa:** a §3.3.1 do `DESIGN.md` diz que `--radius` caiu de `0.625rem` para `0.375rem` porque "o F e o R são chanfrados a 45° e não têm uma curva de canto sequer", e que **não foi a zero** só para não brigar com o resto do chassi. Toda a escala (`--radius-sm` a `--radius-4xl`) deriva desse único token por `calc()`, então esta é uma mudança de **uma linha** que muda o caráter de toda superfície.

- [ ] **Step 1: Baixar o raio**

Em `app/globals.css`, linha ~199:

```css
  --radius: 0.375rem;
```

vira:

```css
  /* 2px, e não zero. A seção 3.3.1 já argumentava nesta direção -- o F e o R
     são chanfrados a 45° e não têm uma curva de canto sequer -- e só parou em
     0.375rem para o controle não brigar com um chassi arredondado. Com o
     chassi inteiro endurecendo, a objeção deixa de existir.
     Não vai a zero porque canto absolutamente vivo serrilha em tela não-HiDPI
     e o chanfro da marca é um corte, não uma quina. Emenda de 24/08/2026 à
     seção 3.3.1 -- ver DESIGN.md. */
  --radius: 0.125rem;
```

- [ ] **Step 2: Rodar o ciclo**

Run: `npm run contraste && npx tsc --noEmit && npm run lint`
Esperado: verde. Raio não altera luminância, então `npm run pisos` não pode ter mudado — rode mesmo assim para confirmar que não mudou.

- [ ] **Step 3: Ver no navegador**

Percorra `/`, `/atendimentos`, `/configuracoes` nos dois temas. Procure especificamente por: badge de categoria de NPS, botão primário, campo de data, cabeçalho de tabela. Nenhum deles pode ter ganhado serrilhado nem perdido a borda.

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/globals.css
git commit -m "feat(chassi): o canto endurece para 2px, como os cortes do monograma"
```

---

### Task 4: O glow no grafite, e as réguas acesas

**Files:**
- Modify: `dashboard/app/globals.css` (bloco `:root, .dark`: `--vidro-sombra`, `--linha`, `--compasso`, `--vidro-quina`, `--vidro-quina-baixa`)

**Interfaces:**
- Consumes: nada.
- Produces: nada que outras tarefas consumam.

**Contexto:** o tema chuva já trocou sombra preta por derrame violeta e já acendeu a quina em ciano/magenta. O grafite ficou para trás com `oklch(0 0 0 / 20%)` — sombra preta sob um painel que flutua sobre luz lê como buraco. Esta tarefa leva a mesma ideia ao grafite, **na cor dele**: ouro fosco, não magenta.

- [ ] **Step 1: Trocar a sombra do grafite**

No bloco `:root, .dark`:

```css
  --vidro-sombra: 0 1px 2px oklch(0 0 0 / 20%), 0 8px 24px oklch(0 0 0 / 28%);
```

vira:

```css
  /* GLOW, não buraco. Sombra preta sob um painel que flutua sobre a luz do
     ateliê lê como recorte no papel; um halo quente lê como a luz da própria
     superfície vazando para baixo. É a mesma ideia que o tema chuva já
     aplicou em violeta, agora na cor deste tema -- ouro FOSCO, croma 0.06,
     porque aqui ele é luz de escritório e não neon de fachada. */
  --vidro-sombra: 0 1px 2px oklch(0.12 0.02 80 / 28%),
    0 8px 26px oklch(0.42 0.06 80 / 22%);
```

- [ ] **Step 2: Acender as réguas e as quinas do grafite**

No mesmo bloco, os quatro tokens:

```css
  --vidro-quina: oklch(1 0 0 / 12%);
  --vidro-quina-baixa: oklch(0 0 0 / 20%);
```

viram:

```css
  /* A quina sobe junto com o resto: é ela que faz a superfície parecer vidro
     em vez de plástico fosco, e acender a aresta acende a interface inteira
     sem uma célula de dado mudar de cor. Continua BRANCA no grafite -- aqui
     ela é reflexo de luz de escritório, e reflexo não tem cor própria. */
  --vidro-quina: oklch(1 0 0 / 20%);
  --vidro-quina-baixa: oklch(0 0 0 / 26%);
```

E os dois da régua, nas linhas 265 e 268 do bloco base:

```css
  --linha: oklch(1 0 0 / 24%);
  --compasso: oklch(1 0 0 / 8%);
```

viram:

```css
  /* A régua sobe junto com a quina. Ela continua sendo a única linha que
     AFIRMA alguma coisa -- o papel pautado do ateliê é papel, esta é medida --
     e por isso ela tem que continuar mais forte que o papel, que subiu para
     0.12 em 24/08/2026. Era 24% e 8%. */
  --linha: oklch(1 0 0 / 34%);
  --compasso: oklch(1 0 0 / 12%);
```

**Não toque nas linhas 543–544**, que são as mesmas duas no bloco `.tema-chuva` — aquele tema já as acendeu.

- [ ] **Step 3: Rodar o ciclo**

Run: `npm run pisos && npm run contraste && npx tsc --noEmit && npm run lint`

Sombra e quina são desenhadas **sobre** o vidro, não atrás dele, então `npm run pisos` não deve mudar. Se mudar, algo foi editado no lugar errado.

- [ ] **Step 4: Ver no navegador**

No grafite, os painéis têm que ganhar um halo quente perceptível embaixo. Compare lado a lado com o commit anterior (`git stash` / `git stash pop`) se estiver em dúvida — a diferença é sutil e real.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/globals.css
git commit -m "feat(chassi): o grafite troca sombra preta por glow e acende as reguas"
```

---

### Task 5: O chanfro a 45° no vidro

**Files:**
- Modify: `dashboard/app/globals.css` (o bloco `@layer components` das classes `.vidro-*`)

**Interfaces:**
- Consumes: da Task 3, o `--radius` já reduzido (o chanfro convive com raio pequeno, brigaria com raio grande). Da Task 4, os valores finais de `--vidro-sombra` nos dois temas — **é por isso que esta tarefa vem depois dela**: os `drop-shadow()` abaixo repetem esses valores à mão, e se a Task 4 ainda não tivesse rodado eles congelariam a sombra preta antiga, deixando painel com chanfro preto ao lado de painel sem chanfro dourado.
- Produces: nada que outras tarefas consumam.

**Antes de colar o CSS abaixo, confira** que `--vidro-sombra` no bloco `:root, .dark` e no bloco `.tema-chuva` bate com os valores repetidos nos `drop-shadow()`. Se a Task 4 tiver ajustado a sombra para outro valor, use o que está no CSS — o arquivo manda, não este plano.

**Contexto e o risco real:** `clip-path` **descarta `box-shadow`** — o navegador recorta o elemento inteiro, sombra inclusive. Como o glow do vidro é `box-shadow` (`--vidro-sombra`), aplicar chanfro ingenuamente **apaga o glow**, que é justamente o que a Task 5 vai reforçar. A saída é mover a sombra para `filter: drop-shadow()` no mesmo elemento, que segue o recorte. `drop-shadow` só aceita UMA sombra por função, então as duas camadas de `--vidro-sombra` viram duas funções encadeadas.

**Esta tarefa é a mais rejeitável do plano.** Se o resultado visual não convencer no Step 4, **descarte-a inteira** — a Task 3 sozinha já entrega o canto duro, e o chanfro é o requinte.

- [ ] **Step 1: Localizar o bloco das classes de vidro**

Run: `grep -n "\.vidro-fino," dashboard/app/globals.css`

Você vai cair no `@layer components` onde `.vidro-fino`, `.vidro` e `.vidro-denso` são definidas, com `background-color`, `backdrop-filter` e `box-shadow: var(--vidro-sombra)`.

- [ ] **Step 2: Adicionar a classe do chanfro**

Logo **depois** das três definições de vidro, no mesmo `@layer components`:

```css
  /* O CHANFRO A 45°, recortado do monograma.

     Por que `clip-path` e não `border-radius`: raio é curva, e o F e o R não
     têm uma curva de canto sequer (seção 3.3.1). Chanfro é corte reto, que é
     a geometria da marca.

     ARMADILHA PAGA: `clip-path` DESCARTA `box-shadow` -- o recorte come o
     elemento inteiro, sombra inclusive. Por isso a sombra sai de `box-shadow`
     e vira `drop-shadow`, que segue o recorte. `drop-shadow` aceita uma
     sombra por função, então as duas camadas do `--vidro-sombra` viram duas
     funções encadeadas, e os valores estão repetidos aqui de propósito: o
     token é uma lista de `box-shadow` e não pode ser interpolado dentro de
     `drop-shadow()`.

     Só nas superfícies GRANDES. Chanfro em badge de 18px de altura come o
     rótulo. */
  .chanfro {
    --chanfro: 10px;
    clip-path: polygon(
      var(--chanfro) 0,
      100% 0,
      100% calc(100% - var(--chanfro)),
      calc(100% - var(--chanfro)) 100%,
      0 100%,
      0 var(--chanfro)
    );
    box-shadow: none;
    filter: drop-shadow(0 1px 2px oklch(0.12 0.02 80 / 28%))
      drop-shadow(0 8px 26px oklch(0.42 0.06 80 / 22%));
  }

  .tema-chuva .chanfro {
    filter: drop-shadow(0 1px 2px oklch(0.08 0.04 300 / 34%))
      drop-shadow(0 10px 34px oklch(0.42 0.2 315 / 26%));
  }
```

- [ ] **Step 3: Aplicar nas superfícies grandes**

Run: `grep -rn "vidro-denso\|className=\"vidro\b" dashboard/components --include=*.tsx | head -20`

Adicione `chanfro` ao `className` **apenas** de painéis e cartões de página inteira (os que usam `vidro` ou `vidro-denso`). **Não** aplique em: badge, botão, campo de formulário, célula de tabela, nem em nada com `vidro-fino`.

- [ ] **Step 4: Ver no navegador — e este é o gate desta tarefa**

Abra `/` e `/configuracoes` nos dois temas. Confira **as duas coisas**:
1. o chanfro aparece nas quinas superior-esquerda e inferior-direita dos painéis;
2. **o glow embaixo dos painéis continua lá.** Se sumiu, o `drop-shadow` não pegou — revise o Step 2.

Se o resultado ficar ruidoso (muitos cantos cortados competindo), **descarte esta tarefa** com `git checkout` e siga para a Task 5. O plano segue de pé sem ela.

- [ ] **Step 5: Rodar o ciclo**

Run: `npm run pisos && npm run contraste && npx tsc --noEmit && npm run lint`

- [ ] **Step 6: Commit**

```bash
git add dashboard/app/globals.css dashboard/components
git commit -m "feat(chassi): o chanfro a 45 graus recorta os paineis de vidro"
```

---

### Task 6: As nove cores que o portão não enxerga

**Files:**
- Modify: `dashboard/app/globals.css:181-189`
- Modify: `dashboard/scripts/contraste.mjs` (lista `textos`)

**Interfaces:**
- Consumes: nada.
- Produces: os três tokens `--destructive-rich-text`, `--success-rich-text`, `--warning-rich-text` medidos pelo portão. **A Task 7 depende desta**: repintar o dado sem isto deixaria três cores de texto cegas.

**Contexto:** `scripts/contraste.mjs` só faz parse de `oklch(L C H)` literal — está escrito no comentário da função `lerTokens`, e é deliberado, para que piso escrito com `color-mix` não passe em silêncio. O efeito colateral é que **nove tokens em `hsl()` são invisíveis para o gate**, e três deles carregam texto: `AvisoApiFora.tsx`, `EstadoSaude.tsx`, `TextoComPesos.tsx`, `MetricasTreino.tsx`, `ReguaDeCamadas.tsx`, `Analisador.tsx`. O rosa de `--destructive-rich-text` sobre o índigo da chuva **já foi confirmado ilegível numa captura de tela**.

- [ ] **Step 1: Converter os nove para oklch**

Em `app/globals.css`, linhas 181–189, substitua o bloco inteiro por:

```css
  /* CONVERTIDOS de hsl() para oklch() em 24/08/2026, e a conversão é
     matematicamente equivalente -- mesma cor, outra notação.

     O motivo não é estético: `scripts/contraste.mjs` só faz parse de
     `oklch()` literal, de propósito (ver o comentário de `lerTokens`), então
     estes nove eram INVISÍVEIS para o portão. Três deles carregam texto e
     nunca foram medidos, em tema nenhum -- e o rosa de
     `--destructive-rich-text` sobre o índigo do tema chuva foi confirmado
     ilegível numa captura de tela. Convertidos, o gate passa a enxergá-los
     sem uma linha de mudança no script. */
  --destructive-rich: oklch(0.199 0.064 23);
  --destructive-rich-border: oklch(0.27 0.103 25.5);
  --destructive-rich-text: oklch(0.799 0.116 17.8);
  --success-rich: oklch(0.209 0.049 158.3);
  --success-rich-border: oklch(0.316 0.083 152.3);
  --success-rich-text: oklch(0.862 0.169 157.8);
  --warning-rich: oklch(0.228 0.051 113.3);
  --warning-rich-border: oklch(0.291 0.063 109.8);
  --warning-rich-text: oklch(0.864 0.142 92.2);
```

- [ ] **Step 2: Pôr os três `-text` na lista do portão**

Em `scripts/contraste.mjs`, no array `textos`, depois de `"--destructive",`:

```js
  // Os tres `-rich-text` estavam CEGOS para este gate ate 24/08/2026: eram
  // escritos em `hsl()` e o parser so le `oklch()` literal. Carregam texto em
  // AvisoApiFora, EstadoSaude, TextoComPesos, MetricasTreino, ReguaDeCamadas
  // e Analisador -- e nunca foram medidos, em tema nenhum.
  "--destructive-rich-text",
  "--success-rich-text",
  "--warning-rich-text",
```

- [ ] **Step 3: Rodar o portão e ESPERAR que reprove**

Run: `cd dashboard && npm run contraste`

Esperado: **FAIL**. Este é o passo mais importante da tarefa — o gate está enxergando pela primeira vez três cores que ninguém mediu. Anote cada par reprovado e a razão exata.

Se passar de primeira, ótimo, mas confirme que os três nomes aparecem no relatório (`npm run contraste | grep rich`) — passar por não estar sendo medido seria o mesmo bug de novo.

- [ ] **Step 4: Corrigir as cores reprovadas, mantendo o matiz**

Para cada par reprovado, suba a **claridade** (o primeiro número do `oklch`) em passos de 0,02, **sem tocar no matiz** (o terceiro número). Repita `npm run contraste` até verde.

Estes são tokens de estado (erro, sucesso, aviso), não das sete famílias de sinal — mas o matiz continua carregando o significado (vermelho = erro), então ele fica.

- [ ] **Step 5: Rodar o ciclo**

Run: `npm run pisos && npm run contraste && npx tsc --noEmit && npm run lint`

- [ ] **Step 6: Ver no navegador**

Abra `/analisar` (usa `TextoComPesos`, verde e vermelho sobre o texto) e `/modelo` (usa `MetricasTreino`, âmbar) **nos dois temas**. Confirme com o olho que o texto está legível — especialmente o vermelho sobre o índigo da chuva, que é o caso confirmado quebrado.

- [ ] **Step 7: Commit**

```bash
git add dashboard/app/globals.css dashboard/scripts/contraste.mjs
git commit -m "fix(contraste): o portao passa a enxergar as nove cores em hsl"
```

---

### Task 7: A camada de dado em neon, com o matiz travado

**Files:**
- Modify: `dashboard/app/globals.css:272-334` (sete famílias, NPS, e os nove nós do grafo)

**Interfaces:**
- Consumes: da Task 6, o portão medindo os nove tokens que estavam cegos.
- Produces: nada que outras tarefas consumam. A Task 8 remede os pisos depois desta.

**A regra desta tarefa, e ela não admite exceção:** **o terceiro número do `oklch()` — o matiz — não muda em token nenhum.** Sobem o primeiro (claridade) e o segundo (croma). O matiz é o que carrega o significado; quem aprendeu a cor num print do trabalho tem que continuar lendo no outro.

Os tokens `-fraco` são `color-mix` do token base e acompanham sozinhos — **não os edite**.

- [ ] **Step 1: Repintar as sete famílias**

Em `app/globals.css`, substitua os valores (mantendo os comentários que já existem em cada bloco):

```css
  --dito: oklch(0.83 0.19 60);
  --dito-texto: oklch(0.87 0.17 60);

  --medido: oklch(0.74 0.2 265);
  --medido-texto: oklch(0.81 0.18 265);

  --emocao: oklch(0.75 0.21 10);
  --emocao-texto: oklch(0.82 0.19 10);

  --lexico: oklch(0.79 0.19 140);
  --lexico-texto: oklch(0.85 0.17 140);

  --ironia: oklch(0.75 0.19 230);
  --ironia-texto: oklch(0.83 0.17 230);

  --estilo: oklch(0.79 0.19 170);
  --estilo-texto: oklch(0.85 0.17 170);

  --tempo: oklch(0.76 0.19 320);
  --tempo-texto: oklch(0.83 0.17 320);
```

Confira token a token: o terceiro número é idêntico ao que estava lá antes. 60, 265, 10, 140, 230, 170, 320.

- [ ] **Step 2: Repintar a escala de NPS**

```css
  --detrator: oklch(0.67 0.24 22);
  --detrator-texto: oklch(0.78 0.2 22);
  --neutro: oklch(0.78 0.15 90);
  --neutro-texto: oklch(0.85 0.14 90);
  --promotor: oklch(0.79 0.18 190);
  --promotor-texto: oklch(0.85 0.16 190);
```

Matizes preservados: 22, 90, 190.

- [ ] **Step 3: Repintar os nove nós do grafo**

Os oito nós coloridos compartilham `L 0.75 / C 0.14` **de propósito** — o comentário no arquivo explica que claridade igual impede hierarquia acidental, já que nenhum tipo de nó é mais importante que outro. **Essa regra continua valendo:** suba os dois juntos, mantendo todos iguais.

Troque `oklch(0.75 0.14 <matiz>)` por `oklch(0.79 0.19 <matiz>)` nos oito, preservando cada matiz (60, 95, 30, 265, 305, 195, 340, 150).

`--no-importacao` é cinza e **não muda**: o comentário diz que é a exceção semântica — importação é nó solto e cinza é a ausência de afirmação. Croma zero continua sendo croma zero.

- [ ] **Step 4: Rodar o portão**

Run: `cd dashboard && npm run contraste`

Para cada par reprovado: **suba a claridade** do token, nunca mexa no matiz, nunca afrouxe o gate. Se um token não couber no neon que a spec pede, **pare onde couber** e anote no comentário do token qual foi o teto e contra qual fundo — a spec §5.2 exige que isso seja reportado, não escondido.

- [ ] **Step 5: Rodar o ciclo**

Run: `npm run pisos && npm run contraste && npx tsc --noEmit && npm run lint`

- [ ] **Step 6: Ver no navegador, e este gate é de olho**

Abra `/` (distribuição de notas, série temporal), `/atendimentos` (tabela com badges), `/modelo` (as sete famílias em `PesosFeatures` e `BarrasDeFeature`) e `/grafo` (os nove tipos de nó), **nos dois temas**.

Duas coisas que o cálculo não pega:
1. **Figura contra fundo por matiz.** `--medido` é matiz 265 e o fundo da chuva é 274 — azul sobre chão azul. Cruza contraste com folga e ainda assim pode custar para separar. Se o olho reprovar, ajuste croma e claridade **mantendo o matiz**.
2. **As sete famílias continuam distinguíveis entre si?** Croma alto aproxima cores vizinhas. `--lexico` (140) e `--estilo` (170) são o par mais próximo — olhe especificamente para eles em `BarrasDeFeature`.

- [ ] **Step 7: Commit**

```bash
git add dashboard/app/globals.css
git commit -m "feat(dado): as sete familias e o NPS em neon, com o matiz travado"
```

---

### Task 8: Remedir os pisos e engrossar o vidro

**Files:**
- Modify: `dashboard/app/globals.css` (`--vidro-*-piso` e `--vidro-*-fundo` nos dois temas)

**Interfaces:**
- Consumes: todas as tarefas anteriores que acenderam luz (1, 2, 5).
- Produces: os pisos honestos que o portão mede.

**Contexto — a regra que governa esta tarefa inteira:** toda luz nova levanta o pior caso das superfícies translúcidas. `npm run pisos` diz qual é o piso real; o valor no CSS tem que ser **maior ou igual** a ele. Piso otimista faz o portão devolver verde medindo uma superfície que não existe.

Quando o portão reprova: **a espessura do vidro ganha opacidade.** O portão nunca é afrouxado, e baixar a luz para salvar contraste é resolver pelo lado errado.

**O teto, e ele é desta spec:** se uma espessura passar de **90%**, quem cede é a peça nova — vidro a 90% não é vidro, e o reskin inteiro morreria para proteger uma superfície que quase ninguém vê. Nesse caso, volte à tarefa da peça e baixe a opacidade dela, e **registre no comentário do token que ela cedeu e por quê**.

- [ ] **Step 1: Medir**

Run: `cd dashboard && npm run pisos`

Anote, para os dois temas, o valor da coluna `piso medido` das três espessuras.

- [ ] **Step 2: Gravar os pisos medidos**

Substitua cada `--vidro-fino-piso`, `--vidro-piso` e `--vidro-denso-piso` (nos dois blocos de tema) pelo valor da coluna `piso medido`, **mantendo croma e matiz** de cada um — o script já os preserva na saída.

- [ ] **Step 3: Confirmar que nenhum piso está otimista**

Run: `npm run pisos`
Esperado: a coluna `veredito` diz `ok` nas seis linhas.

- [ ] **Step 4: Rodar o portão**

Run: `npm run contraste`

Se verde, pule para o Step 6.

- [ ] **Step 5: Engrossar o vidro até passar**

Para cada espessura envolvida num par reprovado, suba o percentual do `--vidro-*-fundo` correspondente em passos de 2 pontos, e **repita o ciclo medir → gravar → medir** (Steps 1–3) a cada passo, porque o piso muda junto.

```bash
# o laço, na prática:
npm run pisos      # le o piso novo
# grava os pisos no CSS
npm run contraste  # passou?
```

Se algum `--vidro-*-fundo` passar de 90%, **pare** e aplique a regra do teto descrita acima.

- [ ] **Step 6: Documentar os números no CSS**

Atualize os comentários acima dos blocos de piso e de fundo nos dois temas, dizendo: os valores anteriores, os novos, qual par reprovou e para quanto ele voltou. Os comentários que já estão lá seguem esse formato — imite.

- [ ] **Step 7: Rodar o ciclo**

Run: `npm run pisos && npm run contraste && npx tsc --noEmit && npm run lint`

- [ ] **Step 8: Commit**

```bash
git add dashboard/app/globals.css
git commit -m "fix(vidro): pisos remedidos e espessura ajustada ao atelie novo"
```

---

### Task 9: As emendas ao DESIGN.md

**Files:**
- Modify: `dashboard/DESIGN.md` (§3.1, §3.3.1, §8.2, §8.5)

**Interfaces:**
- Consumes: os números reais das Tasks 1–8 (opacidades finais, pisos, percentuais de vidro, e qualquer peça que tenha cedido).
- Produces: nada.

**Por que esta tarefa não é opcional:** o projeto é acadêmico e julgado por rigor. Código citando documento que não diz aquilo é o defeito mais caro que existe aqui. Já há quatro emendas registradas no arquivo (§2.1, §3.1, §6, §8) — **imite o formato delas**: o que mudou, o que continua de pé, e o custo.

- [ ] **Step 1: Emendar a §3.1 — a grade e o sol**

Adicione uma terceira emenda datada de 24/08/2026 ao bloco de citação da §3.1, dizendo: o fundo passou a carregar grade em perspectiva e sol listrado nos dois temas; o que **não** mudou é que continuam morando no ateliê, sem carregar dado, e passando por baixo da luz; e o custo em pisos e espessura de vidro, com os números reais da Task 8.

- [ ] **Step 2: Emendar a §3.3.1 — o raio vira canto duro**

Registre que `--radius` foi de `0.375rem` para `0.125rem`, e **use o argumento da própria seção**: ela já dizia que o F e o R são chanfrados a 45° e não têm curva de canto, e que só não foi a zero para não brigar com o chassi arredondado. Com o chassi endurecendo, a objeção caiu. Se a Task 4 sobreviveu, mencione o chanfro nos painéis.

- [ ] **Step 3: Emendar a §8.2 — a camada de dado passa a acompanhar o tema**

Esta é a emenda mais delicada do plano. Ela precisa dizer **três** coisas:

1. A regra 1 da §8.2 ("a camada de dado inteira fica como está") **deixa de valer**, por decisão do dono do projeto.
2. **O que continua de pé:** o matiz de cada família é intocado, então o *encoding* sobrevive — o que mudou foi a saturação, e ela nunca carregou significado. `--primary` continua fora de dado (§3.3). Categoria continua com rótulo textual.
3. **A correção de rota:** a §8.2 apresentava essa regra como compromisso vinculante do `PRODUCT.md`. **Não é.** O `PRODUCT.md` exige AA por cálculo e categoria nunca comunicada só por cor; ambos continuam valendo. A regra era decisão de design, e é dela que esta emenda trata.

- [ ] **Step 4: Emendar a §8.5 — a tabela vale para os dois temas**

O título "Onde a chuva pode gritar" pressupõe um tema só. Adicione uma nota dizendo que a decisão de 24/08/2026 foi **estrutura igual nos dois temas** — as peças existem nos dois e o tema decide cor e intensidade — e acrescente `grade a laser` e `sol listrado` à tabela, no formato das linhas que já estão lá.

- [ ] **Step 5: Conferir que o documento não mente**

Run: `grep -n "0.375rem\|16 features\|so no atelie\|só no ateliê" dashboard/DESIGN.md`

Cada ocorrência tem que estar dentro de uma emenda (descrevendo o passado) e não numa regra vigente (afirmando o presente).

- [ ] **Step 6: Commit**

```bash
git add dashboard/DESIGN.md
git commit -m "docs(design): emendas 3.1, 3.3.1, 8.2 e 8.5 para o vaporwave"
```

---

### Task 10: A conferência final

**Files:** nenhum, a menos que a conferência ache defeito.

**Interfaces:**
- Consumes: tudo.
- Produces: o relatório de fechamento.

**Por que existe:** duas rodadas de trabalho visual já foram entregues neste projeto sem uma única conferência no navegador, e foi assim que "chamativo" saiu invisível. Prova por cálculo não substitui olhar.

- [ ] **Step 1: Rodar os quatro gates**

```bash
cd dashboard
npm run pisos && npm run contraste && npx tsc --noEmit && npm run lint && npm run build
cd .. && uv run pytest -q
```

Esperado: pisos `ok` nas seis linhas, portão verde nos dois temas, tsc e lint limpos, build passa, **428 testes passam** (nada de Python muda; é sanidade).

- [ ] **Step 2: Percorrer as sete telas nos dois temas**

Com `npm run dev` no ar, em cada uma de `/`, `/atendimentos`, `/analisar`, `/modelo`, `/grafo`, `/configuracoes`, `/integracoes`, alternando o tema pelo seletor:

- o ateliê aparece nas calhas e **através** do vidro;
- nenhuma superfície opaca matou a luz (o bug do `SidebarInset`);
- texto legível em toda tela, com atenção ao vermelho de erro sobre o índigo da chuva;
- as sete famílias de sinal continuam distinguíveis entre si.

- [ ] **Step 3: Conferir uma tela VAZIA e uma CHEIA**

O ateliê some quando a tela enche de painéis — foi o que quase invalidou a marca no fundo. Confira `/` com um período sem dado (estado vazio) e `/atendimentos` com a tabela cheia. As peças novas têm que ler nas duas.

- [ ] **Step 4: Escrever o relatório de fechamento**

No corpo do PR, liste:
- cada peça entregue e a opacidade final que ela ficou, por tema;
- **cada peça que cedeu**, com o número que ela queria, o que ela ficou, e contra qual par de contraste ela perdeu;
- os percentuais finais de vidro nos dois temas;
- o que continua sendo dívida (as nove cores `hsl` se alguma ficou no limite, figura contra fundo por matiz).

A spec §6 é explícita: se uma peça ficou abaixo do que o pedido queria, isso é reportado, não escondido.

- [ ] **Step 5: Abrir a PR**

```bash
git push -u origin feat/vaporwave
gh pr create --title "feat(tema): vaporwave assumido nos dois temas" --body-file <relatorio>
```
