import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// `.faixa-indicadores` e so a grade com espaco; quem a usa entrega cards.
describe("consumidores da faixa de indicadores usam a mesma linguagem de card", () => {
  it("as celulas do resumo do atendimento sao superficie, sem fio", () => {
    const fonte = readFileSync("components/atendimentos/ResumoDoAtendimento.tsx", "utf8");
    expect(fonte).toMatch(/className="superficie quebra-evitar[^"]*"/);
    expect(fonte).not.toMatch(/superficie[^"]*\bfio\b/);
  });

  it("o esqueleto da visao geral tem celulas com o mesmo formato de card", () => {
    const fonte = readFileSync("app/dashboard/loading.tsx", "utf8");
    expect(fonte).toMatch(/className="superficie [^"]*"/);
    expect(fonte).not.toContain("separadas por régua");
  });
});
