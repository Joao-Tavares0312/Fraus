import { describe, expect, it } from "vitest";

import { idDaRota } from "./rota";

describe("id do atendimento lido da rota", () => {
  it("desfaz o percent-encoding que o Next deixa no parametro", () => {
    // O link e montado com encodeURIComponent e o Next entrega `analise%3A...`.
    // Codificar de novo para a API dava `%253A` e 404 -- em producao, 02/10/2026.
    expect(idDaRota("analise%3A1ce1c37d")).toBe("analise:1ce1c37d");
    expect(idDaRota("arquivo%3Amaio%3Aabc")).toBe("arquivo:maio:abc");
    expect(idDaRota("conversa%20com%20espaco")).toBe("conversa com espaco");
  });

  it("id sem nada codificado passa igual", () => {
    expect(idDaRota("sim-1-636628032")).toBe("sim-1-636628032");
  });

  it("percent solto nao derruba a pagina", () => {
    expect(idDaRota("100%")).toBe("100%");
  });

  it("ida e volta pelo link preserva o id", () => {
    for (const id of ["analise:abc", "a/b", "c-1404", "ção 😀"]) {
      expect(idDaRota(encodeURIComponent(id))).toBe(id);
    }
  });
});
