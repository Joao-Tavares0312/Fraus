import { describe, expect, it } from "vitest";
import { MARCOS, pesosDasFases } from "./fases";

const soma = (p: ReturnType<typeof pesosDasFases>) =>
  p.frase + p.disperso + p.enxame + p.orbe + p.leitura;

describe("pesosDasFases", () => {
  it("no topo da pagina, as particulas sao a frase", () => {
    expect(pesosDasFases(0).frase).toBe(1);
  });

  it("os pesos de posicao sempre somam 1: a particula nunca fica sem destino", () => {
    for (let p = 0; p <= 1.0001; p += 0.01) expect(soma(pesosDasFases(p))).toBeCloseTo(1, 6);
  });

  it("cada marco da historia e dominado pela sua fase", () => {
    expect(pesosDasFases(MARCOS.disperso).disperso).toBe(1);
    expect(pesosDasFases(MARCOS.enxame).enxame).toBe(1);
    expect(pesosDasFases(MARCOS.orbe).orbe).toBe(1);
    expect(pesosDasFases(MARCOS.leitura).leitura).toBe(1);
  });

  it("os marcos estao em ordem: a historia nao anda para tras", () => {
    const m = Object.values(MARCOS);
    expect([...m].sort((a, b) => a - b)).toEqual(m);
  });

  it("no fecho as particulas voltam ao orbe e respiram", () => {
    const fim = pesosDasFases(1);
    expect(fim.orbe).toBe(1);
    expect(fim.respira).toBe(1);
  });

  it("na secao do analista o campo recua para nao competir com o dado", () => {
    expect(pesosDasFases(MARCOS.recuo).brilho).toBeLessThan(0.4);
    expect(pesosDasFases(MARCOS.enxame).brilho).toBe(1);
  });

  it("grampeia progresso fora de [0, 1]", () => {
    expect(pesosDasFases(-3)).toEqual(pesosDasFases(0));
    expect(pesosDasFases(7)).toEqual(pesosDasFases(1));
  });
});
