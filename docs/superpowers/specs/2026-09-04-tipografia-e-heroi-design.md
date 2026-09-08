---
title: "Spec — Mona Sans no display e o herói de quinas"
date: 2026-09-04
tags: [fraus, design, vitrine, tipografia, spec]
---

# Spec — Mona Sans no display e o herói de quinas

Executa **duas** das seis frentes levantadas em
[`docs/notas/2026-09-04-reformulacao-visual.md`](../../notas/2026-09-04-reformulacao-visual.md):
a §2.2 (tipografia) e o padrão do herói vazio da §1.2.

**O que esta spec deliberadamente NÃO faz**, porque a decisão do dono do projeto
em 04/09/2026 foi de escopo médio e não de reformulação completa:

- não interroga o escuro-por-decreto da §2.1 — os dois temas ficam como estão;
- não mexe na tese *Pauta* (§2.3): ela fica, e só a linguagem visual muda;
- não encosta no modo Operate, em `--primary`, nem no encoding âmbar/azul;
- não leva a vitrine ao território experimental (rolagem sequestrada, WebGL como
  meio de navegação) — a pergunta 4 da nota segue aberta.

---

## 1. Tipografia — Mona Sans, e só no display

**Escolha.** Mona Sans v2.0.27, a mesma display da landonorris.com, que a nota
elege como a referência mais instrutiva das seis. Grotesca variável, sem a
memória de "aplicação moderna bem-feita" que a Inter carrega — que é exatamente o
diagnóstico da §2.2.

**Qual corte.** O release traz dois cortes variáveis, e o escolhido é o de dois
eixos — peso e tamanho óptico, ~137 KB. O corte que acrescenta o eixo de largura
pesa ~308 KB, e nenhuma regra deste trabalho aciona largura: as duas classes de
display só definem família, e a manchete trava o peso. O tamanho óptico, esse
sim, serve ao caso — é fonte de display em corpo grande.

**Como entra.** O `.woff2` variável é versionado em `dashboard/app/fontes/`,
com o arquivo de licença da fonte ao lado, e carregados por `next/font/local`
expondo `--fonte-mona`. Isso preserva a invariante 1 do `CLAUDE.md` do mesmo
jeito que Inter e JetBrains já a preservam: o arquivo é servido do próprio
deploy, e não há chamada de rede no caminho de renderização.

**Onde manda, e onde não manda.** A variável governa `.display-vitrine` e
`.titulo-vitrine`. Mais nada. Inter segue no corpo, nos rótulos e em toda a
ferramenta; JetBrains segue no dado. O numeral tabular não é tocado, porque
nenhum número que se compara passa a usar a nova família — a proibição de fonte
de display em rótulo e dado (`DESIGN.md` §4) continua valendo integralmente.

**Emenda ao `DESIGN.md` §4.** O texto hoje diz que a exceção da LP "usa a própria
Inter em corpo grande". Passa a nomear a família de display e o escopo exato.

## 2. O herói de quinas

**Diagnóstico.** O herói atual é manchete grande, alinhada à esquerda dentro da
coluna, com o argumento inteiro, dois botões e uma seta de rolagem. É a escolha
convencional — e é por isso que ele lê como landing page de produto, e não como
as referências. Na landonorris a primeira tela é quase toda espaço negativo, com
o conteúdo ancorado nas quinas: a confiança está em não preencher.

**Composição.** A `<section>` do herói passa a distribuir o conteúdo entre topo e
base em altura cheia, com três âncoras:

| Âncora | Conteúdo |
|---|---|
| superior esquerda | *(vazia — o cabeçalho fixo acima já ancora a marca)* |
| superior direita | a etiqueta mono `satisfação inferida · sem pesquisa` |
| inferior esquerda | a manchete, com o glitch preservado sobre a frase citada |
| inferior direita | a ação primária |

A marca **não** se repete no herói: o `<header>` fixo já a mantém na quina
superior esquerda em toda a rolagem, e duplicá-la seria o aparato repetido que a
PR #31 acabou de remover em outro lugar.

**O parágrafo de argumento sai do herói** e vira a abertura da seção do artefato,
depois da esteira — onde ele passa a legendar a peça que está sendo mostrada em
vez de disputar espaço com a manchete. Nenhuma frase é perdida.

**A seta de rolagem sai.** Ela vivia centralizada na base, onde agora está o CTA,
e um centro vazio já convida a rolar sem precisar de instrução.

**O glitch fica.** Ele cai sobre `"ok, obrigado 🙂"` e só sobre ela, e é a única
peça da página que É o argumento — o produto se chama Fraus, e texto que diz uma
coisa e mostra outra é literalmente o assunto da ferramenta.

**Telas estreitas.** Abaixo de `sm` as quinas se desfazem numa pilha — etiqueta,
manchete, ação. Quina em 390px de largura é um empilhamento com nome pomposo, e
o espaço negativo que dá o efeito não existe ali para ser gasto.

## 3. Invariantes que continuam valendo

Nenhuma é questão de gosto, e nenhuma é afrouxada por esta spec:

- a manchete continua sendo texto real dentro de um `<h1>` — sem canvas, sem
  imagem, sem `background-clip: text` (a tentativa e o defeito já estão
  registrados em comentário no `app/page.tsx`);
- nada que carrega dado é translúcido nem animado;
- todo par de cor que carrega texto cruza AA por cálculo;
- sem chamada de rede em runtime, o que inclui a fonte.

## 4. Verificação

Nenhum par de cor novo nasce aqui, mas o gate roda mesmo assim:

```bash
cd dashboard && npm run contraste && npm run lint && npm run build
```

A conferência visual é **por viewport**, em `localhost:3000`. Nunca `fullPage`,
que não dispara `whileInView` e não dá conta de página alta; nunca
`127.0.0.1:3000`, que leva 403 nos chunks do Next 16 em dev e congela o estado
inicial dos componentes com sintoma idêntico ao de um bug de animação. Os três
modos de falha estão pagos e descritos na §5 da nota de design.
