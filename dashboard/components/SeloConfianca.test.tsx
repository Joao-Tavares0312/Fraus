import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SeloConfianca } from "./SeloConfianca";
import type { Confianca, Resultado } from "@/lib/api";

const base: Confianca = {
  conversa_id: "c1",
  score: 62,
  conjunto: [1],
  rotulos_conjunto: ["neutro"],
  abstencao: false,
  criterios: [],
  features_fora_da_faixa: [],
  alvo: 0.9,
  garantia: "cobertura ≥ alvo por classe, sob permutabilidade; não vale sob mudança de distribuição.",
  metodo: "conformal por classe",
};

const ok = (c: Confianca): Resultado<Confianca> => ({ ok: true, dado: c });
const html = (r: Resultado<Confianca>) =>
  renderToStaticMarkup(<SeloConfianca resultado={r} />);

describe("SeloConfianca", () => {
  it("sem abstenção: uma linha discreta com alvo e rótulo, e a garantia", () => {
    const m = html(ok(base));
    expect(m).toContain("Classe de satisfação compatível com esta nota (calibração de 90%):");
    expect(m).toContain("neutro");
    expect(m).toContain("não a categoria NPS");
    expect(m).toContain(base.garantia);
    expect(m).not.toContain("sem confiança suficiente");
  });

  it("abstenção por conjunto múltiplo, vazio e deriva, em linguagem simples", () => {
    const m = html(
      ok({
        ...base,
        conjunto: [0, 1],
        rotulos_conjunto: ["insatisfeito", "neutro"],
        abstencao: true,
        criterios: ["conjunto_multiplo", "conjunto_vazio", "deriva"],
        features_fora_da_faixa: ["texto_p_media", "tempo_log"],
      }),
    );
    expect(m).toContain("Leitura sem confiança suficiente");
    expect(m).toContain("a nota é compatível com mais de uma classe de satisfação");
    expect(m).toContain("a nota não se parece com nenhuma classe de satisfação calibrada");
    expect(m).toContain("fora da faixa de treino em: texto_p_media, tempo_log");
    expect(m).toContain("Continua contando no NPS.");
    expect(m).not.toContain("calibração de 90%");
    expect(m).not.toContain("não a categoria NPS");
  });

  it("deriva não avaliada em conversa longa aparece como nota, sem afirmar nada", () => {
    const m = html(ok({ ...base, features_fora_da_faixa: null, deriva_nao_avaliada: true }));
    expect(m).toContain("deriva não avaliada nesta leitura (conversa longa)");
    expect(html(ok(base))).not.toContain("deriva não avaliada");
  });

  it("score nulo não renderiza nada", () => {
    const m = html(
      ok({ ...base, score: null, conjunto: null, rotulos_conjunto: null, abstencao: null }),
    );
    expect(m).toBe("");
  });

  it("503 nomeia o que falta, traz o detalhe do servidor e nunca diz confiante", () => {
    const m = html({ ok: false, erro: "artefato ausente: rode o gerador", status: 503 });
    expect(m).toContain("Calibração conformal ainda não gerada para este modelo");
    expect(m).toContain("artefato ausente: rode o gerador");
    expect(m).not.toMatch(/confiante/i);
  });

  it("409 pede repontuar", () => {
    const m = html({ ok: false, erro: "outra régua", status: 409 });
    expect(m).toContain("pontuada com outra régua; repontue para ver a confiança");
    expect(m).not.toMatch(/confiante/i);
  });

  it("outra falha não afirma nada sobre confiança", () => {
    const m = html({ ok: false, erro: "API não respondeu", status: 500 });
    expect(m).toContain("Confiança indisponível");
    expect(m).not.toMatch(/confiante/i);
  });
});
