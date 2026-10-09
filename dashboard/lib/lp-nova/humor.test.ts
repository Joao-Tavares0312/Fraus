import { describe, expect, it } from "vitest";
import { humorDaCategoria } from "./humor";

describe("humorDaCategoria", () => {
  it("detrator agita o campo, promotor assenta", () => {
    expect(humorDaCategoria("detrator")).toEqual({ humor: -1, cinza: 0 });
    expect(humorDaCategoria("promotor")).toEqual({ humor: 1, cinza: 0 });
  });
  it("neutro fica perto do meio, inclinado ao dito", () => {
    expect(humorDaCategoria("neutro")).toEqual({ humor: -0.2, cinza: 0 });
  });
  it("sem categoria e sem sinal: campo cinza e parado, nunca o humor de um detrator", () => {
    expect(humorDaCategoria(null)).toEqual({ humor: 0, cinza: 1 });
  });
  it("categoria desconhecida tambem cai no cinza em vez de inventar inclinacao", () => {
    expect(humorDaCategoria("outra")).toEqual({ humor: 0, cinza: 1 });
  });
});
