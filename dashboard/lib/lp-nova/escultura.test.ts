import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { criarVerticesFR } from "./escultura";

type Ponto = readonly [number, number];

/** Oraculo independente: le as curvas e a fenda do SVG oficial, nao os
 * contornos ja recortados usados pelo renderizador. Suporta os comandos
 * absolutos M/L/C/Z presentes nesse asset; mudanca de formato falha alto. */
function lerCaminho(d: string) {
  const tokens = d.match(/[A-Za-z]|-?\d+(?:\.\d+)?/g) ?? [];
  const pontos: Ponto[] = [];
  let comando = "", i = 0;
  let atual: Ponto = [0, 0];
  while (i < tokens.length) {
    if (/^[A-Za-z]$/.test(tokens[i])) comando = tokens[i++];
    if (comando === "Z") { comando = ""; continue; }
    if (comando === "M" || comando === "L") {
      atual = [Number(tokens[i++]), Number(tokens[i++])];
      pontos.push(atual);
      comando = "L";
    } else if (comando === "C") {
      const a: Ponto = [Number(tokens[i++]), Number(tokens[i++])];
      const b: Ponto = [Number(tokens[i++]), Number(tokens[i++])];
      const fim: Ponto = [Number(tokens[i++]), Number(tokens[i++])];
      for (let passo = 1; passo <= 128; passo++) {
        const t = passo / 128, u = 1 - t;
        pontos.push([
          u*u*u*atual[0] + 3*u*u*t*a[0] + 3*u*t*t*b[0] + t*t*t*fim[0],
          u*u*u*atual[1] + 3*u*u*t*a[1] + 3*u*t*t*b[1] + t*t*t*fim[1],
        ]);
      }
      atual = fim;
    } else {
      throw new Error(`Comando SVG nao coberto pelo oraculo FR: ${comando}`);
    }
  }
  return pontos;
}

function dentro(p: Ponto, poligono: readonly Ponto[]) {
  let resultado = false;
  for (let i = 0, j = poligono.length - 1; i < poligono.length; j = i++) {
    const a = poligono[i], b = poligono[j];
    if ((a[1] > p[1]) !== (b[1] > p[1]) && p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]) resultado = !resultado;
  }
  return resultado;
}

function distanciaSegmento(p: Ponto, a: Ponto, b: Ponto) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx*dx + dy*dy)));
  return Math.hypot(p[0] - a[0] - t*dx, p[1] - a[1] - t*dy);
}

function referenciaOficial() {
  const svg = readFileSync(new URL("../../public/fraus-logo.svg", import.meta.url), "utf8");
  const f = svg.match(/<g transform="matrix\(([^)]+)\)"><path d="([^"]+)"/);
  const r = svg.match(/<path d="([^"]+)" style="fill:url/);
  const corte = svg.match(/<path id="fenda" d="([^"]+)"[^>]*stroke-width:(\d+)/);
  if (!f || !r || !corte) throw new Error("Estrutura da marca oficial mudou; atualizar o oraculo explicitamente.");
  const [a, b, c, d, e, h] = f[1].split(",").map(Number);
  const formas = [lerCaminho(f[2]).map(([x, y]): Ponto => [a*x+c*y+e, b*x+d*y+h]), lerCaminho(r[1])];
  const minX = Math.min(...formas.flat().map((p) => p[0]));
  const minY = Math.min(...formas.flat().map((p) => p[1]));
  const fator = 400 / (Math.max(...formas.flat().map((p) => p[0])) - minX);
  const normalizar = ([x, y]: Ponto): Ponto => [(x-minX)*fator, (y-minY)*fator];
  return { formas: formas.map((forma) => forma.map(normalizar)), corte: lerCaminho(corte[1]).map(normalizar), raio: Number(corte[2]) * fator / 2 };
}

