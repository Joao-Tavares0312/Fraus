import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SidebarProvider } from "@/components/ui/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { NavegacaoLateral } from "./NavegacaoLateral";

const ambiente = vi.hoisted(() => ({
  caminho: "/dashboard",
  consulta: "de=2026-08-01&ate=2026-08-22&busca=nao-carregar&pagina=3",
}));
vi.mock("next/navigation", () => ({
  usePathname: () => ambiente.caminho,
  useSearchParams: () => new URLSearchParams(ambiente.consulta),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

beforeEach(() => {
  ambiente.caminho = "/dashboard";
  vi.stubEnv("NEXT_PUBLIC_URL_DOCS", "https://docs.example.test/fraus");
});

function renderizar(papel: "dev" | "usuario" = "dev", aberta = true) {
  return renderToStaticMarkup(
    <TooltipProvider>
      <SidebarProvider defaultOpen={aberta}>
        <NavegacaoLateral papel={papel} usuario={{ nome: "Analista", email: "analista@example.test" }} />
      </SidebarProvider>
    </TooltipProvider>,
  );
}

function linksDoMenu(html: string) {
  return [...html.matchAll(/<a\b[^>]*>/g)].map((resultado) => resultado[0])
    .filter((tag) => tag.includes('data-sidebar="menu-button"'));
}

describe("destinos efetivamente renderizados na sidebar", () => {
  it("usuario só recebe as cinco tarefas permitidas, todas com o período", () => {
    const html = renderizar("usuario");
    const internos = linksDoMenu(html).filter((tag) => tag.includes('href="/dashboard'));
    expect(internos).toHaveLength(5);
    for (const destino of ["/dashboard", "/dashboard/atendimentos", "/dashboard/analisar", "/dashboard/grafo", "/dashboard/operacao"]) {
      expect(internos.some((tag) => tag.includes(`href="${destino}?de=2026-08-01&amp;ate=2026-08-22"`)), destino).toBe(true);
    }
    expect(html).not.toContain('aria-label="Configurar"');
    expect(html).not.toContain('href="/dashboard/modelo');
    expect(html).not.toContain('href="/dashboard/integracoes');
    expect(html).not.toContain('href="/dashboard/configuracoes');
    expect(html).not.toContain("nao-carregar");
  });

  it("dev recebe as oito rotas, com nomes explícitos mesmo recolhidas", () => {
    const html = renderizar("dev", false);
    expect(html).toContain('data-state="collapsed"');
    const links = linksDoMenu(html);
    expect(links).toHaveLength(9);
    for (const nome of ["Visão geral", "Atendimentos", "Analisar", "Grafo", "Operação", "Integrações", "Modelo", "Configurações", "Documentação (abre em nova aba)"]) {
      expect(links.some((tag) => tag.includes(`aria-label="${nome}"`)), nome).toBe(true);
    }
    expect(html).toContain('aria-label="Expandir navegação"');
  });

  it("marca a folha e o ancestral sem marcar a visão geral em todo caminho", () => {
    ambiente.caminho = "/dashboard/atendimentos";
    expect(linksDoMenu(renderizar()).filter((tag) => tag.includes('aria-current="page"')))
      .toEqual([expect.stringContaining('aria-label="Atendimentos"')]);
    ambiente.caminho = "/dashboard/atendimentos/caso-42";
    expect(linksDoMenu(renderizar()).filter((tag) => tag.includes("aria-current=")))
      .toEqual([expect.stringContaining('aria-current="location"')]);
    expect(linksDoMenu(renderizar()).find((tag) => tag.includes('aria-current="location"')))
      .toContain('aria-label="Atendimentos"');
  });

  it("documentação e sessão permanecem acessíveis, sem marca interativa dentro do link", () => {
    const html = renderizar();
    const docs = linksDoMenu(html).find((tag) => tag.includes('href="https://docs.example.test/fraus"'));
    expect(docs).toContain('target="_blank"');
    expect(docs).toContain('rel="noopener noreferrer"');
    expect(html).toContain('aria-label="Sair da conta de Analista"');
    expect(html).toContain('aria-label="Tema: Escuro. Trocar para Claro."');
    expect(html).toContain('aria-label="Fraus — revelar o segredo com cinco cliques"');
    for (const [link] of html.matchAll(/<a\b[^>]*>[\s\S]*?<\/a>/g)) {
      expect(link).not.toContain("<button");
    }
    for (const [botao] of html.matchAll(/<button\b[^>]*>[\s\S]*?<\/button>/g)) {
      expect(botao).not.toContain("<a ");
    }
  });
});
