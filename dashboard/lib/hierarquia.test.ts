// dashboard/lib/hierarquia.test.ts
import { describe, expect, it } from "vitest";
import { DOMINANTE_POR_TELA, dominanteDaTela } from "./hierarquia";


describe("dominanteDaTela", () => {
  it("nomeia um dominante para cada tela da ferramenta", () => {
    const rotas = [
      "/dashboard",
      "/dashboard/atendimentos",
      "/dashboard/modelo",
      "/dashboard/grafo",
      "/dashboard/integracoes",
      "/dashboard/configuracoes",
    ];
    for (const rota of rotas) {
      const id = dominanteDaTela(rota);
      expect(id, rota).toBeTruthy();
      // Identificador estavel: sem espaco e sem maiuscula. E o que impede
      // alguem de reintroduzir titulo de exibicao aqui sem perceber.
      expect(id, rota).toMatch(/^[a-z0-9-]+$/);
    }
  });

  it("da UM dominante por tela, nunca dois", () => {
    // A tese da hierarquia: um sistema por tela responde a pergunta que
    // levou o analista ali. Dois dominantes e nenhum.
    const valores = Object.values(DOMINANTE_POR_TELA);
    expect(new Set(valores).size).toBe(valores.length);
  });

  it("devolve null para rota que nao e tela da ferramenta", () => {
    expect(dominanteDaTela("/")).toBeNull();
  });
});

