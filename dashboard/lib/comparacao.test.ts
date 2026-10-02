import { describe, expect, it } from "vitest";
import { comSinal, fracao, milissegundos, pValor, veredito } from "./comparacao";

describe("formatação do laudo de comparação", () => {
  it("escreve fração com três casas fixas e vírgula", () => {
    expect(fracao(0.58)).toBe("0,580");
    expect(fracao(1)).toBe("1,000");
  });

  it("não medido é travessão, nunca zero", () => {
    expect(fracao(null)).toBe("—");
    expect(milissegundos(null)).toBe("—");
  });

  it("diferença sempre carrega o sinal", () => {
    expect(comSinal(0.0312)).toBe("+0,031");
    expect(comSinal(-0.2)).toBe("−0,200");
    expect(comSinal(0)).toBe("+0,000");
  });

  it("tempo vai em milissegundos inteiros acima de dez e com uma casa abaixo", () => {
    expect(milissegundos(194.6)).toBe("195 ms");
    expect(milissegundos(8.25)).toBe("8,3 ms");
  });
});

describe("p-valor", () => {
  it("p minúsculo não é escrito como zero", () => {
    expect(pValor(3e-9)).toBe("p < 0,0001");
    expect(pValor(0.0391)).toBe("p = 0,0391");
  });
});

describe("veredito da comparação", () => {
  const nomes = { bertimbau: "BERTimbau fine-tunado", laya_treinado: "Laya treinado" };
  const base = {
    candidato: "laya_treinado",
    referencia: "bertimbau",
    ic95: [0.01, 0.05] as [number, number],
    mcnemar: { so_candidato: 30, so_referencia: 10, p_valor: 0.002 },
  };

  it("intervalo que cruza o zero não nomeia vencedor", () => {
    expect(
      veredito({ ...base, diferenca_f1_macro: 0.01, ic95: [-0.02, 0.04], diferenca_demonstrada: false }, nomes),
    ).toBe("sem diferença demonstrada");
  });

  it("diferença demonstrada nomeia quem ficou à frente pelo sinal", () => {
    expect(
      veredito({ ...base, diferenca_f1_macro: 0.03, diferenca_demonstrada: true }, nomes),
    ).toBe("Laya treinado à frente");
    expect(
      veredito({ ...base, diferenca_f1_macro: -0.03, ic95: [-0.05, -0.01], diferenca_demonstrada: true }, nomes),
    ).toBe("BERTimbau fine-tunado à frente");
  });
});
