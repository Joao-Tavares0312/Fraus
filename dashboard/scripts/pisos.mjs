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

/**
 * O PIOR CASO DA CENA DA VITRINE VIROU TRAJETORIA, NAO PONTO (04/09/2026).
 *
 * A cena (grade, planeta, estrelas) passou a acompanhar a rolagem em
 * `lib/cena.ts`: cada camada varia entre 0 e um FATOR MAXIMO ao longo do
 * scroll, em vez de ficar fixa na opacidade do tema. O piso deste script
 * precisa medir o estado MAIS CLARO que a cena atinge em QUALQUER ponto da
 * rolagem -- que e `fator maximo x token do tema`, por tema (o fator nao sabe
 * de tema, o token e quem carrega a intensidade, inclusive o zero deliberado
 * de `--estrelas-op` na chuva).
 *
 * ESTE ARQUIVO E `lib/cena.ts` NAO SAO ARQUIVOS TYPESCRIPT ES MODULES QUE UM
 * SCRIPT `.mjs` POSSA IMPORTAR SEM UM PASSO DE TRANSPILACAO -- e este projeto
 * nao tem dependencia nova para isso. A saida e a mesma do resto do arquivo
 * (ver `lerCores`/`lerNumeros` acima): ler o texto do `.ts` e extrair por
 * expressao regular. Ler so o fator, ou so o token, mede uma superficie que
 * nao existe -- o modo de falha que a §8.6 do DESIGN.md registra ter
 * acontecido duas vezes; por isso o fator vem DAQUI, do arquivo fonte, e
 * nunca de um numero copiado a mao.
 */
const cenaTs = readFileSync(join(RAIZ, "lib", "cena.ts"), "utf8");

function lerFatorMaximo(camada) {
  const re = new RegExp(`${camada}:\\s*([\\d.]+)`, "i");
  const bloco = recortarBloco(cenaTs, "FATOR_MAXIMO_POR_CAMADA") ?? "";
  const m = bloco.match(re);
  if (!m) throw new Error(`fator maximo de "${camada}" nao encontrado em lib/cena.ts`);
  return Number(m[1]);
}

const FATOR_GRADE = lerFatorMaximo("grade");
const FATOR_PLANETA = lerFatorMaximo("planeta");
const FATOR_ESTRELAS = lerFatorMaximo("estrelas");

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
 * Resolve os tokens escritos como `--a: var(--b)` -- e ha varios: na base
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

