import { afterEach, describe, expect, it, vi } from "vitest";
import { paletaAtual } from "./desenho";

afterEach(() => vi.unstubAllGlobals());

describe("paleta do grafo", () => {
  it("invalida o cache na troca de tema, não em cada nó", () => {
    let claro = false;
    vi.stubGlobal("document", { documentElement: { classList: { contains: () => claro } } });
    const lerCss = vi.fn(() => ({ getPropertyValue: (token: string) => `${claro ? "claro" : "escuro"}:${token}` }));
    vi.stubGlobal("getComputedStyle", lerCss);
    const escura = paletaAtual();
    expect(paletaAtual()).toBe(escura);
    expect(lerCss).toHaveBeenCalledOnce();
    claro = true;
    const clara = paletaAtual();
    expect(clara).not.toBe(escura);
    expect(clara.rotulo).toBe("claro:--muted-foreground");
    expect(clara.porTipo.emoji).toBe("claro:--no-emoji");
    expect(paletaAtual()).toBe(clara);
    expect(lerCss).toHaveBeenCalledTimes(2);
  });
});
