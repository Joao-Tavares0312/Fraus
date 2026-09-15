import { describe, expect, it } from "vitest";

import {
  LIMIAR_DISPUTA,
  ORDEM_EMOCOES,
  disputaDasClasses,
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
