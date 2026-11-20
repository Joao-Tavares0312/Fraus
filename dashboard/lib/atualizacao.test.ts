import { describe, expect, it } from "vitest";
import { INTERVALO_MINIMO_FOCO_MS, deveAtualizarNoFoco } from "./atualizacao";

describe("deveAtualizarNoFoco", () => {
  it("nao relê antes de 60 s desde a ultima leitura", () => {
    expect(deveAtualizarNoFoco(1_000 + INTERVALO_MINIMO_FOCO_MS - 1, 1_000)).toBe(false);
  });

  it("relê a partir de 60 s", () => {
    expect(deveAtualizarNoFoco(1_000 + INTERVALO_MINIMO_FOCO_MS, 1_000)).toBe(true);
  });
});

import { mudouAAssinatura } from "./atualizacao";

describe("mudouAAssinatura", () => {
  it("a primeira leitura so registra a base", () => {
    expect(mudouAAssinatura(null, "5:100")).toBe(false);
  });

  it("assinatura diferente da base pede releitura", () => {
    expect(mudouAAssinatura("5:100", "5:140")).toBe(true);
    expect(mudouAAssinatura("5:100", "6:180")).toBe(true);
  });

  it("assinatura igual nao rele nada", () => {
    expect(mudouAAssinatura("5:100", "5:100")).toBe(false);
  });

  it("sonda que falhou nao e mudanca", () => {
    // API fora do ar nao pode virar uma releitura a cada 15 s.
    expect(mudouAAssinatura("5:100", null)).toBe(false);
  });
});
