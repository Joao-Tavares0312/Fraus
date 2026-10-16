import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export const css = readFileSync(fileURLToPath(new URL("../app/globals.css", import.meta.url)), "utf8");

/** Canais sRGB lineares para WCAG; CSS pode usar HEX ou OKLCH. */
function corLinear(valor) {
  const hex = valor.match(/^#([0-9a-f]{6})$/i);
  if (hex) return [0, 2, 4].map((i) => {
    const canal = parseInt(hex[1].slice(i, i + 2), 16) / 255;
    return canal <= 0.04045 ? canal / 12.92 : ((canal + 0.055) / 1.055) ** 2.4;
  });
  const oklch = valor.match(/^oklch\(([\d.]+)\s+([\d.]+)\s+([\d.]+)\)$/);
  if (!oklch) throw new Error(`Cor opaca não reconhecida: ${valor}`);
  const [, L, C, H] = oklch.map(Number);
  const h = H * Math.PI / 180;
  const a = C * Math.cos(h), b = C * Math.sin(h);
  const l = (L + .3963377774 * a + .2158037573 * b) ** 3;
  const m = (L - .1055613458 * a - .0638541728 * b) ** 3;
  const s = (L - .0894841775 * a - 1.291485548 * b) ** 3;
  return [4.0767416621 * l - 3.3077115913 * m + .2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - .3413193965 * s,
    -.0041960863 * l - .7034186147 * m + 1.707614701 * s].map((v) => Math.min(1, Math.max(0, v)));
}

function bloco(seletor) {
  const inicio = css.search(seletor);
  if (inicio < 0) throw new Error(`Bloco de tema ausente: ${seletor}`);
  const abre = css.indexOf("{", inicio);
  let profundidade = 1;
  for (let i = abre + 1; i < css.length; i++) {
    if (css[i] === "{") profundidade++;
    if (css[i] === "}" && --profundidade === 0) return css.slice(abre + 1, i);
  }
  throw new Error(`Bloco sem fechamento: ${seletor}`);
}

const base = bloco(/:root\s*,\s*\.dark\s*\{/);
export const temas = [
  { nome: "escuro", corpo: base },
  { nome: "claro", corpo: `${base}\n${bloco(/^\.light\s*\{/m)}` },
].map(({ nome, corpo }) => {
  const valores = new Map();
  for (const m of corpo.matchAll(/^\s*(--[a-z0-9-]+):\s*([^;]+);/gm)) valores.set(m[1], m[2].trim());
  const cor = (token) => {
    let valor = valores.get(token);
    const visitados = new Set();
    while (valor?.startsWith("var(")) {
      if (visitados.has(valor)) throw new Error(`Alias circular: ${token}`);
      visitados.add(valor);
      valor = valores.get(valor.slice(4, -1));
    }
    if (!valor) throw new Error(`Token ausente em ${nome}: ${token}`);
    return corLinear(valor);
  };
  return { nome, valores, cor };
});

export function contraste(a, b) {
  const luminancia = (c) => .2126 * c[0] + .7152 * c[1] + .0722 * c[2];
  const x = luminancia(a), y = luminancia(b);
  return (Math.max(x, y) + .05) / (Math.min(x, y) + .05);
}
