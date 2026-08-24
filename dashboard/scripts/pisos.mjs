/**
 * Medidor dos PISOS DE VIDRO -- a cor mais clara que cada espessura pode
 * assumir, que e o pior caso que `scripts/contraste.mjs` mede.
 *
 * POR QUE ISTO EXISTE COMO ARQUIVO. Esta conta ja foi feita tres vezes -- ao
 * acender o atelie do tema chuva, ao ligar o papel pautado, e ao imprimir a
 * marca no fundo -- e nas duas primeiras ela morreu num scratchpad, obrigando
 * a proxima sessao a reconstituir o metodo a partir de um comentario. Piso de
 * vidro nao e numero de gosto: e medicao, e medicao sem instrumento versionado
 * vira chute na terceira rodada.
 *
 * O METODO, e cada passo tem um porque:
 *
 *   1. Compoe TODAS as camadas do atelie no mesmo ponto. Isso e
 *      geometricamente impossivel -- a mancha da marca fica no alto a
 *      esquerda e a fria embaixo a direita --, e e de proposito: piso otimista
 *      e pior que piso nenhum, porque faz o portao devolver verde medindo uma
 *      superficie que nao existe.
 *   2. Poe cada espessura de vidro por cima, com a opacidade declarada no
 *      `--vidro-*-fundo`.
 *   3. Converte a luminancia resultante de volta para OKLCH, mantendo croma e
 *      matiz do piso vigente -- so a claridade e medida.
 *
 * A composicao e feita em sRGB com gama, que e como o navegador compoe
 * `background` sobre `background` por padrao. Compor em linear daria um numero
 * mais escuro e otimista, ou seja, o erro que este arquivo existe para evitar.
 *
 * Rode com:  node scripts/pisos.mjs
 * Ele nao escreve nada: le o `globals.css` e IMPRIME o piso que cada espessura
 * deveria ter. Comparar com o que esta no arquivo e trabalho de quem roda.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");

// --- conversao de cor ------------------------------------------------------

function oklchParaLinear(L, C, Hdeg) {
  const h = (Hdeg * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
}

const trava = (v) => Math.min(1, Math.max(0, v));
const paraGama = (v) =>
  v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(trava(v), 1 / 2.4) - 0.055;
const paraLinear = (v) =>
  v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);

/** OKLCH -> sRGB com gama, no formato em que o navegador compoe. */
function oklchParaGama(L, C, H) {
  return oklchParaLinear(L, C, H).map((v) => paraGama(trava(v)));
}

