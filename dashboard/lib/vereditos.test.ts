import { describe, expect, it } from "vitest";
import { descreverVeredito, ordemDoVeredito } from "./vereditos";

/**
 * O painel de Entregas caia inteiro com um veredito que a tela nao conhecia: o
 * `switch` devolvia `undefined` e a desestruturacao lancava. "vazao" e gravado
 * pela API desde que o webhook ganhou teto por fonte (429), e a tela nunca
 * soube dele.
 */
describe("descreverVeredito", () => {
  it("conhece o veredito de vazao (429), em cor de aviso", () => {
    const { rotulo, plural, cor } = descreverVeredito("vazao");
    expect(rotulo).toContain("teto de envios por minuto");
    expect(plural).toContain("teto de envios por minuto");
    expect(cor).toBe("text-warning-rich-text");
  });

  it("conhece a falha interna (500), no vermelho de defeito da maquina", () => {
    const { rotulo, cor } = descreverVeredito("erro");
    expect(rotulo).toBe("falha interna da API");
    expect(cor).toBe("text-detrator-texto");
  });

  it("veredito desconhecido mostra o valor cru em vez de quebrar", () => {
    const { rotulo, plural, cor } = descreverVeredito("veredito_do_futuro");
    expect(rotulo).toBe("veredito desconhecido: veredito_do_futuro");
    expect(plural).toBe("com veredito desconhecido (veredito_do_futuro)");
    expect(cor).toBe("text-muted-foreground");
  });

  it("os que ja existiam continuam como eram", () => {
    expect(descreverVeredito("aceita").plural).toBe("aceitas");
    expect(descreverVeredito("sem_segredo").cor).toBe("text-detrator-texto");
  });
});

describe("ordemDoVeredito", () => {
  it("o desconhecido vai para o fim, depois de todos os conhecidos", () => {
    expect(ordemDoVeredito("aceita")).toBe(0);
    expect(ordemDoVeredito("veredito_do_futuro")).toBeGreaterThan(
      ordemDoVeredito("erro"),
    );
  });
});
