import { describe, expect, it } from "vitest";

import {
  LIMIAR_DISPUTA,
  ORDEM_EMOCOES,
  disputaDasClasses,
  emocoesPorValor,
  separarEmocoes,
} from "./partitura";

/**
 * A logica da partitura da fala, fora do componente para poder ser testada.
 *
 * Duas decisoes daqui mudam o que o analista le, e por isso tem teste: QUANDO a
 * disputa acende (a margem entre a 1a e a 2a classe, nunca uma "confianca" que
 * o modelo nao calibrado nao tem) e QUAIS emocoes ficam a vista.
 */
describe("disputaDasClasses", () => {
  it("acha a vencedora, a segunda e a margem entre elas", () => {
    const d = disputaDasClasses({ insatisfeito: 0.02, neutro: 0.52, satisfeito: 0.46 });
    expect(d.vencedora).toBe("neutro");
    expect(d.segunda).toBe("satisfeito");
    expect(d.margem).toBeCloseTo(0.06);
    expect(d.disputa).toBe(true);
  });

  it("classe dominante nao acende disputa", () => {
    const d = disputaDasClasses({ insatisfeito: 0.04, neutro: 0.09, satisfeito: 0.87 });
    expect(d.vencedora).toBe("satisfeito");
    expect(d.disputa).toBe(false);
  });

  it("o limiar e estrito: margem igual ao limiar nao e disputa", () => {
    const d = disputaDasClasses({ insatisfeito: 0, neutro: 0.425, satisfeito: 0.425 + LIMIAR_DISPUTA });
    expect(d.disputa).toBe(false);
  });

  it("empate exato desempata pela ordem fixa das classes, sem sortear", () => {
    const d = disputaDasClasses({ insatisfeito: 0.2, neutro: 0.4, satisfeito: 0.4 });
    expect(d.vencedora).toBe("neutro");
    expect(d.margem).toBe(0);
    expect(d.disputa).toBe(true);
  });
});

describe("separarEmocoes", () => {
  const emocao = {
    alegria: 0.58, surpresa: 0.14, neutro: 0.11, tristeza: 0.03,
    medo: 0.02, raiva: 0.07, nojo: 0.05, desprezo: 0.059,
  };

  it("mostra as duas maiores e recolhe o resto na ordem canonica", () => {
    const { visiveis, recolhidas } = separarEmocoes(emocao);
    expect(visiveis.map(([nome]) => nome)).toEqual(["alegria", "surpresa"]);
    expect(recolhidas.map(([nome]) => nome)).toEqual(
      ORDEM_EMOCOES.filter((nome) => !["alegria", "surpresa"].includes(nome)),
    );
  });

  it("desprezo nunca disputa as visiveis: e derivado, vem por ultimo no recolhido", () => {
    const { visiveis, desprezo } = separarEmocoes({ ...emocao, desprezo: 0.9 });
    expect(visiveis.map(([nome]) => nome)).not.toContain("desprezo");
    expect(desprezo).toBe(0.9);
  });

  it("sem desprezo na resposta, ele fica ausente, nao zero", () => {
    const semDesprezo: Record<string, number> = { ...emocao };
    delete semDesprezo.desprezo;
    expect(separarEmocoes(semDesprezo).desprezo).toBeNull();
  });

  it("emocao que a API nao conhece vai para o fim, sem sumir", () => {
    const { recolhidas } = separarEmocoes({ ...emocao, confianca: 0.01 });
    expect(recolhidas.at(-1)?.[0]).toBe("confianca");
  });
});

describe("formatarProbabilidade", () => {
  it("escreve como a pauta: sem zero a esquerda, virgula decimal, 1,00 no topo", async () => {
    const { formatarProbabilidade } = await import("./partitura");
    expect(formatarProbabilidade(0.8712)).toBe(",87");
    expect(formatarProbabilidade(0.004)).toBe(",00");
    expect(formatarProbabilidade(0.999)).toBe("1,00");
  });
});

describe("separarEmocoes com todas a vista", () => {
  it("mostra as sete na ordem canonica e nao recolhe nada", async () => {
    const { separarEmocoes, ORDEM_EMOCOES } = await import("./partitura");
    const emocao = { alegria: 0.98, surpresa: 0.001, neutro: 0.01, tristeza: 0.002, medo: 0.001, raiva: 0.003, nojo: 0.001, desprezo: 0.002 };
    const { visiveis, recolhidas, desprezo } = separarEmocoes(emocao, Infinity);
    expect(visiveis.map(([nome]) => nome)).toEqual([...ORDEM_EMOCOES]);
    expect(recolhidas).toEqual([]);
    expect(desprezo).toBe(0.002);
  });
});

/**
 * Desde 13/11/2026 a leitura por fala sao tres graficos, e o de emocao lista
 * da MAIOR para a menor (a primeira linha responde "qual emocao?").
 */
describe("emocoesPorValor", () => {
  const emocao = {
    alegria: 0.05, surpresa: 0.06, neutro: 0.19, tristeza: 0.21,
    medo: 0.02, raiva: 0.38, nojo: 0.09, desprezo: 0.18,
  };

  it("ordena da maior para a menor e nomeia a dominante", () => {
    const { dominante, visiveis, recolhidas } = emocoesPorValor(emocao, Infinity);
    expect(dominante).toEqual(["raiva", 0.38]);
    expect(visiveis.map(([nome]) => nome)).toEqual([
      "raiva", "tristeza", "neutro", "nojo", "surpresa", "alegria", "medo",
    ]);
    expect(recolhidas).toEqual([]);
  });

  it("recolhe o que passa do corte, ainda da maior para a menor", () => {
    const { visiveis, recolhidas } = emocoesPorValor(emocao, 2);
    expect(visiveis.map(([nome]) => nome)).toEqual(["raiva", "tristeza"]);
    expect(recolhidas.map(([nome]) => nome)).toEqual(["neutro", "nojo", "surpresa", "alegria", "medo"]);
  });

  it("empate desempata pela ordem canonica, sem sortear", () => {
    const { visiveis } = emocoesPorValor({ alegria: 0.5, medo: 0.5 }, Infinity);
    expect(visiveis.map(([nome]) => nome)).toEqual(["medo", "alegria"]);
  });

  it("desprezo nunca e dominante nem entra na lista: e derivado, sai a parte", () => {
    const { dominante, visiveis, recolhidas, desprezo } = emocoesPorValor({ ...emocao, desprezo: 0.99 }, 2);
    expect(dominante?.[0]).toBe("raiva");
    expect([...visiveis, ...recolhidas].map(([nome]) => nome)).not.toContain("desprezo");
    expect(desprezo).toBe(0.99);
  });

  it("desprezo ausente e null, nunca zero; sem emocao treinada nao ha dominante", () => {
    expect(emocoesPorValor({ raiva: 0.4 }).desprezo).toBeNull();
    expect(emocoesPorValor({ desprezo: 0.3 }).dominante).toBeNull();
  });
});
