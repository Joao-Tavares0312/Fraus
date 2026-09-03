import { describe, expect, it } from "vitest";

import { categoriaDaNota, distribuicaoDeNotas, FAIXAS_NPS } from "./derivacoes";
import type { ResumoConversa } from "./api";

/**
 * A invariante 4: a faixa de NPS vigente e passada POR PARAMETRO, nunca
 * digitada de novo. Ate 03/09/2026 `categoriaDaNota` tinha `<= 6` e `<= 8` no
 * corpo, e isso rodava no caminho FELIZ da tela inicial -- um operador que
 * mexesse em Configuracoes via a mesma tela dar dois vereditos para o mesmo
 * atendimento: a etiqueta da linha com as faixas novas, a cor da barra com as
 * antigas.
 */

/** Faixas deslocadas: o operador endureceu o criterio de promotor. */
const FAIXAS_APERTADAS: Record<string, [number, number]> = {
  detrator: [0, 7],
  neutro: [8, 9],
  promotor: [10, 10],
};

function resumo(nota: number | null): ResumoConversa {
  return { nota } as ResumoConversa;
}

describe("categoria segue as faixas vigentes", () => {
  it("sem faixas, cai no padrao de fabrica", () => {
    expect(categoriaDaNota(6)).toBe("detrator");
    expect(categoriaDaNota(7)).toBe("neutro");
    expect(categoriaDaNota(8)).toBe("neutro");
    expect(categoriaDaNota(9)).toBe("promotor");
  });

  it("com faixas vigentes, elas mandam -- e discordam da fabrica", () => {
    // As notas em que as duas configuracoes divergem. Se o parametro fosse
    // ignorado, este teste passaria com os valores da fabrica.
    expect(categoriaDaNota(7, FAIXAS_APERTADAS)).toBe("detrator");
    expect(categoriaDaNota(9, FAIXAS_APERTADAS)).toBe("neutro");
    expect(categoriaDaNota(10, FAIXAS_APERTADAS)).toBe("promotor");
  });

  it("as pontas de cada faixa sao inclusivas, como o servidor grava", () => {
    for (const { categoria, de, ate } of FAIXAS_NPS) {
      expect(categoriaDaNota(de)).toBe(categoria);
      expect(categoriaDaNota(ate)).toBe(categoria);
    }
  });
});

describe("distribuicao colore as barras pelas faixas vigentes", () => {
  const notas = [0, 5, 7, 9, 10].map(resumo);

  it("repassa as faixas para cada barra", () => {
    const { barras } = distribuicaoDeNotas(notas, FAIXAS_APERTADAS);
    expect(barras[7].categoria).toBe("detrator");
    expect(barras[9].categoria).toBe("neutro");
    expect(barras[10].categoria).toBe("promotor");
  });

  it("sem faixas do servidor, usa a fabrica -- e nao um numero inventado", () => {
    const { barras } = distribuicaoDeNotas(notas);
    expect(barras[7].categoria).toBe("neutro");
    expect(barras[9].categoria).toBe("promotor");
  });

  it("ausencia de nota nao vira barra: ela e contada a parte", () => {
    // Invariante 2. Nota nula nao pode engordar a barra do zero.
    const { barras, semSinal } = distribuicaoDeNotas(
      [resumo(null), resumo(null), resumo(0)],
      FAIXAS_APERTADAS,
    );
    expect(semSinal).toBe(2);
    expect(barras[0].quantidade).toBe(1);
  });
});
