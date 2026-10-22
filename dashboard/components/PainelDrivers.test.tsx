import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { TabelaDrivers } from "./PainelDrivers";
import type { Drivers } from "@/lib/api";

const base: Drivers = {
  recorte: { de: null, ate: null, canal: null },
  n_pedido: 50,
  amostra: 2,
  elegiveis: 2,
  sem_sinal: 3,
  defasadas: 1,
  semente: 20261014,
  eixo: "log(P(satisfeito)/P(insatisfeito))",
  rotulo: "associação no modelo, não causa",
  metodo: "…",
  familias: [
    {
      familia: "tempo",
      detratores: { n: 0, media: null, ic: null },
      promotores: { n: 2, media: 0.8, ic: [0.5, 1.1] },
    },
  ],
};

const html = (d: Drivers) => renderToStaticMarkup(<TabelaDrivers drivers={d} />);

describe("TabelaDrivers", () => {
  it("grupo vazio aparece como sem dado, não como 0", () => {
    const markup = html(base);
    expect(markup).toMatch(/sem detratores na amostra/i);
    expect(markup).toContain("Tempo");
  });


  it("declara amostra, sem sinal, defasadas e o rótulo de associação", () => {
    const markup = html(base);
    expect(markup).toContain("não causa");
    expect(markup).toMatch(/3 sem sinal/);
    expect(markup).toMatch(/1 .*repontuar/);
  });

  it("diz o período medido: todo o histórico e um recorte datado", () => {
    expect(html(base)).toContain("período medido: todo o histórico");
    const datado = html({
      ...base,
      recorte: { de: "2026-10-01", ate: "2026-10-07", canal: null },
    });
    expect(datado).toContain("período medido: de 2026-10-01 até 2026-10-07");
  });

  it("n = 1 sem intervalo é dito, e promotor vazio também", () => {
    const markup = html({
      ...base,
      familias: [
        {
          familia: "texto",
          detratores: { n: 1, media: -0.4, ic: null },
          promotores: { n: 0, media: null, ic: null },
        },
      ],
    });
    expect(markup).toMatch(/n = 1, sem intervalo/);
    expect(markup).toMatch(/sem promotores na amostra/i);
  });
});

