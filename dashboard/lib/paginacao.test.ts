import { describe, expect, it } from "vitest";
import { limitarPagina } from "./paginacao";

describe("limitarPagina", () => {
  it("pagina dentro do total fica onde esta", () => {
    expect(limitarPagina(2, 5)).toBe(2);
    expect(limitarPagina(4, 5)).toBe(4);
  });

  it("lista que encolheu traz a pagina para a ultima que existe", () => {
    expect(limitarPagina(4, 2)).toBe(1);
  });

  it("lista vazia nao tem pagina negativa", () => {
    expect(limitarPagina(3, 0)).toBe(0);
    expect(limitarPagina(0, 0)).toBe(0);
  });
});
