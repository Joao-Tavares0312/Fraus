import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PaginaEntrar from "@/app/entrar/page";
import PaginaCadastrar from "@/app/cadastrar/page";

const sessao = vi.hoisted(() => ({ estadoAutenticacao: vi.fn(), usuarioDaSessao: vi.fn() }));
vi.mock("@/lib/sessao", () => sessao);
vi.mock("@/components/auth/MolduraDeConta", () => ({
  MolduraDeConta: ({ children }: { children: ReactNode }) => <main>{children}</main>,
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  redirect: (destino: string) => { throw new Error(`REDIRECT:${destino}`); },
}));

const token = "a".repeat(43);
const parametros = (convite?: string) => ({ searchParams: Promise.resolve({ convite }) });

beforeEach(() => {
  sessao.usuarioDaSessao.mockReset().mockResolvedValue(null);
  sessao.estadoAutenticacao.mockReset().mockResolvedValue({ estado: "disponivel", cadastroExigeCodigo: true });
});

describe.each([PaginaEntrar, PaginaCadastrar])("estado das páginas de acesso", (pagina) => {
  it("falha da API não abre formulário e permite tentar de novo sem perder o convite", async () => {
    sessao.estadoAutenticacao.mockResolvedValue({ estado: "indisponivel" });
    const html = renderToStaticMarkup(await pagina(parametros(token)));
    expect(html).not.toContain("<form");
    expect(html).toContain('role="alert"');
    expect(html).toContain(`?convite=${token}`);
    expect(html).not.toContain('href="/dashboard"');
  });

  it("modo aberto confirmado oferece dashboard, não um formulário sem login", async () => {
    sessao.estadoAutenticacao.mockResolvedValue({ estado: "desativado" });
    const html = renderToStaticMarkup(await pagina(parametros()));
    expect(html).not.toContain("<form");
    expect(html).toContain('href="/dashboard"');
  });

  it.each([undefined, token])("sessão logada retorna ao destino interno correto: %s", async (convite) => {
    sessao.usuarioDaSessao.mockResolvedValue({ id: 1 });
    await expect(pagina(parametros(convite))).rejects.toThrow(`REDIRECT:${convite ? `/convite/${token}` : "/dashboard"}`);
  });
});

describe("exigência de admissão na página de cadastro", () => {
  it("convite de equipe válido elimina a exigência de outro código", async () => {
    const html = renderToStaticMarkup(await PaginaCadastrar(parametros(token)));
    expect(html).toContain("<form");
    expect(html).not.toContain('name="codigo_dev"');
  });

  it("convite malformado não contorna a admissão", async () => {
    const html = renderToStaticMarkup(await PaginaCadastrar(parametros("invalido")));
    expect(html).toMatch(/<input(?=[^>]*name="codigo_dev")(?=[^>]*required="")[^>]*>/);
    const divulgacao = html.match(/<details\b[^>]*>[\s\S]*?<\/details>/)?.[0];
    expect(divulgacao).toContain('name="codigo_dev"');
    expect(divulgacao?.match(/^<details[^>]*>/)?.[0]).not.toMatch(/\bopen(?:=|\s|>)/);
    expect(html).not.toContain("?convite=invalido");
  });
});
