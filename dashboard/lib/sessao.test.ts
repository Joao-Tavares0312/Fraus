import { afterEach, describe, expect, it, vi } from "vitest";
import { estadoAutenticacao, loginDisponivel } from "./sessao";

vi.mock("next/headers", () => ({ cookies: vi.fn() }));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("estado público da autenticação", () => {
  it.each([true, false])("preserva a exigência de código publicada: %s", async (exigeCodigo) => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ disponivel: true, cadastro_exige_codigo: exigeCodigo })));
    expect(await estadoAutenticacao()).toEqual({ estado: "disponivel", cadastroExigeCodigo: exigeCodigo });
    expect(await loginDisponivel()).toBe(true);
  });

  it("reconhece modo aberto somente quando o servidor o confirma", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ disponivel: false, cadastro_exige_codigo: false })));
    expect(await estadoAutenticacao()).toEqual({ estado: "desativado" });
    expect(await loginDisponivel()).toBe(false);
  });

  it.each([
    async () => { throw new Error("sem conexão"); },
    async () => new Response("indisponível", { status: 503 }),
    async () => new Response("<html>proxy</html>"),
    async () => Response.json({}),
    async () => Response.json({ disponivel: "false" }),
    async () => Response.json({ disponivel: true }),
  ])("não transforma falha ou contrato incompleto em modo aberto", async (resposta) => {
    vi.stubGlobal("fetch", vi.fn(resposta));
    expect(await estadoAutenticacao()).toEqual({ estado: "indisponivel" });
    expect(await loginDisponivel()).toBe(false);
  });
});