const temas = [{ nome: "instrumento (base)", corpo: corpoBase }];
for (const m of css.matchAll(/^(\.tema-[a-z0-9-]+)\s*\{/gim)) {
  const corpo = recortarBloco(css, m[1]);
  if (corpo) temas.push({ nome: m[1].replace(".tema-", ""), corpo });
}

// A CHUVA DIAGONAL e a unica camada cuja cor esta cravada no `Atelier.tsx` em
// vez de vir de token -- ela e textura, nao luz de tema. Repetida aqui, e o
// arquivo diz de onde vem para o dia em que mudar.
const COR_CHUVA = [0.92, 0.08, 250]; // Atelier.tsx, camada da chuva

// O CAMPO DE ESTRELAS (tema "espaco profundo", 01/09/2026) tem cor cravada no
// `Atelier.tsx` pelo mesmo motivo da chuva: e textura, nao luz de tema. A mais
// CLARA das tres camadas de ponto, porque piso otimista e pior que piso nenhum.
const COR_ESTRELAS = [0.98, 0.02, 230]; // Atelier.tsx, camada das estrelas

// A COBERTURA AREAL das estrelas, e sem ela esta camada seria modelada errado
// por ordens de grandeza -- para MAIS, o que aqui e o lado caro: um piso
// pessimista demais engrossa vidro que nao precisava engrossar, e vidro grosso
// apaga exatamente a cena que o tema existe para mostrar.
//
// Todas as outras camadas desta lista sao lavagens de tela CHEIA, entao para
// elas a opacidade do token JA e a contribuicao. As estrelas nao: sao tres
// tiles com UM ponto cada (raio ~1,2px, com queda para transparente) em
// periodos de 137, 191 e 89 pixels. A area pintada e ~1,5px^2 num tile de
// ~18.800px^2 -- da ordem de um decimo de milesimo.
//
// E POR QUE A MEDIA E O NUMERO CERTO, e nao o brilho do ponto: o que este
// script modela e o fundo visto ATRAVES de `backdrop-filter: blur()`. O blur
// borra o backdrop, ou seja, ele devolve a media local -- pontos isolados
// viram uma lavagem uniforme do valor medio. Medir a estrela pelo pico seria
// medir um pixel que o vidro nunca entrega a superficie nenhuma.
const COBERTURA_ESTRELAS = 0.00008;

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
  // DUAS ALTERNATIVAS, e so uma disjuncao continua sendo verdade: o PAPEL
  // PAUTADO contra MARCA+GRADE SOMADAS.
  //
  // O papel e disjunto dos outros dois porque a mascara dele e
  // `radial-gradient(140% 100% at 50% -10%, black 15%, transparent 70%)`, que
  // zera por volta de 60% da altura da tela -- ele nao tem massa nenhuma no
  // terco de baixo, onde as outras duas moram.
  //
  // MARCA E GRADE SOMAM porque se SOBREPOEM na quina inferior direita: a marca
  // e `-bottom-[12%] -right-[10%] h-[115vmin] w-[115vmin]` com segunda mascara
  // `radial-gradient(150% 150% at 100% 100%, black 34%, transparent 96%)` --
  // solida num raio grande a partir da quina --, e a grade e `bottom-0
  // h-[45vh]` de largura total, mais forte justamente colada no rodape. O pixel
  // "linha da grade sobre traco do monograma" existe de verdade.
  //
  // ARMADILHA PAGA (24/08/2026): ate esta correcao as tres eram alternativas
  // entre si, e o comentario citava como prova a mascara ANTIGA da marca
  // (`radial-gradient(120% 120% at 100% 100%, ..., transparent 72%)`), que so
  // deixava massa num raio estreito. Essa mascara foi ALARGADA depois, de
  // proposito e a pedido do dono do projeto, para a marca ficar visivel -- e o
  // modelo de medicao nao acompanhou. Resultado: os seis pisos ficaram
  // OTIMISTAS e o portao devolvia verde medindo uma superficie que nao existe
  // (`--destructive` x `--vidro-fino-piso` caia para 4,29 no grafite e 4,44 na
  // chuva). Premissa de disjuncao e afirmacao sobre GEOMETRIA: quem mexer numa
  // mascara do `Atelier.tsx` tem que reconferir esta lista.
  //
  // A alternativa vencedora e a que resulta MAIS CLARA, e nao a de maior
  // opacidade: as camadas tem cor diferente (ouro palido, magenta, ciano), e
  // mais alfa de uma cor escura pode clarear menos que menos alfa de uma clara.
  const alternativas = [
    ["papel pautado", ["papel pautado"]],
    ["marca + grade", ["marca impressa", "grade a laser"]],
  ];

  // A lista abaixo esta na ORDEM DO DOM em `Atelier.tsx`, incluindo as camadas
  // opcionais -- e por isso que a escolha entra como filtro e nao como item
  // prefixado: sobreposicao alfa nao e comutativa, e a marca impressa vem
  // DEPOIS das manchas de luz, a grade DEPOIS do asfalto.
  const compor = (ligadas) => {
    const camadas = [
      ["papel pautado", cor("--pauta-cor"), op("--pauta-op")],
      // Ver COBERTURA_ESTRELAS: a contribuicao e opacidade x area pintada, e
      // nao a opacidade do token. Entra sempre (nao e alternativa) porque a
      // mascara dela cobre a tela toda menos o rodape -- ela se sobrepoe a
      // qualquer uma das duas alternativas abaixo. Somar sempre e a leitura
      // pessimista, e com uma contribuicao desta ordem ela nao custa nada.
      [
        "estrelas",
        COR_ESTRELAS,
        op("--estrelas-op") * FATOR_ESTRELAS * COBERTURA_ESTRELAS,
      ],
      ["mancha da marca", cor("--atelie-marca"), op("--atelie-op-marca")],
      ["mancha fria", cor("--atelie-fria"), op("--atelie-op-fria")],
      // O sol listrado herdou o posto da mancha quente (ver Atelier.tsx). A
      // cor medida e a ALTA do gradiente: e a mais clara das duas, e piso
      // otimista e pior que piso nenhum.
      ["sol listrado", cor("--sol-cor-alta"), op("--sol-op") * FATOR_PLANETA],
      ["marca impressa", cor("--marca-cor"), op("--marca-op")],
      ["reflexo no asfalto", cor("--atelie-fria"), op("--atelie-asfalto")],
      ["grade a laser", cor("--grade-cor"), op("--grade-op") * FATOR_GRADE],
      ["chuva", COR_CHUVA, op("--atelie-chuva")],
    ];
    const opcionais = new Set(["papel pautado", "marca impressa", "grade a laser"]);
    let acc = oklchParaGama(...cor("--background"));
    for (const [nome, c, a] of camadas) {
      if (opcionais.has(nome) && !ligadas.includes(nome)) continue;
      if (!c || !a) continue;
      acc = sobrepor(acc, oklchParaGama(...c), a);
    }
    return acc;
  };

  const candidatos = alternativas.map(([nome, ligadas]) => ({
    nome,
    cor: compor(ligadas),
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
