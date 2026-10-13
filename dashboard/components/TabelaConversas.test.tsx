import { describe, expect, it } from "vitest";
import { escaparCampo } from "./TabelaConversas";

describe("escaparCampo (CSV da tela)", () => {
  it("neutraliza tab e retorno no inicio, que o Excel pula antes de ler a formula", () => {
    // Auditoria de 13/10/2026: a lista da OWASP inclui \t e \r; o
    // CSV do servidor (/operacao/exportar) ja neutraliza os dois.
    expect(escaparCampo("\t=1+1")).toBe(`"'\t=1+1"`);
    expect(escaparCampo("\r=1")).toBe(`"'\r=1"`);
    expect(escaparCampo("=HYPERLINK(1)")).toBe(`"'=HYPERLINK(1)"`);
    expect(escaparCampo("chat")).toBe(`"chat"`);
  });
});