function frente() {
  const vertices = criarVerticesFR();
  const triangulos: Ponto[][] = [];
  for (let i = 0; i < vertices.length; i += 21) {
    // Placa frontal, sem projetar camera ou misturar arestas/dorso na ocupacao.
    if (vertices[i + 2] !== 9 || vertices[i + 3] !== 2 || vertices[i + 5] > 2) continue;
    triangulos.push([[vertices[i], vertices[i+1]], [vertices[i+7], vertices[i+8]], [vertices[i+14], vertices[i+15]]]);
  }
  return triangulos;
}

describe("silhueta extrudada do FR oficial", () => {
  it("preserva materia, vazios e ilhas apos subtrair a fenda do SVG original", () => {
    const { formas, corte, raio } = referenciaOficial();
    const triangulos = frente();
    const divergencias: Ponto[] = [];
    for (let x = 1.37; x < 400; x += 4) {
      for (let y = 1.83; y < 302; y += 4) {
        const p: Ponto = [x, y];
        const distanciaCorte = distanciaSegmento(p, corte[0], corte[1]);
        // Ignora somente a margem de discretizacao declarada (0,16 no original),
        // nao regioes vazias ou triângulos que cruzem a fenda.
        if (Math.abs(distanciaCorte - raio) < .2 || formas.some((forma) => forma.some((a, i) => distanciaSegmento(p, a, forma[(i+1) % forma.length]) < .2))) continue;
        const esperado = formas.some((forma) => dentro(p, forma)) && distanciaCorte > raio;
        const obtido = triangulos.some((triangulo) => dentro(p, triangulo));
        if (esperado !== obtido) divergencias.push(p);
      }
    }
    expect(divergencias, "Ocupacao da malha diverge do SVG, inclusive arco/haste separados pela fenda").toEqual([]);
  });

  it("mantem os cinco fragmentos visiveis e nao tampa o vazio do R ou a fenda", () => {
    const triangulos = frente();
    const materia: Ponto[] = [[40, 290], [40, 220], [100, 20], [90, 140], [310, 20], [205, 135], [375, 95], [325, 245]];
    const vazio: Ponto[] = [[310, 80], [100, 85], [40, 265], [290, 105], [290, 90], [250, 112], [390, 20]];
    for (const ponto of materia) expect(triangulos.some((triangulo) => dentro(ponto, triangulo)), `Materia ausente em ${ponto}`).toBe(true);
    for (const ponto of vazio) expect(triangulos.some((triangulo) => dentro(ponto, triangulo)), `Vazio preenchido em ${ponto}`).toBe(false);
  });

  it("fecha a extrusao com winding externo consistente para culling real", () => {
    const vertices = criarVerticesFR();
    const arestas = new Map<string, { ida: number; volta: number }>();
    for (let i = 0; i < vertices.length; i += 21) {
      const pontos = [0, 7, 14].map((offset) => `${vertices[i+offset]},${vertices[i+offset+1]},${vertices[i+offset+2]}`);
      const superficie = vertices[i+5];
      const normalZ = (vertices[i+7]-vertices[i]) * (vertices[i+15]-vertices[i+1]) - (vertices[i+8]-vertices[i+1]) * (vertices[i+14]-vertices[i]);
      if (superficie < 3) expect(normalZ, "Frente deve olhar +z").toBeGreaterThan(0);
      if (superficie === 3) expect(normalZ, "Dorso deve olhar -z").toBeLessThan(0);
      for (let j = 0; j < 3; j++) {
        const a = pontos[j], b = pontos[(j+1) % 3];
        const ida = a < b;
        const chave = `${vertices[i+3]}:${vertices[i+4]}:${ida ? a : b}|${ida ? b : a}`;
        const par = arestas.get(chave) ?? { ida: 0, volta: 0 };
        if (ida) par.ida++; else par.volta++;
        arestas.set(chave, par);
      }
    }
    // Cada aresta pertence a duas faces opostas, sem buracos nem paredes duplicadas.
    for (const [aresta, par] of arestas) expect(par, aresta).toEqual({ ida: 1, volta: 1 });
  });
});
