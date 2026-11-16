import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FichaModelo, MetricasTreino } from "@/lib/api";
import { EstadoDoModelo } from "./EstadoDoModelo";

function renderizar(metricas: MetricasTreino | null) {
  const modelo: FichaModelo = {
    importancias: {},
    cabecas: [{ nome: "ironia", classes: ["nao_ironico", "ironico"], pontua: false, metricas }],
    classes: ["insatisfeito", "neutro", "satisfeito"],
    metricas: null,
    faixas_nps: {},
    total_emojis_lexicon: 0,
  };
  return renderToStaticMarkup(<EstadoDoModelo modelo={modelo} />);
}

describe("F1 da classe irônica na ficha atual", () => {
  it.each([
    [0.571, "57,1"],
    [0, "0"],
  ])("exibe a classe irônica (%s), não o macro nem a outra classe", (valor, esperado) => {
    const html = renderizar({
      f1_macro: 0.66,
      f1_por_classe: { nao_ironico: 0.75, ironico: valor },
    });
    expect(html).toContain(`aria-label="F1 da classe irônica, em porcento: ${esperado}"`);
  });

  it.each([null, {}, { f1_macro: 0.66 }, { f1_por_classe: { nao_ironico: 0.75 } }])(
    "não inventa uma medida quando falta a classe irônica: %j",
    (metricas) => {
      expect(renderizar(metricas)).not.toContain('aria-label="F1 da classe irônica, em porcento:');
    },
  );
});
