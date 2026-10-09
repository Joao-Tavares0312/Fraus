import { describe, expect, it } from "vitest";
import { FAMILIAS_DO_VETOR, FATOS_DO_MODELO } from "../../components/lp/fatos";
import { MASCARA, nosDasFeatures, pontoDaMascara } from "./constelacao";
import { aleatorioComSemente } from "./quadro";

const dentroDoOval = (x: number, y: number) => (x / MASCARA.rx) ** 2 + (y / MASCARA.ry) ** 2 <= 1.0001;
const noVazio = (x: number, y: number) =>
  MASCARA.vazios.some(([vx, vy, ax, ay]) => ((x - vx) / ax) ** 2 + ((y - vy) / ay) ** 2 < 1);

describe("pontoDaMascara", () => {
  const pontos = Array.from({ length: 4000 }, ((r) => () => pontoDaMascara(r))(aleatorioComSemente(3)));

  it("todo ponto cai dentro do oval (a borda tem folga de 2%)", () => {
    expect(pontos.every(([x, y]) => (x / MASCARA.rx) ** 2 + (y / MASCARA.ry) ** 2 <= 1.05)).toBe(true);
  });
  it("nenhum ponto preenche olho ou boca: os vazios sao a mascara", () => {
    expect(pontos.filter(([x, y]) => dentroDoOval(x, y) && noVazio(x, y))).toHaveLength(0);
  });
  it("os dois lados aparecem: metade dito, metade medido", () => {
    const esquerda = pontos.filter(([x]) => x < 0).length / pontos.length;
    expect(esquerda).toBeGreaterThan(0.4);
    expect(esquerda).toBeLessThan(0.6);
  });
});

describe("nosDasFeatures", () => {
  const nos = nosDasFeatures();
  it("um no por feature", () => {
    expect(nos).toHaveLength(FATOS_DO_MODELO.features);
  });
  it("agrupados na contagem real de cada familia, na ordem do vetor", () => {
    const contagem = FAMILIAS_DO_VETOR.map((f) => nos.filter((n) => n.familia === f.chave).length);
    expect(contagem).toEqual(FAMILIAS_DO_VETOR.map((f) => f.qtd));
  });
  it("famílias separadas por folga: o vao entre familias e maior que entre vizinhos", () => {
    const ang = nos.map((n) => Math.atan2(n.y, n.x));
    const passo = (i: number) => Math.abs(ang[i + 1] - ang[i]);
    const dentro = passo(0); // texto 0 -> texto 1
    const entre = passo(FAMILIAS_DO_VETOR[0].qtd - 1); // ultimo texto -> primeiro emoji
    expect(entre).toBeGreaterThan(dentro * 1.5);
  });
});
