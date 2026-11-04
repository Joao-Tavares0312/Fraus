import { describe, expect, it } from "vitest";
import { erroEmFrase, erroParaTela, mostraDetalheDoErro } from "./erro-publico";

describe("erroParaTela", () => {
  const tecnico = "A API respondeu 500 em /conversas";

  it("mostra o detalhe tecnico para dev", () => {
    expect(erroParaTela(tecnico, true)).toBe(tecnico);
  });

  it("troca rota e status por uma frase humana para o cliente", () => {
    const frase = erroParaTela(tecnico, false);
    expect(frase).not.toContain("500");
    expect(frase).not.toContain("/conversas");
    expect(frase).toContain("Tente de novo");
  });

  it("mantem a falha de conexao, que o EstadoVazio reconhece pela frase", () => {
    const fora = "API não respondeu em http://localhost:8000. Algo mais.";
    expect(erroParaTela(fora, false)).toBe(fora);
  });
});

describe("erroEmFrase", () => {
  it("fecha o erro tecnico com ponto, para o texto seguinte nao colar nele", () => {
    expect(erroEmFrase("A API respondeu 500 em /fontes", true)).toBe("A API respondeu 500 em /fontes.");
  });

  it("nao duplica o ponto da frase do cliente", () => {
    const frase = erroEmFrase("A API respondeu 500 em /fontes", false);
    expect(frase).not.toContain("/fontes");
    expect(frase.endsWith("..")).toBe(false);
  });
});

describe("mostraDetalheDoErro", () => {
  it("so mostra o detalhe para dev ou quando a API esta fora", () => {
    expect(mostraDetalheDoErro("A API respondeu 500", true)).toBe(true);
    expect(mostraDetalheDoErro("A API respondeu 500", false)).toBe(false);
    expect(mostraDetalheDoErro("API não respondeu em http://x. Algo.", false)).toBe(true);
  });
});
