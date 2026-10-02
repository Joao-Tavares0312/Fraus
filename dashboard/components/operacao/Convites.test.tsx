import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Equipe } from "../../lib/operacao";

vi.mock("@/lib/formato", async () => import("../../lib/formato"));
vi.mock("@/lib/utils", async () => import("../../lib/utils"));
vi.mock("@/components/ui/button", async () => import("../ui/button"));
vi.mock("@/components/ui/input", async () => import("../ui/input"));
vi.mock("@/components/IconeDeAcao", async () => import("../IconeDeAcao"));
const recurso = vi.hoisted(() => vi.fn());
vi.mock("./comum", () => ({
  CAMPO: "", GRADE: "", LINHA: "", PILHA: "", lista: () => [],
  useRecurso: recurso,
  useAcao: () => ({ ocupado: false, executar: vi.fn(), feedback: null }),
  Carregamento: ({ erro }: { erro: string | null }) => <p role="status">{erro ?? "Carregando"}</p>,
  Campo: ({ nome, children }: { nome: string; children: ReactNode }) => <label>{nome}{children}</label>,
  Numero: ({ nome }: { nome: string }) => <input aria-label={nome} />,
  Medida: () => null,
}));
import { ConvitesEquipe } from "./Convites";

const equipe: Equipe = {
  id: "suporte", nome: "Suporte", membros: [1], competencias: [], canais: ["chat"], papeis: { "1": "proprietario" },
  meu_papel: "proprietario", integrantes: [{ id: 1, nome: "Ana", papel: "proprietario" }],
};
const renderizar = (alteracoes: Partial<Equipe> = {}) => renderToStaticMarkup(<ConvitesEquipe equipe={{ ...equipe, ...alteracoes }} recarregar={vi.fn()} />);

beforeEach(() => {
  recurso.mockReset().mockReturnValue({ dado: { convites: [] }, erro: null, recarregar: vi.fn() });
});

describe("hierarquia e convites com respostas incompletas", () => {
  it("renderiza uma equipe antiga sem integrantes ou papel sem liberar gestao", () => {
    const html = renderizar({ integrantes: undefined, meu_papel: undefined });
    expect(html).toContain("dados da hierarquia");
    expect(html).not.toContain("Gerar link de convite");
    expect(html).not.toContain("Atualizar equipe");
    expect(recurso).toHaveBeenCalledWith(null);
  });
  it("nao quebra se integrantes vier como null", () => {
    expect(renderizar({ integrantes: null as unknown as Equipe["integrantes"] })).toContain("dados da hierarquia");
    expect(recurso).toHaveBeenCalledWith(null);
  });
  it("nao concede gestao quando o papel estiver ausente", () => {
    expect(renderizar({ meu_papel: undefined })).not.toContain("Gerar link de convite");
    expect(recurso).toHaveBeenCalledWith(null);
  });
  it("exibe integrantes e controles quando a hierarquia estiver completa", () => {
    const html = renderizar();
    expect(html).toContain("Ana");
    expect(html).toContain("Papel de Ana");
    expect(html).toContain("Atualizar equipe");
    expect(html).toContain("Gerar link de convite");
    expect(html).not.toContain("dados da hierarquia");
    expect(recurso).toHaveBeenCalledWith("/equipes/suporte/convites");
  });
  it("mantem membro em leitura sem consultar convites", () => {
    const html = renderizar({ meu_papel: "membro" });
    expect(html).toContain("Ana");
    expect(html).not.toContain("Gerar link de convite");
    expect(html).not.toContain("Papel de Ana");
    expect(recurso).toHaveBeenCalledWith(null);
  });
});
