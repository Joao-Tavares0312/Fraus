import { describe, expect, it } from "vitest";
import { formatarDuracaoCompacta } from "./formato";

describe("formatarDuracaoCompacta", () => {
  it("abaixo de um minuto: so segundos, com a virgula do pt-BR", () => {
    expect(formatarDuracaoCompacta(38)).toEqual({ valor: "38", unidade: "s" });
    expect(formatarDuracaoCompacta(38.5)).toEqual({ valor: "38,5", unidade: "s" });
  });

  it("minutos: m:ss, com zero a esquerda nos segundos", () => {
    expect(formatarDuracaoCompacta(72)).toEqual({ valor: "1:12", unidade: "min:s" });
    expect(formatarDuracaoCompacta(252)).toEqual({ valor: "4:12", unidade: "min:s" });
    expect(formatarDuracaoCompacta(65)).toEqual({ valor: "1:05", unidade: "min:s" });
  });

  it("o minuto redondo nao vira 0:60", () => {
    expect(formatarDuracaoCompacta(59.6)).toEqual({ valor: "59,6", unidade: "s" });
    expect(formatarDuracaoCompacta(119.6)).toEqual({ valor: "2:00", unidade: "min:s" });
  });

  it("horas: h:mm", () => {
    expect(formatarDuracaoCompacta(3900)).toEqual({ valor: "1:05", unidade: "h:min" });
  });
  it("preserva zero como duração observada", () => {
    expect(formatarDuracaoCompacta(0)).toEqual({ valor: "0", unidade: "s" });
  });

});
