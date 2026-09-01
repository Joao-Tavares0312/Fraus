/**
 * Verificador de contraste WCAG dos tokens do Fraus.
 *
 * O DESIGN.md exige AA (4.5:1) "verificado por calculo" e diz que cor de
 * marcacao e cor de tipo nao sao a mesma coisa: quando uma cor de categoria
 * carrega TEXTO, ela precisa cruzar 4.5:1 contra --card.
 *
 * Rode com:  node scripts/contraste.mjs
 * Ele le os tokens do proprio app/globals.css -- nao ha lista duplicada aqui,
 * entao um token editado no CSS aparece no relatorio sem ninguem lembrar.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");

// --- OKLCH -> sRGB linear -> luminancia relativa ---------------------------

function oklchParaSrgb(L, C, Hdeg) {
  const h = (Hdeg * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);

  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.291485548 * b;

  const l = l_ ** 3;
  const m = m_ ** 3;
  const s = s_ ** 3;

  return [
    +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
}

/** Luminancia relativa WCAG. A entrada ja e sRGB LINEAR, entao nao ha gama a desfazer. */
function luminancia([r, g, b]) {
  const clamp = (v) => Math.min(1, Math.max(0, v));
  return 0.2126 * clamp(r) + 0.7152 * clamp(g) + 0.0722 * clamp(b);
}

function razao(corA, corB) {
  const a = luminancia(oklchParaSrgb(...corA));
  const b = luminancia(oklchParaSrgb(...corB));
  const [claro, escuro] = a > b ? [a, b] : [b, a];
  return (claro + 0.05) / (escuro + 0.05);
}

// --- leitura dos tokens do globals.css -------------------------------------

const css = readFileSync(join(RAIZ, "app", "globals.css"), "utf8");

/**
 * Le os tokens `oklch(L C H)` literais de dentro de UM bloco de CSS.
 *
 * So captura literal de proposito: um token escrito com `color-mix` seria
 * ignorado em silencio, e por isso os pisos de vidro sao pre-calculados. Ver
 * o comentario da lista `fundos`.
 */
function lerTokens(bloco) {
  const mapa = new Map();
  for (const m of bloco.matchAll(
    /^\s*(--[a-z0-9-]+):\s*oklch\(([\d.]+)\s+([\d.]+)\s+([\d.]+)\)\s*;/gim,
  )) {
    mapa.set(m[1], [Number(m[2]), Number(m[3]), Number(m[4])]);
  }
  return mapa;
}

/**
 * Recorta o corpo do bloco que comeca no seletor dado, contando chaves.
 *
 * Contagem em vez de regex porque o bloco de tema tem `@supports` e `@media`
 * aninhados dentro, e `[^}]*` pararia na primeira chave interna.
 */
