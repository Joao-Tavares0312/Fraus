import { describe, expect, it } from "vitest";
import {
  FATOR_MAXIMO_POR_CAMADA,
  coreografiaValeEm,
  intensidadeDaCamada,
  type Camada,
} from "./cena";

const CAMADAS: Camada[] = ["grade", "planeta", "estrelas"];

describe("intensidadeDaCamada", () => {
  it("nunca passa do maximo declarado, em nenhum ponto da rolagem", () => {
    // O fator maximo e o que o pisos.mjs vai multiplicar pelo token de
    // opacidade do tema. Se a curva passar dele, o portao mede uma
    // superficie mais escura que a real e devolve verde com folga que nao
    // existe -- o defeito registrado na §8.6 do DESIGN.md.
    for (const camada of CAMADAS) {
      for (let p = 0; p <= 1.0001; p += 0.01) {
        expect(intensidadeDaCamada(camada, p), `${camada} @ ${p}`)
          .toBeLessThanOrEqual(FATOR_MAXIMO_POR_CAMADA[camada]);
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
        FATOR_MAXIMO_POR_CAMADA[camada],
      );
    }
  });

  it("trata NaN grampeando para o extremo seguro (cena apagada)", () => {
    // NaN nao e hipotetico: e o que scrollY / rolavel produz quando a
    // pagina e curta demais para rolar (rolavel = 0) ou antes do layout
    // medir. Math.max/Math.min propagam NaN em vez de grampear -- o extremo
    // seguro e 0, nunca claro demais.
    for (const camada of CAMADAS) {
      expect(intensidadeDaCamada(camada, NaN)).toBe(0);
    }
  });

  it("trata Infinity e -Infinity sem estourar o maximo", () => {
    for (const camada of CAMADAS) {
      expect(intensidadeDaCamada(camada, Infinity)).toBeLessThanOrEqual(
        FATOR_MAXIMO_POR_CAMADA[camada],
      );
      expect(intensidadeDaCamada(camada, -Infinity)).toBeGreaterThanOrEqual(0);
    }
  });

  it("todo fator vale 1 no progresso 0 -- o heroi fica identico ao de hoje", () => {
    // Correcao de 04/09/2026: a primeira curva apagava planeta e estrelas no
    // heroi (nasciam em 0), matando o sol listrado exatamente na unica tela
    // que ja funcionava antes desta feature existir. Este teste e a trava
    // contra reintroduzir isso -- p=0 tem que devolver o teto de CADA
    // camada, sem excecao.
    for (const camada of CAMADAS) {
      expect(intensidadeDaCamada(camada, 0)).toBe(FATOR_MAXIMO_POR_CAMADA[camada]);
    }
  });

  it("cada camada atinge o proprio maximo em algum ponto", () => {
    // Maximo que nunca e alcancado e pessimismo gratuito: faria o vidro
    // engrossar sem motivo, e a §8.6 diz que a espessura cede so quando
    // precisa.
    for (const camada of CAMADAS) {
      let maximo = 0;
      for (let p = 0; p <= 1.0001; p += 0.005) {
        maximo = Math.max(maximo, intensidadeDaCamada(camada, p));
      }
      expect(maximo).toBeCloseTo(FATOR_MAXIMO_POR_CAMADA[camada], 2);
    }
  });
});

describe("coreografiaValeEm", () => {
  it("vale na LP", () => {
    expect(coreografiaValeEm("/")).toBe(true);
  });

  it("nao vale em rota nenhuma do Operate", () => {
    // Regressao do achado de 04/09/2026: o Atelier mora no layout raiz,
    // compartilhado pela LP e pela ferramenta, e a coreografia so pode
    // acender fora da vitrine se esta funcao disser que sim.
    for (const rota of [
      "/dashboard",
      "/dashboard/atendimentos",
      "/dashboard/atendimentos/123",
      "/dashboard/modelo",
      "/dashboard/grafo",
      "/dashboard/analisar",
      "/dashboard/integracoes",
      "/dashboard/configuracoes",
      "/entrar",
      "/cadastrar",
    ]) {
      expect(coreografiaValeEm(rota)).toBe(false);
    }
  });
});
