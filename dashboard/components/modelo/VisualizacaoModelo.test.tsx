import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { FichaModelo, Simulacao } from "@/lib/api";
import { sinaisRetornados, VisualizacaoModelo } from "./VisualizacaoModelo";

vi.mock("@/lib/api", () => ({ simularTexto: vi.fn() }));
import { simularTexto } from "@/lib/api";

const modelo: FichaModelo = {
  importancias: { texto_prob_insatisfeito_media: 0, emocao_raiva_media: 1 },
  cabecas: [
    { nome: "satisfacao", classes: ["insatisfeito", "neutro", "satisfeito"], pontua: true, metricas: null },
    { nome: "emocao", classes: [], pontua: true, metricas: null },
    { nome: "ironia", classes: ["nao-ironico", "ironico"], pontua: false, metricas: null },
  ],
  classes: ["insatisfeito", "neutro", "satisfeito"],
  metricas: null,
  faixas_nps: {},
  total_emojis_lexicon: 0,
};
const resposta: Simulacao = {
  texto: "Frase sintética do teste",
  prob_insatisfeito: 0,
  prob_neutro: 1,
  prob_satisfeito: 0,
  emojis: [],
  emocao: null,
  prob_ironia: null,
  estilo: null,
};

function botaoDaFamilia(html: string, nome: string) {
  return html.match(/<button\b[^>]*>[\s\S]*?<\/button>/g)?.find((botao) => botao.includes(`>${nome}</span>`));
}

describe("presença de sinais na resposta de frase", () => {
  it("ausência de resposta não destaca família alguma", () => {
    expect(sinaisRetornados(null)).toEqual([]);
  });

  it("zero medido e lista vazia são respostas, não ausência", () => {
    expect(sinaisRetornados(resposta)).toEqual(["texto", "emoji"]);
  });

  it("só destaca as famílias efetivamente retornadas, nunca tempo, léxico ou incongruência", () => {
    expect(sinaisRetornados({
      ...resposta,
      emocao: { raiva: 0, alegria: 1 },
      prob_ironia: 0,
      estilo: { caixa_alta: false, alongamento: false, pontuacao_enfatica: 0, palavrao: null, palavrao_dirigido: false, censura: false },
    })).toEqual(["texto", "emoji", "emocao", "ironia", "estilo"]);
  });

  it("objeto vazio ou probabilidades não finitas não viram saída disponível", () => {
    expect(sinaisRetornados({ ...resposta, emocao: {}, prob_ironia: Number.NaN, prob_neutro: Number.NaN })).toEqual(["emoji"]);
  });
});

describe("explorador do modelo", () => {
  it("separa contrato estático da contagem observada, incluindo peso zero", () => {
    const html = renderToStaticMarkup(<VisualizacaoModelo modelo={modelo} />);
    expect(html).toContain("7 famílias · 39 features");
    expect(html).toContain("Ficha consultada: 2 features em 2 famílias.");
    expect(html).toContain("Texto: 1");
    expect(simularTexto).not.toHaveBeenCalled();
  });

  it("mapa de pesos vazio nomeia ausência, não afirma que o modelo tem zero features", () => {
    const html = renderToStaticMarkup(<VisualizacaoModelo modelo={{ ...modelo, importancias: {} }} />);
    expect(html).toContain("contagem observada não disponível");
    expect(html).not.toContain("Ficha consultada: 0");
    expect(html).toContain("7 famílias · 39 features");
  });

  it.each([true, false])("o ramo neural segue pontua da API: ironia=%s", (pontua) => {
    const ficha = { ...modelo, cabecas: modelo.cabecas.map((cabeca) => cabeca.nome === "ironia" ? { ...cabeca, pontua } : cabeca) };
    const html = renderToStaticMarkup(<VisualizacaoModelo modelo={ficha} />);
    const botao = botaoDaFamilia(html, "Ironia");
    expect(botao).toBeDefined();
    expect(botao).toContain(pontua ? "Entra no vetor" : "Ramo por mensagem · fora do vetor");
    expect(botao).not.toContain(pontua ? "fora do vetor" : "Entra no vetor");
  });

  it("cabeça ausente não vira caminho confirmado nem probabilidade zero", () => {
    const html = renderToStaticMarkup(<VisualizacaoModelo modelo={{ ...modelo, cabecas: [] }} />);
    expect(botaoDaFamilia(html, "Texto")).toContain("Caminho não confirmado");
    expect(botaoDaFamilia(html, "Ironia")).toContain("Caminho não confirmado");
    expect(html).not.toContain("0%");
  });

  it("a advertência e os limites da simulação ficam no conteúdo visível", () => {
    const html = renderToStaticMarkup(<VisualizacaoModelo modelo={modelo} />);
    expect(html).toContain("Esquema didático do processamento. Não mostra ativações internas, atenção ou influência causal das palavras.");
    expect(html).toContain("não calculado nesta simulação de frase");
    expect(html).toContain('aria-label="Fluxo de processamento do Fraus"');
    expect(botaoDaFamilia(html, "Tempo")).toContain("somente no processamento de conversa");
    expect(simularTexto).not.toHaveBeenCalled();
  });
});
