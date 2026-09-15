import { describe, expect, it } from "vitest";
import { lerProgresso } from "./repontuacao";

describe("lerProgresso", () => {
  it("404 do servidor e nada rodando", () => {
    expect(lerProgresso(null)).toEqual({ tipo: "parado" });
  });

  it("rodando carrega as contagens do servidor e a fracao so para a barra", () => {
    expect(lerProgresso({ estado: "rodando", total: 62, feitas: 31, erro: null })).toEqual({
      tipo: "rodando",
      feitas: 31,
      total: 62,
      fracao: 0.5,
    });
  });

  it("banco vazio rodando nao divide por zero", () => {
    const leitura = lerProgresso({ estado: "rodando", total: 0, feitas: 0, erro: null });
    expect(leitura).toMatchObject({ tipo: "rodando", fracao: 0 });
  });

  it("falha diz onde parou e por que", () => {
    expect(
      lerProgresso({ estado: "falhou", total: 10, feitas: 4, erro: "RuntimeError: modelo caiu" }),
    ).toEqual({ tipo: "falhou", feitas: 4, total: 10, mensagem: "RuntimeError: modelo caiu" });
  });

  it("falha sem mensagem nao fica muda", () => {
    const leitura = lerProgresso({ estado: "falhou", total: 1, feitas: 0, erro: null });
    expect(leitura).toMatchObject({ tipo: "falhou" });
    if (leitura.tipo === "falhou") expect(leitura.mensagem.length).toBeGreaterThan(0);
  });
});
