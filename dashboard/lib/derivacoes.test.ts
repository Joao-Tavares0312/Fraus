import { describe, expect, it } from "vitest";

import {
  categoriaDaNota,
  distribuicaoDeNotas,
  FAIXAS_NPS,
  indicadoresDoPeriodo,
  legendaDasFaixas,
  pesoPorSinal,
  polaridadeDoEmoji,
} from "./derivacoes";
import type { DetalheConversa, ResumoConversa } from "./api";

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

/**
 * Falso containment no PLANO B (o agregado do servidor caiu).
 *
 * O numero e o cruzamento de contido x detrator, e o unico jeito de errar sem
 * quebrar nada e contar o detrator ESCALADO -- que nao foi contido, e portanto
 * nao e sucesso falso nenhum.
 */
function detalhe(
  categoria: "detrator" | "neutro" | "promotor" | null,
  escalou: boolean,
): DetalheConversa {
  return { categoria, escalou_para_humano: escalou } as DetalheConversa;
}

describe("falso containment do plano B", () => {
  it("conta o contido que saiu detrator", () => {
    const saida = indicadoresDoPeriodo(
      [],
      [detalhe("detrator", false), detalhe("promotor", false)],
    );
    expect(saida.falsoContainment).toBeCloseTo(50);
    expect(saida.contidosComSinal).toBe(2);
  });

  it("nao conta o detrator ESCALADO -- escalar nao e conter", () => {
    const saida = indicadoresDoPeriodo(
      [],
      [detalhe("detrator", true), detalhe("promotor", false)],
    );
    expect(saida.falsoContainment).toBeCloseTo(0);
    expect(saida.contidosComSinal).toBe(1);
  });

  it("contido sem sinal fica fora das duas pontas da fracao", () => {
    const saida = indicadoresDoPeriodo(
      [],
      [detalhe(null, false), detalhe("detrator", false)],
    );
    expect(saida.falsoContainment).toBeCloseTo(100);
    expect(saida.contidosComSinal).toBe(1);
  });

  it("sem nenhum contido pontuado e null, nunca 0", () => {
    expect(indicadoresDoPeriodo([], []).falsoContainment).toBeNull();
    expect(
      indicadoresDoPeriodo([], [detalhe(null, false)]).falsoContainment,
    ).toBeNull();
  });
});

describe("pesoPorSinal omite a familia que nao esta no vetor", () => {
  /**
   * A ironia saiu do vetor em 04/09/2026 e a legenda da tela Modelo continuava
   * listando "Ironia · 0% do peso total". Zero e uma MEDIDA; a familia que nao
   * tem feature nenhuma nao foi medida, e ausencia nao e zero (invariante 2).
   */
  const IMPORTANCIAS = {
    texto_prob_satisfeito_media: 3,
    emoji_score_medio: 1,
    incongruencia_polaridade: 1,
    // Presente no vetor com peso ZERO: isto e medida, e fica na legenda.
    estilo_frac_caixa_alta: 0,
  };

  it("nao lista ironia quando nenhuma feature `ironia_*` veio", () => {
    const sinais = pesoPorSinal(IMPORTANCIAS).map((peso) => peso.sinal);
    expect(sinais).not.toContain("ironia");
    expect(sinais).not.toContain("tempo");
    expect(sinais).not.toContain("outros");
  });

  it("lista a incongruencia, que esta no vetor", () => {
    const incongruencia = pesoPorSinal(IMPORTANCIAS).find(
      (peso) => peso.sinal === "incongruencia",
    );
    expect(incongruencia?.fracao).toBeCloseTo(0.2);
  });

  it("familia presente com peso zero continua na legenda, com 0", () => {
    const estilo = pesoPorSinal(IMPORTANCIAS).find(
      (peso) => peso.sinal === "estilo",
    );
    expect(estilo?.fracao).toBe(0);
  });

  it("mantem a ordem canonica das familias", () => {
    expect(pesoPorSinal(IMPORTANCIAS).map((peso) => peso.sinal)).toEqual([
      "texto",
      "emoji",
      "estilo",
      "incongruencia",
    ]);
  });
});

describe("polaridadeDoEmoji", () => {
  it("emoji do ranking devolve a polaridade publicada", () => {
    expect(polaridadeDoEmoji("😂")).toBeCloseTo(0.221);
  });

  it("emoji FORA do ranking e null, nunca 0", () => {
    // 🫠 e de 2021; o Emoji Sentiment Ranking foi anotado em 2015. "0.00 no
    // ranking" afirmava uma neutralidade que ninguem mediu.
    expect(polaridadeDoEmoji("🫠")).toBeNull();
  });
});

describe("legendaDasFaixas sai das faixas vigentes", () => {
  it("escreve os cortes que o operador configurou, nao os de fabrica", () => {
    expect(legendaDasFaixas(FAIXAS_APERTADAS).map((f) => f.rotulo)).toEqual([
      "0–7 detrator",
      "8–9 neutro",
      "10 promotor",
    ]);
  });

  it("sem faixas vigentes, degrada para o padrao de fabrica declarado", () => {
    expect(legendaDasFaixas(undefined).map((f) => f.rotulo)).toEqual(
      FAIXAS_NPS.map((f) => f.rotulo),
    );
  });

  it("categoria sem faixa na resposta nao ganha numero inventado", () => {
    const legenda = legendaDasFaixas({ detrator: [0, 6] });
    expect(legenda.map((f) => f.rotulo)).toEqual([
      "0–6 detrator",
      "neutro",
      "promotor",
    ]);
  });
});
