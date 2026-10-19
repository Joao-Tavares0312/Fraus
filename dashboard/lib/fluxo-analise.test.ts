import { describe, expect, it } from "vitest";
import { deveSalvar, proximoPasso } from "./fluxo-analise";

describe("fluxo da tela Analisar", () => {
  it("leitura confiável segue direto para a análise", () => {
    expect(proximoPasso({ confiavel: true })).toBe("analisar");
  });

  it("leitura duvidosa para na conferência de colunas", () => {
    expect(proximoPasso({ confiavel: false })).toBe("conferir");
  });

  it("salva sempre que há horário", () => {
    expect(deveSalvar({ tem_tempo: true })).toBe(true);
  });

  it("sem horário não salva: não há nota para somar aos indicadores", () => {
    expect(deveSalvar({ tem_tempo: false })).toBe(false);
  });
});
