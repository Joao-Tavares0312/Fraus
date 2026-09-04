import { describe, expect, it } from "vitest";
import { TETO_POR_CAMADA, intensidadeDaCamada, type Camada } from "./cena";

const CAMADAS: Camada[] = ["grade", "planeta", "estrelas"];

describe("intensidadeDaCamada", () => {
  it("nunca passa do teto declarado, em nenhum ponto da rolagem", () => {
    // O teto e o que o pisos.mjs vai medir. Se a curva passar dele, o portao
    // mede uma superficie mais escura que a real e devolve verde com folga
    // que nao existe -- o defeito registrado na §8.6 do DESIGN.md.
    for (const camada of CAMADAS) {
      for (let p = 0; p <= 1.0001; p += 0.01) {
        expect(intensidadeDaCamada(camada, p), `${camada} @ ${p}`)
          .toBeLessThanOrEqual(TETO_POR_CAMADA[camada]);
      }
    }
  });

  it("nunca e negativa", () => {
    for (const camada of CAMADAS) {
      for (let p = 0; p <= 1.0001; p += 0.01) {
        expect(intensidadeDaCamada(camada, p)).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("trata progresso fora de 0..1 sem estourar", () => {
    for (const camada of CAMADAS) {
      expect(intensidadeDaCamada(camada, -5)).toBeGreaterThanOrEqual(0);
      expect(intensidadeDaCamada(camada, 99)).toBeLessThanOrEqual(
        TETO_POR_CAMADA[camada],
      );
    }
  });

  it("cada camada atinge o proprio teto em algum ponto", () => {
    // Teto que nunca e alcancado e pessimismo gratuito: faria o vidro
    // engrossar sem motivo, e a §8.6 diz que a espessura cede so quando
    // precisa.
    for (const camada of CAMADAS) {
      let maximo = 0;
      for (let p = 0; p <= 1.0001; p += 0.005) {
        maximo = Math.max(maximo, intensidadeDaCamada(camada, p));
      }
      expect(maximo).toBeCloseTo(TETO_POR_CAMADA[camada], 2);
    }
  });
});
