import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

// Resolve os aliases usados pelos componentes, sem alterar o runner global.
vi.mock("@/lib/utils", async () => import("../lib/utils"));
vi.mock("@/lib/formato", async () => import("../lib/formato"));
vi.mock("@/lib/derivacoes", async () => import("../lib/derivacoes"));
vi.mock("@/lib/movimento", () => ({ pilha: {}, itemDaPilha: {} }));
vi.mock("./CartaoIndicador", () => ({
  CartaoIndicador: ({ rotulo, valor, explicacaoVazio, destaque }: { rotulo: string; valor: number | null; explicacaoVazio: string; destaque?: boolean }) =>
    <section aria-label={rotulo} data-destaque={String(!!destaque)}>{valor === null ? explicacaoVazio : String(valor)}</section>,
}));
vi.mock("./AparatoDaTela", () => ({ RessalvaDaTela: () => null }));
vi.mock("./Explicacao", () => ({ Explicacao: () => null }));

import { FaixaIndicadores } from "./FaixaIndicadores";

const base = {
  nps: 100, csat: 100, containment: 100, falsoContainment: 0,
  contidosComSinal: 8, total: 8, semSinal: 0, comSinal: 8,
  votosComNota: null, concordanciaComVoto: null,
};
const renderizar = (npsIntervalo: { nps: number | null; ic_inferior: number; ic_superior: number; n: number } | null, nps: number | null = 100) =>
  renderToStaticMarkup(<FaixaIndicadores
    indicadores={{ ...base, nps, npsIntervalo }} tempoMediano={1}
    limiares={{ pico: 10, saudavel: 60, degradando: 180 }} rotuloDoPeriodo="hoje"
  />);
const cartaoNps = (html: string) => html.match(/<section aria-label="NPS inferido" data-destaque="true">(.*?)<\/section>/)?.[1];

describe("NPS na faixa de indicadores", () => {
  it("respeita a abstencao do servidor no cartao principal", () => {
    const html = renderizar({ nps: null, ic_inferior: 30, ic_superior: 100, n: 8 });
    expect(cartaoNps(html)).toContain("Amostra insuficiente");
    expect(cartaoNps(html)).not.toContain("100");
    expect(cartaoNps(html)).not.toContain("Nenhum atendimento");
  });
  it("usa o ponto autorizado no intervalo quando ele existe", () => {
    expect(cartaoNps(renderizar({ nps: 25, ic_inferior: 0, ic_superior: 50, n: 40 }))).toBe("25");
  });
  it("mantem compatibilidade com resposta sem intervalo", () => {
    expect(cartaoNps(renderizar(null))).toBe("100");
  });
  it("cortesia sem score nao e descrita como ausencia de fala", () => {
    expect(cartaoNps(renderizar(null, null))).toContain("sinal de satisfação");
    expect(cartaoNps(renderizar(null, null))).not.toContain("tem fala do cliente");
  });
});

describe("voto do cliente abaixo dos indicadores", () => {
  const comVotos = (votosComNota: number | null, concordanciaComVoto: number | null) =>
    renderToStaticMarkup(<FaixaIndicadores
      indicadores={{ ...base, npsIntervalo: null, votosComNota, concordanciaComVoto }} tempoMediano={1}
      limiares={{ pico: 10, saudavel: 60, degradando: 180 }} rotuloDoPeriodo="hoje"
    />);
  it("sem voto no periodo nomeia a ausencia, nunca 0%", () => {
    const html = comVotos(0, null);
    expect(html).toContain("Nenhum voto do cliente em atendimentos com nota neste período.");
    expect(html).not.toContain("0%");
  });
  it("com votos mostra a concordancia do servidor e o denominador", () => {
    const html = comVotos(6, 0.5);
    expect(html).toContain("50%");
    expect(html).toMatch(/dos <span class="num">6<\/span> atendimentos com voto e nota/);
  });
  it("sem a contagem do servidor (plano B ou API antiga) nao afirma nada", () => {
    expect(comVotos(null, null)).not.toContain("Voto do cliente");
  });
});

