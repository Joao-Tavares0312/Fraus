import { describe, expect, it } from "vitest";
import { FAMILIAS_DO_VETOR } from "../../components/lp/fatos";
import { distribuirEnxames } from "./enxames";

describe("distribuirEnxames", () => {
  it.each([4000, 16000, 120000, 7])("fecha a soma exata em %i particulas", (total) => {
    const soma = distribuirEnxames(total).reduce((acc, e) => acc + e.particulas, 0);
    expect(soma).toBe(total);
  });

  it("segue a ordem e as chaves de FAMILIAS_DO_VETOR", () => {
    expect(distribuirEnxames(4000).map((e) => e.chave)).toEqual(FAMILIAS_DO_VETOR.map((f) => f.chave));
  });

  it("guarda faixas contiguas: cada enxame comeca onde o anterior termina", () => {
    const enxames = distribuirEnxames(16000);
    let esperado = 0;
    for (const e of enxames) {
      expect(e.inicio).toBe(esperado);
      esperado += e.particulas;
    }
  });

  it("da mais particulas a familia com mais features (tempo 7 contra lexico 3)", () => {
    const porChave = Object.fromEntries(distribuirEnxames(16000).map((e) => [e.chave, e.particulas]));
    expect(porChave.tempo).toBeGreaterThan(porChave.lexico);
    // proporcao real: 7/39 do total, com folga de uma particula pelo arredondamento
    expect(Math.abs(porChave.tempo - (16000 * 7) / 39)).toBeLessThanOrEqual(1);
  });

  it("poe os centros num circulo em volta do meio da tela", () => {
    for (const e of distribuirEnxames(4000)) {
      const raio = Math.hypot(e.centro[0] - 0.5, e.centro[1] - 0.5);
      expect(raio).toBeCloseTo(0.32, 5);
    }
  });

  it("recusa menos particulas que familias: um enxame vazio mentiria a contagem", () => {
    expect(() => distribuirEnxames(6)).toThrow(RangeError);
  });
});
