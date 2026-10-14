import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ImpactoTema } from "./ImpactoTema";
import type { ImpactoTema as Impacto } from "@/lib/operacao";

const medido: Impacto = { impacto_nps: -23.5, ic_inferior: -40.1, ic_superior: -6.2, n_tema: 48, n_resto: 310, sem_sinal_tema: 3, minimo: 30, motivo: null, rotulo: "associação, não causa" };
const html = (i: Impacto | undefined) => renderToStaticMarkup(<ImpactoTema impacto={i} />);

describe("ImpactoTema", () => {
  it("mostra a diferença com sinal, o IC e o rótulo", () => {
    const m = html(medido);
    expect(m).toContain("−23,5");
    expect(m).toContain("−40,1");
    expect(m).toContain("associação, não causa");
    expect(m).toContain("3 sem sinal");
    expect(m).toContain("Impacto no NPS inferido");
    expect(m).toContain("IC só amostral, não cobre o erro do modelo");
  });
  it("abaixo do mínimo nomeia o que falta e não mostra zero", () => {
    const m = html({ ...medido, impacto_nps: null, ic_inferior: null, ic_superior: null, n_tema: 12, motivo: "n abaixo do mínimo" });
    expect(m).toContain("n abaixo do mínimo");
    expect(m).toContain("12");
    expect(m).toContain("Impacto no NPS inferido indisponível (n abaixo do mínimo): 12 conversas");
    expect(m).not.toContain("::");
    expect(m).not.toContain(": n abaixo do mínimo:");
    expect(m).not.toMatch(/[+−]0(,0)?\b/);
  });
  it("API antiga: indisponível", () => {
    expect(html(undefined)).toContain("indisponível nesta versão da API");
  });
  it("só o resto abaixo do mínimo: nomeia os dois lados", () => {
    const m = html({ ...medido, impacto_nps: null, ic_inferior: null, ic_superior: null, n_tema: 48, n_resto: 17, motivo: "n abaixo do mínimo" });
    expect(m).toContain("48 conversas com sinal no tema");
    expect(m).toContain("17 no resto do recorte");
    expect(m).toContain("mínimo 30 em cada lado");
  });
  it("impacto presente com IC nulo mostra o número sem o IC", () => {
    const m = html({ ...medido, ic_inferior: null, ic_superior: null });
    expect(m).toContain("−23,5");
    expect(m).not.toContain("indisponível");
    expect(m).not.toContain("IC 95%");
  });
  it("sem_sinal_tema 0 não aparece", () => {
    expect(html({ ...medido, sem_sinal_tema: 0 })).not.toContain("sem sinal");
  });
  it("valor que arredonda para zero não leva sinal", () => {
    const m = html({ ...medido, impacto_nps: -0.04, ic_inferior: -3, ic_superior: 3 });
    expect(m).toContain("0,0 pontos");
    expect(m).not.toContain("−0,0");
  });
});