function recortarBloco(fonte, seletor) {
  // Regex e nao `indexOf`: o arquivo pode estar em CRLF, e um seletor de duas
  // linhas casado por string literal quebraria so na maquina que usa CRLF --
  // o tipo de falha que so aparece no computador do outro.
  const achado = seletor instanceof RegExp ? fonte.match(seletor) : null;
  const inicio = achado ? achado.index : fonte.indexOf(seletor);
  if (inicio === -1 || inicio === undefined) return null;
  const abre = fonte.indexOf("{", inicio);
  if (abre === -1) return null;
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

// OS TEMAS. O primeiro e a base; os demais SOBREPOEM a base, exatamente como
// a cascata do CSS faz -- um tema que so troca o chassi herda a camada de dado
// inteira e nao precisa redeclarar nada.
//
// POR QUE ISTO EXISTE, e e o ponto todo deste arquivo: antes havia um Map
// unico para o arquivo inteiro, entao o segundo tema a declarar `--background`
// sobrescrevia o primeiro e o gate passava a medir UM tema achando que media
// todos. Falha silenciosa: relatorio verde, tema ilegivel em producao.
const SELETOR_BASE = /:root\s*,\s*\.dark\s*\{/;
const base = lerTokens(recortarBloco(css, SELETOR_BASE) ?? "");
if (base.size === 0) {
  console.error(`nenhum token lido do bloco base (${SELETOR_BASE})`);
  process.exit(1);
}

const temas = [{ nome: "espacial (base)", tokens: base }];

for (const m of css.matchAll(/^(\.tema-[a-z0-9-]+)\s*\{/gim)) {
  const corpo = recortarBloco(css, m[1]);
  if (!corpo) continue;
  // Base primeiro, sobreposicao depois: o tema so precisa declarar o que muda.
  const mapa = new Map(base);
  for (const [nome, cor] of lerTokens(corpo)) mapa.set(nome, cor);
  temas.push({ nome: m[1].replace(".tema-", ""), tokens: mapa });
}

// Os PISOS DE VIDRO entram aqui porque superficie translucida nao tem cor
// fixa: ela depende do que esta atras. Cada piso e a cor MAIS CLARA que
// aquela espessura pode assumir -- o fundo do vidro composto sobre a mancha
// mais brilhante do atelie --, ou seja, o pior caso para texto claro.
//
// Eles sao opacos e pre-calculados de proposito: o regex acima so captura
// `oklch(L C H)` literal, e um piso escrito com color-mix seria ignorado em
// silencio -- o modo de falha que esta lista existe para evitar.
const fundos = [
  "--background",
  "--card",
  "--muted",
  "--vidro-fino-piso",
  "--vidro-piso",
  "--vidro-denso-piso",
];

// Tokens que CARREGAM TEXTO em algum lugar da interface. So estes precisam AA.
const textos = [
  "--foreground",
  "--muted-foreground",
  "--primary",
  "--dito-texto",
  "--medido-texto",
  "--tempo-texto",
  "--emocao-texto",
  "--lexico-texto",
  "--ironia-texto",
  "--estilo-texto",
  "--outros-sinal-texto",
  "--detrator-texto",
  "--neutro-texto",
  "--promotor-texto",
  // os cinco abaixo passaram a carregar texto sobre vidro no reskin
  // "vidro liquido" e o gate estava cego para eles
  "--secondary-foreground",
  "--popover-foreground",
  "--card-foreground",
  "--sidebar-foreground",
  "--destructive",
  // Os tres `-rich-text` estavam CEGOS para este gate ate 24/08/2026: eram
  // escritos em `hsl()` e o parser so le `oklch()` literal. Carregam texto em
  // AvisoApiFora, EstadoSaude, TextoComPesos, MetricasTreino, ReguaDeCamadas
  // e Analisador -- e nunca foram medidos, em tema nenhum.
  "--destructive-rich-text",
  "--success-rich-text",
  "--warning-rich-text",
];

// MARCAS: cor que desenha DADO sem carregar texto -- serie do grafico, no do
// grafo, ponto, barra, cabeca vazada.
//
// Elas exigem 3:1 e nao 4.5:1, e a diferenca nao e leniencia: a WCAG separa
// texto de objeto grafico (1.4.11) porque uma forma de varios pixels de
// espessura se distingue com menos contraste que a haste de uma letra.
//
// POR QUE ISTO FALTAVA: o gate media texto sobre fundo e nada mais, entao
// nenhuma cor de marcacao foi verificada contra fundo nenhum, em tema nenhum.
// Passou despercebido enquanto havia um tema so, cujo fundo essas cores
// acompanharam desde que nasceram. Um tema novo e exatamente o evento que
// quebraria isso em silencio -- e o gate nao teria dito nada.
//
// ATENCAO ao que este numero NAO cobre: ele mede luminancia, nao matiz. Uma
// serie azul sobre fundo azul pode cruzar 3:1 com folga e ainda assim custar
// para separar do fundo. Figura contra fundo por MATIZ e julgamento de olho, e
// nao ha calculo aqui que substitua olhar.
const marcas = [
  "--dito",
  "--medido",
  "--emocao",
  "--lexico",
  "--ironia",
  "--estilo",
  "--tempo",
  "--detrator",
  "--neutro",
  "--promotor",
  "--sem-sinal",
  "--no-conversa",
  "--no-termo",
  "--no-emoji",
  "--no-feature",
  "--no-categoria",
  "--no-canal",
  "--no-desfecho",
  "--no-fonte",
  "--no-importacao",
];

/** Fundos sobre os quais uma marca chega a ser desenhada. */
const fundosDeMarca = ["--background", "--card"];

const MINIMO_MARCA = 3;

let falhou = false;

for (const tema of temas) {
const tokens = tema.tokens;
const linhas = [];

for (const nomeTexto of textos) {
  const cor = tokens.get(nomeTexto);
  if (!cor) {
    console.error(`token ausente no globals.css: ${nomeTexto}`);
    falhou = true;
    continue;
  }
  for (const nomeFundo of fundos) {
    const fundo = tokens.get(nomeFundo);
    if (!fundo) continue;
    const r = razao(cor, fundo);
    const ok = r >= 4.5;
    if (!ok) falhou = true;
    linhas.push({
      texto: nomeTexto,
      sobre: nomeFundo,
      razao: r.toFixed(2),
      AA: ok ? "PASS" : "FAIL",
    });
  }
}

// Texto sobre SUPERFICIE PREENCHIDA -- o rotulo dentro do botao.
//
// Faltava, e era um buraco de verdade: a lista acima cobre texto sobre fundo,
// e o botao primario e o contrario disso (texto escuro sobre a cor da marca).
// Ninguem checava o par mais clicado da interface. Apareceu ao trocar o lime
// pelo dourado da logo -- exatamente o tipo de mudanca que poderia ter
// derrubado a legibilidade do botao sem nenhum aviso.
const preenchidos = [
  ["--primary-foreground", "--primary"],
  ["--sidebar-primary-foreground", "--sidebar-primary"],
];

for (const [nomeTexto, nomeFundo] of preenchidos) {
  const cor = tokens.get(nomeTexto);
  const fundo = tokens.get(nomeFundo);
  if (!cor || !fundo) {
    console.error(`token ausente no globals.css: ${nomeTexto} ou ${nomeFundo}`);
    falhou = true;
    continue;
  }
  const r = razao(cor, fundo);
  const ok = r >= 4.5;
  if (!ok) falhou = true;
  linhas.push({
    texto: nomeTexto,
    sobre: nomeFundo,
    razao: r.toFixed(2),
    AA: ok ? "PASS" : "FAIL",
  });
}

for (const nomeMarca of marcas) {
  const cor = tokens.get(nomeMarca);
  if (!cor) {
    console.error(`token ausente no globals.css: ${nomeMarca}`);
    falhou = true;
    continue;
  }
  for (const nomeFundo of fundosDeMarca) {
    const fundo = tokens.get(nomeFundo);
    if (!fundo) continue;
    const r = razao(cor, fundo);
    const ok = r >= MINIMO_MARCA;
    if (!ok) falhou = true;
    linhas.push({
      texto: nomeMarca,
      sobre: nomeFundo,
      razao: r.toFixed(2),
      AA: ok ? "PASS" : "FAIL",
      minimo: `${MINIMO_MARCA}:1 (marca)`,
    });
  }
}

console.log(`\n=== tema: ${tema.nome} ===`);
console.table(linhas);
}

if (falhou) {
  console.error("\nFALHOU: ha par abaixo de 4.5:1.");
  process.exit(1);
}
console.log(
  `\nTexto cruza AA (4.5:1) e marca cruza ${MINIMO_MARCA}:1 nos ` +
    `${temas.length} tema(s): ${temas.map((t) => t.nome).join(", ")}.` +
    "\nLembrete: isto mede LUMINANCIA. Figura contra fundo por MATIZ nao tem" +
    " calculo -- precisa de olho.",
);