function luminanciaDeGama([r, g, b]) {
  const [R, G, B] = [r, g, b].map(paraLinear);
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

/** `fonte` sobre `destino`, ambos em sRGB com gama. */
function sobrepor(destino, fonte, alfa) {
  return destino.map((d, i) => d * (1 - alfa) + fonte[i] * alfa);
}

/**
 * A claridade OKLCH que, com o croma e o matiz dados, tem a luminancia alvo.
 *
 * Busca binaria e nao formula fechada porque a luminancia WCAG e uma soma
 * ponderada dos tres canais depois do cubo e da matriz -- monotonica em L, mas
 * sem inversa analitica limpa. 40 passos levam o erro a ordem de 1e-12.
 */
function claridadeParaLuminancia(alvo, C, H) {
  let baixo = 0;
  let alto = 1;
  for (let i = 0; i < 40; i += 1) {
    const meio = (baixo + alto) / 2;
    if (luminanciaDeGama(oklchParaGama(meio, C, H)) < alvo) baixo = meio;
    else alto = meio;
  }
  return (baixo + alto) / 2;
}

// --- leitura dos tokens ----------------------------------------------------

const css = readFileSync(join(RAIZ, "app", "globals.css"), "utf8");

/** Recorta o corpo de um bloco contando chaves (ha `@supports` aninhado). */
function recortarBloco(fonte, seletor) {
  const achado = seletor instanceof RegExp ? fonte.match(seletor) : null;
  const inicio = achado ? achado.index : fonte.indexOf(seletor);
  if (inicio === -1 || inicio === undefined) return null;
  const abre = fonte.indexOf("{", inicio);
  let profundidade = 0;
  for (let i = abre; i < fonte.length; i += 1) {
    if (fonte[i] === "{") profundidade += 1;
    else if (fonte[i] === "}") {
      profundidade -= 1;
      if (profundidade === 0) return fonte.slice(abre + 1, i);
    }
  }
  return null;
}

function lerCores(bloco) {
  const mapa = new Map();
  for (const m of bloco.matchAll(
    /^\s*(--[a-z0-9-]+):\s*oklch\(([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*(?:\/\s*[\d.]+%?\s*)?\)\s*;/gim,
  )) {
    mapa.set(m[1], [Number(m[2]), Number(m[3]), Number(m[4])]);
  }
  return mapa;
}

/**
 * Resolve os tokens escritos como `--a: var(--b)` -- e ha varios: no grafite
 * `--atelie-marca` e `var(--primary)` e `--marca-cor` e `var(--atelie-marca)`.
 * Sem isto o alias sumiria em silencio do calculo, que e o modo de falha que
 * `contraste.mjs` documenta na lista `fundos`.
 */
/**
 * ARMADILHA PAGA (24/08/2026): a chamada original resolvia os aliases da BASE
 * depois de já ter mesclado os literais do tema no mesmo mapa
 * (`resolverAliases(new Map([...base, ...tema]), corpoBase)`), com o mapa
 * mesclado sendo mutado in-place. Como o bloco base declara
 * `--atelie-fria: var(--medido)`, essa resolucao SOBRESCREVIA o literal que o
 * tema chuva ja tinha declarado para `--atelie-fria` (magenta,
 * `oklch(0.62 0.24 320)`) com o azul de `--medido` da base. O script media
 * mais claro que a realidade -- erro pessimista, mas ainda erro: engordava o
 * vidro da chuva sem necessidade.
 *
 * A ordem importa porque `mapa.set` nao sabe qual bloco "ganhou" um valor --
 * ele so ve o mapa final. Por isso a resolucao de alias de um bloco tem que
 * rodar ANTES de aquele bloco ser sobreposto por um de maior precedencia: um
 * token declarado literalmente nunca pode ser sobrescrito por um alias de um
 * bloco de precedencia menor. Ver o uso abaixo: a base resolve sozinha
 * primeiro, so depois o tema é mesclado por cima (e resolvido por ultimo).
 */
function resolverAliases(mapa, bloco) {
  const alias = new Map();
  for (const m of bloco.matchAll(
    /^\s*(--[a-z0-9-]+):\s*var\(\s*(--[a-z0-9-]+)\s*\)\s*;/gim,
  )) {
    alias.set(m[1], m[2]);
  }
  for (const [nome, destino] of alias) {
    let atual = destino;
    for (let i = 0; i < 8 && !mapa.has(atual); i += 1) {
      atual = alias.get(atual);
      if (!atual) break;
    }
    if (atual && mapa.has(atual)) mapa.set(nome, mapa.get(atual));
  }
  return mapa;
}

function lerNumeros(bloco) {
  const mapa = new Map();
  for (const m of bloco.matchAll(/^\s*(--[a-z0-9-]+):\s*([\d.]+)\s*;/gim)) {
    mapa.set(m[1], Number(m[2]));
  }
  return mapa;
}

/** Le a porcentagem do `color-mix(in oklch, var(--card) N%, transparent)`. */
function lerMistura(bloco, nome) {
  const re = new RegExp(
    `${nome}:\\s*color-mix\\(in oklch,\\s*var\\(--card\\)\\s*([\\d.]+)%`,
    "i",
  );
  const m = bloco.match(re);
  return m ? Number(m[1]) / 100 : null;
}

const SELETOR_BASE = /:root\s*,\s*\.dark\s*\{/;
const corpoBase = recortarBloco(css, SELETOR_BASE) ?? "";

const temas = [{ nome: "grafite (base)", corpo: corpoBase }];
for (const m of css.matchAll(/^(\.tema-[a-z0-9-]+)\s*\{/gim)) {
  const corpo = recortarBloco(css, m[1]);
  if (corpo) temas.push({ nome: m[1].replace(".tema-", ""), corpo });
}

// A CHUVA DIAGONAL e a unica camada cuja cor esta cravada no `Atelier.tsx` em
// vez de vir de token -- ela e textura, nao luz de tema. Repetida aqui, e o
// arquivo diz de onde vem para o dia em que mudar.
const COR_CHUVA = [0.92, 0.08, 250]; // Atelier.tsx, camada da chuva

const ESPESSURAS = [
  ["fino", "--vidro-fino-fundo", "--vidro-fino-piso"],
  ["medio", "--vidro-fundo", "--vidro-piso"],
  ["denso", "--vidro-denso-fundo", "--vidro-denso-piso"],
];

for (const tema of temas) {
  // Base primeiro, tema por cima: o tema so declara o que muda.
  // A base resolve os proprios aliases SOZINHA, com o proprio mapa -- so
  // depois os literais do tema entram por cima, e so entao os aliases do
  // tema resolvem. Assim um literal do tema nunca perde para um alias da
  // base (ver a armadilha documentada em `resolverAliases`).
  const coresBase = resolverAliases(lerCores(corpoBase), corpoBase);
  const cores = resolverAliases(
    new Map([...coresBase, ...lerCores(tema.corpo)]),
    tema.corpo,
  );
  const nums = new Map([...lerNumeros(corpoBase), ...lerNumeros(tema.corpo)]);
  const cor = (n) => cores.get(n);
  const op = (n) => nums.get(n) ?? 0;

  // A ORDEM E A DO DOM em Atelier.tsx. Trocar a ordem muda o resultado --
  // sobreposicao alfa nao e comutativa.
  // PAUTA, MARCA e GRADE sao ALTERNATIVAS, nao somam, e isto foi lido das
  // mascaras e nao escolhido por conveniencia: a mascara do papel e
  // `radial-gradient(140% 100% at 50% -10%, black 15%, transparent 70%)`, que
  // zera por volta de 60% da altura da tela; a marca mora colada na quina
  // inferior direita e a propria mascara dela
  // (`radial-gradient(120% 120% at 100% 100%, ..., transparent 72%)`) so deixa
  // massa no terco de baixo; a grade mora no mesmo terco de baixo, mascarada
  // por `linear-gradient(to top, black 0%, transparent 92%)`. Onde uma tem
  // forca as outras ja acabaram ou ainda nao comecaram.
  //
  // Somar as duas seria empilhar luz que nao existe em pixel nenhum, e o custo
  // disso e concreto: medido assim, o vidro medio da chuva precisaria de 93%
  // de opacidade para o portao passar -- vidro a 93% nao e vidro, e o reskin
  // inteiro morreria para proteger uma superficie imaginaria. O resto do pior
  // caso continua impossivel de proposito (as tres manchas somadas no mesmo
  // ponto), porque ali a impossibilidade e barata.
  // A alternativa vencedora e a que resulta MAIS CLARA, e nao a de maior
  // opacidade: as tres tem cor diferente (ouro palido, magenta, ciano), e mais
  // alfa de uma cor escura pode clarear menos que menos alfa de uma clara.
  const alternativas = [
    ["papel pautado", cor("--pauta-cor"), op("--pauta-op")],
    ["marca impressa", cor("--marca-cor"), op("--marca-op")],
    ["grade a laser", cor("--grade-cor"), op("--grade-op")],
  ];

  const compor = (escolhida) => {
    const camadas = [
      escolhida,
      ["mancha da marca", cor("--atelie-marca"), op("--atelie-op-marca")],
      ["mancha fria", cor("--atelie-fria"), op("--atelie-op-fria")],
      // O sol listrado herdou o posto da mancha quente (ver Atelier.tsx). A
      // cor medida e a ALTA do gradiente: e a mais clara das duas, e piso
      // otimista e pior que piso nenhum.
      ["sol listrado", cor("--sol-cor-alta"), op("--sol-op")],
      ["reflexo no asfalto", cor("--atelie-fria"), op("--atelie-asfalto")],
      ["chuva", COR_CHUVA, op("--atelie-chuva")],
    ];
    let acc = oklchParaGama(...cor("--background"));
    for (const [, c, a] of camadas) {
      if (!c || !a) continue;
      acc = sobrepor(acc, oklchParaGama(...c), a);
    }
    return acc;
  };

  const candidatos = alternativas.map((alt) => ({
    nome: alt[0],
    cor: compor(alt),
  }));
  candidatos.sort(
    (a, b) => luminanciaDeGama(b.cor) - luminanciaDeGama(a.cor),
  );
  const composto = candidatos[0].cor;
  const vencedora = candidatos[0].nome;

  console.log(`\n=== tema: ${tema.nome} ===`);
  console.log(
    `atelie composto (pior caso, com "${vencedora}"): L ~ ${claridadeParaLuminancia(
      luminanciaDeGama(composto),
      0,
      0,
    ).toFixed(3)}`,
  );

  const linhas = [];
  for (const [nome, tokenFundo, tokenPiso] of ESPESSURAS) {
    const pct =
      lerMistura(tema.corpo, tokenFundo) ?? lerMistura(corpoBase, tokenFundo);
    const vidro = sobrepor(composto, oklchParaGama(...cor("--card")), pct);
    const vigente = cor(tokenPiso);
    const L = claridadeParaLuminancia(
      luminanciaDeGama(vidro),
      vigente[1],
      vigente[2],
    );
    linhas.push({
      espessura: nome,
      "opacidade do vidro": `${(pct * 100).toFixed(0)}%`,
      "piso medido": `oklch(${L.toFixed(3)} ${vigente[1]} ${vigente[2]})`,
      "piso no CSS": `oklch(${vigente[0]} ${vigente[1]} ${vigente[2]})`,
      veredito: L <= vigente[0] + 0.0005 ? "ok" : "OTIMISTA -- corrigir",
    });
  }
  console.table(linhas);
}

console.log(
  "\nO piso no CSS precisa ser >= o medido. Piso otimista faz o portao" +
    "\ndevolver verde medindo uma superficie que nao existe." +
    "\nSe o portao reprovar com o piso certo, ENGROSSE o vidro (--vidro-*-fundo)" +
    "\n-- o portao manda no vidro, o vidro nao afrouxa o portao.",
);
