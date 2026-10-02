import { describe, expect, it } from "vitest";
import { formatarComSinal, formatarNps, formatarSegundos } from "./formato";

/**
 * As BORDAS dos dois formatadores que mais aparecem na tela. Os dois erravam
 * exatamente onde o arredondamento cruza uma fronteira, e nenhum dos dois tinha
 * teste: `-0` e `60 s` nao aparecem em build nem em lint.
 */

describe("formatarNps", () => {
  it("o sinal e informacao: positivo leva +, negativo leva -", () => {
    expect(formatarNps(12.34)).toBe("+12,3");
    expect(formatarNps(-12.34)).toBe("-12,3");
  });

  it("zero nao tem sinal", () => {
    expect(formatarNps(0)).toBe("0");
  });

  it("negativo que arredonda para zero e 0, nunca -0", () => {
    // Math.round(-0.4) e -0, e o Intl escreve o zero negativo como "-0": um
    // NPS "negativo" que nao e negativo em casa decimal nenhuma da tela.
    expect(formatarNps(-0.04)).toBe("0");
    expect(formatarNps(0.04)).toBe("0");
  });
});

describe("formatarSegundos", () => {
  it("abaixo de um minuto: segundos, com uma casa", () => {
    expect(formatarSegundos(7)).toBe("7 s");
    expect(formatarSegundos(38.5)).toBe("38,5 s");
  });

  it("minutos e segundos", () => {
    expect(formatarSegundos(60)).toBe("1 min");
    expect(formatarSegundos(72)).toBe("1 min 12 s");
  });

  it("o resto nunca arredonda para 60 s", () => {
    expect(formatarSegundos(119.6)).toBe("2 min");
    expect(formatarSegundos(59.96)).toBe("1 min");
  });

  it("os minutos nunca arredondam para 60 min", () => {
    expect(formatarSegundos(3599.7)).toBe("1 h 0 min");
  });

  it("horas e minutos", () => {
    expect(formatarSegundos(3900)).toBe("1 h 5 min");
  });
});

describe("formatarComSinal", () => {
  it("valor que arredonda para zero nao leva sinal", () => {
    // A tela de Analisar mostrava "−0" na contribuicao da caixa alta (02/10/2026).
    expect(formatarComSinal(-0.001, 2)).toBe("0");
    expect(formatarComSinal(0.004, 2)).toBe("0");
    expect(formatarComSinal(-0, 2)).toBe("0");
  });
  it("positivo leva +, negativo leva o sinal de menos tipografico", () => {
    expect(formatarComSinal(2.851, 2)).toBe("+2,85");
    expect(formatarComSinal(-3.08, 2)).toBe("−3,08");
    expect(formatarComSinal(-0.006, 2)).toBe("−0,01");
  });
});
