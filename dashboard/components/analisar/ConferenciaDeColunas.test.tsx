import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { PreviaLeitura } from "../../lib/api";

vi.mock("@/lib/api", async () => import("../../lib/api"));
vi.mock("@/lib/utils", async () => import("../../lib/utils"));
vi.mock("@/components/ui/alert", async () => import("../ui/alert"));
vi.mock("@/components/ui/button", async () => import("../ui/button"));
vi.mock("@/components/ui/input", async () => import("../ui/input"));
vi.mock("@/components/ui/label", async () => import("../ui/label"));
vi.mock("@/components/ui/select", async () => import("../ui/select"));
vi.mock("@/components/Painel", async () => import("../Painel"));
vi.mock("@/components/IconeDeAcao", async () => import("../IconeDeAcao"));
import { ConferenciaDeColunas } from "./ConferenciaDeColunas";

const previa: PreviaLeitura = {
  formato: "planilha com colunas inferidas",
  tem_tempo: true,
  conversas: 1,
  mensagens: 4,
  avisos: [],
  total_rejeitadas: 0,
  rejeitadas: [],
  mapeamento: {
    colunas: ["quem", "mensagem", "quando"],
    assinatura: "x",
    papeis: {
      texto: { coluna: "mensagem", confianca: 0.52, motivo: "pelo conteúdo" },
      autor: { coluna: "quem", confianca: 0.48, motivo: "pelo conteúdo" },
      enviada_em: { coluna: "quando", confianca: 0.9, motivo: "pelo nome e pelo conteúdo" },
    },
    ordem_data: null,
    data_ambigua: false,
  },
  amostra: [["cliente", "a", "1"], ["bot", "b", "2"], ["cliente", "c", "3"], ["bot", "d", "4"]],
  perfil: null,
  confiavel: false,
};

const renderizar = () => renderToStaticMarkup(
  <ConferenciaDeColunas previa={previa} ocupado={false}
    aoAjustar={vi.fn()} aoConfirmar={vi.fn()} aoCancelar={vi.fn()} />,
);

describe("conferência de colunas enxuta", () => {
  it("não oferece salvar perfil na análise", () => {
    expect(renderizar()).not.toContain("Lembrar este mapeamento");
  });

  it("não mostra a força da evidência ao cliente final", () => {
    const html = renderizar();
    expect(html).not.toContain("evidência");
    expect(html).not.toContain("0,52");
  });

  it("deixa data, conversa e canal recolhidos em Mais colunas", () => {
    expect(renderizar()).toContain("Mais colunas");
  });

  it("mostra só três linhas de amostra", () => {
    const html = renderizar();
    expect(html).toContain(">c<");
    expect(html).not.toContain(">d<");
  });
});
