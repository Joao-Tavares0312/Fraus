import { describe, expect, it } from "vitest";
import { destinoAuth, tokenDeConvite } from "./destino-auth";

describe("retorno após autenticar por convite", () => {
  it("preserva somente o token no formato esperado", () => {
    const token = "a".repeat(43);
    expect(destinoAuth(token)).toBe(`/convite/${token}`);
  });
  it.each(["https://outro.site", "//outro.site", "../acesso", ["a".repeat(43)], null])("recusa destinos externos ou malformados %s", (valor) => {
    expect(tokenDeConvite(valor)).toBeNull();
    expect(destinoAuth(valor)).toBe("/dashboard");
  });
});
