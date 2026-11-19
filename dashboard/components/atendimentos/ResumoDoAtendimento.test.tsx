import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { DetalheConversa } from "@/lib/api";

vi.mock("@/lib/utils", async () => import("../../lib/utils"));
vi.mock("@/lib/formato", async () => import("../../lib/formato"));
vi.mock("@/components/CabecaVazada", () => ({ CabecaVazada: () => null }));
vi.mock("@/components/Explicacao", () => ({ Explicacao: () => null }));
vi.mock("@/components/EtiquetaCategoria", () => ({ EtiquetaCategoria: () => null }));
vi.mock("@/components/MarcaContestacao", () => ({ MarcaContestacao: () => null }));
vi.mock("@/components/NotaInferida", () => ({ NotaInferida: () => null }));
import { ResumoDoAtendimento } from "./ResumoDoAtendimento";

const conversa = (extra: Partial<DetalheConversa>) =>
  ({
    id: "c1",
    canal: "telegram",
    iniciada_em: "2026-11-20T12:00:00-03:00",
    escalou_para_humano: false,
    nota: 3,
    categoria: "detrator",
    mensagens: [],
    ...extra,
  }) as unknown as DetalheConversa;

const renderizar = (extra: Partial<DetalheConversa>) =>
  renderToStaticMarkup(<ResumoDoAtendimento conversa={conversa(extra)} mediana={null} respostas={0} duracao={null} />);

describe("voto do cliente no resumo do atendimento", () => {
  it("resolveu", () => {
    expect(renderizar({ feedback_declarado: 1 })).toContain("cliente votou: resolveu");
  });
  it("não resolveu, com o comentário citado", () => {
    const html = renderizar({ feedback_declarado: -1, comentario_feedback: " faltou o boleto " });
    expect(html).toContain("cliente votou: não resolveu");
    expect(html).toContain("Comentário do cliente");
    expect(html).toContain("faltou o boleto");
  });
  it("sem voto diz que não há voto, sem inventar um", () => {
    for (const extra of [{}, { feedback_declarado: null }] as Partial<DetalheConversa>[]) {
      const html = renderizar(extra);
      expect(html).toContain("sem voto do cliente");
      expect(html).not.toContain("cliente votou");
      expect(html).not.toContain("Comentário do cliente");
    }
  });
});
