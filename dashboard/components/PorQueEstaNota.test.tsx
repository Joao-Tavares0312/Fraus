import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { PorQueEstaNota } from "./PorQueEstaNota";
import type { Explicacao } from "@/lib/api";

const explicacao: Explicacao = {
  frases: [
    "Pesou contra: o ritmo do atendimento, −23,4 pontos.",
    "Pesou a favor: o texto do cliente, +31,0 pontos.",
  ],
  contra: [{ familia: "tempo", rotulo: "o ritmo do atendimento", pontos: -23.4, detalhe: null }],
  a_favor: [{ familia: "texto", rotulo: "o texto do cliente", pontos: 31, detalhe: null }],
  aviso: "Efeito de cada sinal medido no próprio modelo... associação no modelo, não causa.",
  efeitos: { texto: 31, emoji: 0, tempo: -23.4, emocao: 0.3, lexico: 0, estilo: 0, incongruencia: 0 },
  decomposicao: { referencia: 0, score: 41.2, eixos: [] },
  familia_da_feature: {},
};

const html = (e: Explicacao | null) =>
  renderToStaticMarkup(<PorQueEstaNota conversaId="c1" explicacao={e} comSinal />);

describe("PorQueEstaNota", () => {
  it("mostra as frases do servidor e o aviso de associação", () => {
    const markup = html(explicacao);
    expect(markup).toContain("Pesou contra");
    expect(markup).toContain("Pesou a favor");
    expect(markup).toContain("não causa");
  });

  it("sem explicação, nomeia o endpoint e o campo, sem alegar falta de sinal", () => {
    const markup = html(null);
    expect(markup).toMatch(/Explicação indisponível nesta versão da API/);
    expect(markup).toContain("GET /conversas/{id}/atribuicao");
    expect(markup).toContain("explicacao");
    expect(markup).not.toMatch(/Sem sinal do cliente/i);
    expect(markup).not.toMatch(/0 pontos/);
  });

  it("só desenha famílias com efeito de pelo menos 1 ponto", () => {
    const markup = html(explicacao);
    expect(markup).toContain("Texto");
    expect(markup).toContain("Tempo");
    expect(markup).not.toContain("Emoji");
    expect(markup).not.toContain("Emoção");
    expect(markup).not.toMatch(/(^|[^\d,])0,0\b/);
  });

  it("tem o formulário do contrafactual de primeira resposta", () => {
    const markup = html(explicacao);
    expect(markup).toContain('max="86400"');
    expect(markup).toContain("Calcular");
  });

  it("aceita explicação sem o campo (API antiga) como vazio", () => {
    const markup = renderToStaticMarkup(
      <PorQueEstaNota conversaId="c1" explicacao={undefined as unknown as null} comSinal />,
    );
    expect(markup).toMatch(/Explicação indisponível nesta versão da API/);
    expect(markup).not.toMatch(/Sem sinal do cliente/i);
  });

  it("sem sinal do cliente não renderiza nada: o vazio é o do painel de contribuições", () => {
    const markup = renderToStaticMarkup(
      <PorQueEstaNota conversaId="c1" explicacao={null} comSinal={false} />,
    );
    expect(markup).toBe("");
  });
});
