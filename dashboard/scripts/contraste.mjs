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
const tokens = new Map();
for (const m of css.matchAll(
  /^\s*(--[a-z0-9-]+):\s*oklch\(([\d.]+)\s+([\d.]+)\s+([\d.]+)\)\s*;/gim,
)) {
  tokens.set(m[1], [Number(m[2]), Number(m[3]), Number(m[4])]);
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
];

let falhou = false;
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

console.table(linhas);
if (falhou) {
  console.error("\nFALHOU: ha par abaixo de 4.5:1.");
  process.exit(1);
}
console.log("\nTodos os pares de texto cruzam AA (4.5:1).");
