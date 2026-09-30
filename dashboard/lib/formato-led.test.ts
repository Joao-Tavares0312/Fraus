import { describe, expect, it } from "vitest";
import { formatarSegundosLED } from "./formato";

describe("formatarSegundosLED", () => {
  it("abaixo de um minuto: so segundos, com a virgula do pt-BR", () => {
    expect(formatarSegundosLED(38)).toEqual({ valor: "38", unidade: "s" });
    expect(formatarSegundosLED(38.5)).toEqual({ valor: "38,5", unidade: "s" });
  });

  it("minutos: m:ss, com zero a esquerda nos segundos", () => {
    expect(formatarSegundosLED(72)).toEqual({ valor: "1:12", unidade: "min:s" });
    expect(formatarSegundosLED(252)).toEqual({ valor: "4:12", unidade: "min:s" });
    expect(formatarSegundosLED(65)).toEqual({ valor: "1:05", unidade: "min:s" });
  });

  it("o minuto redondo nao vira 0:60", () => {
    expect(formatarSegundosLED(59.6)).toEqual({ valor: "59,6", unidade: "s" });
    expect(formatarSegundosLED(119.6)).toEqual({ valor: "2:00", unidade: "min:s" });
  });

  it("horas: h:mm", () => {
    expect(formatarSegundosLED(3900)).toEqual({ valor: "1:05", unidade: "h:min" });
  });

  it("so produz caracteres do alfabeto do LED", () => {
    for (const s of [0, 1, 59, 60, 61, 599, 3599, 3600, 90000]) {
      expect(formatarSegundosLED(s).valor).toMatch(/^[\d,:]+$/);
    }
  });
});
