import { afterEach, describe, expect, it, vi } from "vitest";
import { aplicarTema, assinarTema, CHAVE_TEMA, EVENTO_TEMA, lerTema, SCRIPT_ANTI_PISCADA, sincronizarTemaDaRota, temaDaRota, temaValido } from "./tema";

function ambiente(caminho = "/dashboard", preferencia: string | null = "escuro") {
  const classes = new Set(["dark"]);
  const raiz = { classList: { add: (c: string) => classes.add(c), remove: (...cs: string[]) => cs.forEach((c) => classes.delete(c)) }, style: { colorScheme: "dark" } };
  const valores = new Map(preferencia === null ? [] : [[CHAVE_TEMA, preferencia]]);
  const localStorage = { getItem: (c: string) => valores.get(c) ?? null, setItem: (c: string, v: string) => { valores.set(c, v); } };
  const janela = Object.assign(new EventTarget(), { location: { pathname: caminho }, localStorage });
  vi.stubGlobal("window", janela);
  vi.stubGlobal("document", { documentElement: raiz });
  return { classes, raiz, localStorage, janela };
}

afterEach(() => vi.unstubAllGlobals());

describe("preferência de tema", () => {
  it.each([null, "instrumento", "chuva", "claro-inexistente"])("valor legado ou desconhecido %s usa escuro", (valor) => {
    expect(temaValido(valor)).toBe("escuro");
  });
  it("persiste a troca e sincroniza a aba que escreveu", () => {
    const { classes, localStorage } = ambiente();
    const ouvir = vi.fn();
    const desligar = assinarTema(ouvir);
    aplicarTema("claro");
    expect(localStorage.getItem(CHAVE_TEMA)).toBe("claro");
    expect(lerTema()).toBe("claro");
    expect(classes.has("light")).toBe(true);
    expect(classes.has("dark")).toBe(false);
    expect(ouvir).toHaveBeenCalledOnce();
    desligar();
    window.dispatchEvent(new Event(EVENTO_TEMA));
    expect(ouvir).toHaveBeenCalledOnce();
  });
  it("não perde a preferência ao entrar e sair da ferramenta", () => {
    const { classes, localStorage } = ambiente("/dashboard", "claro");
    sincronizarTemaDaRota("/dashboard/atendimentos/abc");
    expect(classes.has("light")).toBe(true);
    sincronizarTemaDaRota("/");
    expect(classes.has("dark")).toBe(true);
    expect(localStorage.getItem(CHAVE_TEMA)).toBe("claro");
    sincronizarTemaDaRota("/dashboard");
    expect(classes.has("light")).toBe(true);
  });
  it.each(["/", "/entrar", "/cadastrar", "/convite/abc", "/dashboardX"])("%s é sempre escuro", (rota) => {
    expect(temaDaRota(rota, "claro")).toBe("escuro");
  });
  it("acompanha storage de outra aba e remove a assinatura", () => {
    const { localStorage } = ambiente();
    const ouvir = vi.fn();
    const desligar = assinarTema(ouvir);
    localStorage.setItem(CHAVE_TEMA, "claro");
    window.dispatchEvent(new Event("storage"));
    expect(lerTema()).toBe("claro");
    expect(ouvir).toHaveBeenCalledOnce();
    desligar();
    window.dispatchEvent(new Event("storage"));
    expect(ouvir).toHaveBeenCalledOnce();
  });
  it("continua utilizável sem acesso a localStorage", () => {
    const { classes } = ambiente();
    vi.spyOn(window.localStorage, "getItem").mockImplementation(() => { throw new Error("bloqueado"); });
    vi.spyOn(window.localStorage, "setItem").mockImplementation(() => { throw new Error("bloqueado"); });
    aplicarTema("claro");
    expect(lerTema()).toBe("claro");
    expect(classes.has("light")).toBe(true);
  });
});

describe("primeira pintura", () => {
  it.each([
    ["/dashboard", "claro", "light"],
    ["/dashboard/modelo", "claro", "light"],
    ["/", "claro", "dark"],
    ["/entrar", "claro", "dark"],
    ["/dashboardX", "claro", "dark"],
    ["/dashboard", "chuva", "dark"],
  ])("%s com preferência %s pinta %s", (rota, preferencia, classe) => {
    const { classes, raiz, localStorage, janela } = ambiente(rota, preferencia);
    new Function("document", "location", "localStorage", SCRIPT_ANTI_PISCADA)({ documentElement: raiz }, janela.location, localStorage);
    expect(classes.has(classe)).toBe(true);
    expect(classes.size).toBe(1);
  });
});
