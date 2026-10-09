import { describe, expect, it } from "vitest";
import { MARCOS, pesosDasFases } from "./fases";
import { estadoDoOrbe } from "./orbe";

const em = (p: number, cinza = 0) => estadoDoOrbe(pesosDasFases(p), cinza);

describe("estadoDoOrbe", () => {
  it("no hero o orbe e grande, no lugar e em equilibrio de cor", () => {
    const o = em(MARCOS.frase);
    expect(o.escala).toBe(1);
    expect(o.noCanto).toBe(0);
    expect(o.dito).toBeCloseTo(o.medido);
    expect(o.tracos).toBe(1);
  });

  it("na mascara ele encolhe para o canto e os tracos baixam: o rosto precisa ler", () => {
    const o = em(MARCOS.mascara);
    expect(o.escala).toBeLessThan(0.3);
    expect(o.noCanto).toBe(1);
    expect(o.tracos).toBeLessThan(0.5);
  });

  it("no fusor o azul do medido domina", () => {
    const o = em(MARCOS.orbe);
    expect(o.medido).toBeGreaterThan(o.dito);
    expect(o.noCanto).toBe(0);
  });

  it("leitura sem sinal: cinza, parado e sem o canal do dito -- ausencia fora da escala", () => {
    const o = em(MARCOS.leitura, 1);
    expect(o.saturacao).toBe(0);
    expect(o.afastamento).toBe(0);
    expect(o.apagaDito).toBe(1);
    const comSinal = em(MARCOS.leitura, 0);
    expect(comSinal.saturacao).toBe(1);
    expect(comSinal.apagaDito).toBe(0);
  });

  it("no fecho ele volta grande e o ambar do dito volta a dominar", () => {
    const o = em(MARCOS.fecho);
    expect(o.escala).toBeCloseTo(1);
    expect(o.dito).toBeGreaterThan(o.medido);
  });

  it("todo canal e finito e sem salto ao longo da rolagem", () => {
    let anterior = em(0);
    for (let p = 0.005; p <= 1.0001; p += 0.005) {
      const o = em(p, p > 0.6 ? 1 : 0);
      for (const [canal, v] of Object.entries(o)) {
        expect(Number.isFinite(v), canal).toBe(true);
        if (canal !== "saturacao" && canal !== "afastamento" && canal !== "apagaDito")
          expect(Math.abs(v - anterior[canal as keyof typeof o]), `${canal} em ${p}`).toBeLessThan(0.2);
      }
      anterior = o;
    }
  });
});
