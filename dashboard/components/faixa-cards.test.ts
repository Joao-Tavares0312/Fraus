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

describe("rotulo do indicador e cabecalho de tabela sem canto cortado solto", () => {
  it("o rotulo estimativa/observado e texto puro: ghost, sem outline com traco", () => {
    const fonte = readFileSync("components/CartaoIndicador.tsx", "utf8");
    expect(fonte).toMatch(/<Badge variant="ghost"/);
    expect(fonte).not.toMatch(/<Badge variant="outline"[^>]*border-0/);
    expect(fonte).toMatch(/justify-between gap-2 pr-3/);
  });

  it("o thead nao leva .superficie (cortaria o grupo de linhas)", () => {
    const fonte = readFileSync("components/ui/table.tsx", "utf8");
    const thead = fonte.match(/<thead[\s\S]*?\/>/)![0];
    expect(thead).not.toMatch(/superficie/);
    expect(thead).toMatch(/bg-card/);
  });
});
