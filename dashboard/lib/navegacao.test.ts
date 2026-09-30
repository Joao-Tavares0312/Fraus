import { describe, expect, it } from "vitest";
import {
  numeroDaRota,
  rotuloNumerado,
  telaDoCaminho,
  TELAS,
} from "./navegacao";

describe("numeroDaRota", () => {
  it("numera em dois digitos, na ordem da tela", () => {
    expect(numeroDaRota("/dashboard")).toBe("01");
    expect(numeroDaRota("/dashboard/atendimentos")).toBe("02");
    expect(numeroDaRota("/dashboard/integracoes")).toBe("07");
  });

  it("rota desconhecida nao ganha numero", () => {
    expect(numeroDaRota("/dashboard/nao-existe")).toBeNull();
  });

  it("nao repete numero nem href", () => {
    const numeros = TELAS.map((t) => numeroDaRota(t.href));
    expect(new Set(numeros).size).toBe(TELAS.length);
  });
});

describe("telaDoCaminho", () => {
  it("a raiz da ferramenta so casa consigo mesma", () => {
    expect(telaDoCaminho("/dashboard")?.rotulo).toBe("Visão geral");
    expect(telaDoCaminho("/dashboard/qualquer")).toBeNull();
  });

  it("sub-rota pertence a tela pai (prefixo mais longo)", () => {
    expect(telaDoCaminho("/dashboard/atendimentos/abc-123")?.rotulo).toBe(
      "Atendimentos",
    );
  });

  it("nao confunde prefixo de palavra com sub-rota", () => {
    expect(telaDoCaminho("/dashboard/atendimentosX")).toBeNull();
  });

  it("caminho fora da ferramenta devolve null", () => {
    expect(telaDoCaminho("/")).toBeNull();
    expect(telaDoCaminho("/entrar")).toBeNull();
  });
});

describe("rotuloNumerado", () => {
  it("monta 01_VISÃO GERAL", () => {
    expect(rotuloNumerado(TELAS[0])).toBe("01_VISÃO GERAL");
    expect(rotuloNumerado(TELAS[5])).toBe("06_CONFIGURAÇÕES");
  });
});
