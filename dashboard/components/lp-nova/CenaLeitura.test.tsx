import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { acompanharCena } from "./CenaLeitura";
import type { CenaLeitura as Cena } from "@/lib/lp-nova/cena";

const motor = vi.hoisted(() => ({ iniciarCena: vi.fn() }));
vi.mock("@/lib/lp-nova/cena", () => motor);

class ConsultaMedia extends EventTarget {
  constructor(public matches: boolean) { super(); }
  mudar(matches: boolean) {
    if (matches === this.matches) return;
    this.matches = matches;
    this.dispatchEvent(new Event("change"));
  }
}

let celular: ConsultaMedia;
let movimento: ConsultaMedia;
let liberarFontes: () => void;
let fontes: Promise<void>;
let janela: EventTarget & { scrollY: number; innerHeight: number };
let soltar: (() => void) | undefined;
const canvas = { closest: () => null } as unknown as HTMLCanvasElement;

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  soltar = undefined;
  celular = new ConsultaMedia(true);
  movimento = new ConsultaMedia(false);
  fontes = new Promise<void>((resolve) => { liberarFontes = resolve; });
  const consultas: Record<string, ConsultaMedia> = {
    "(max-width: 899px)": celular,
    "(prefers-reduced-motion: reduce)": movimento,
  };
  janela = Object.assign(new EventTarget(), {
    scrollY: 800,
    innerHeight: 800,
    matchMedia: (consulta: string) => consultas[consulta],
    setTimeout,
    clearTimeout,
  });
  vi.stubGlobal("window", janela);
  vi.stubGlobal("document", Object.assign(new EventTarget(), {
    fonts: { ready: fontes },
    documentElement: { scrollHeight: 2400 },
    querySelector: () => null,
    querySelectorAll: () => [
      { dataset: { marco: "frase" }, getBoundingClientRect: () => ({ top: -janela.scrollY, width: 1, height: 1 }) },
      { dataset: { marco: "fecho" }, getBoundingClientRect: () => ({ top: 1600 - janela.scrollY, width: 1, height: 1 }) },
    ],
  }));
  motor.iniciarCena.mockImplementation(() => ({
    pronto: Promise.resolve({ regime: "vivo-alto", motivo: "inicial" }),
    definirProgresso: vi.fn(),
    definirHumor: vi.fn(),
    refazerFrase: vi.fn(),
    dispose: vi.fn(),
  }));
});

afterEach(() => {
  soltar?.();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("preferencias vivas da cena", () => {
  it("reduce em runtime descarta cada cena anterior antes de montar a proxima", async () => {
    const cena: { current: Cena | null } = { current: null };
    const humor: { current: [number, number] } = { current: [-0.7, 0] };
    soltar = acompanharCena(canvas, cena, humor, vi.fn());
    expect(motor.iniciarCena).not.toHaveBeenCalled();
    liberarFontes();
    await fontes;
    const viva = motor.iniciarCena.mock.results[0].value;
    movimento.mudar(true);
    expect(viva.dispose).toHaveBeenCalledTimes(1);
    const poster = cena.current!;
    humor.current = [0.4, 1];
    janela.scrollY = 1200;
    movimento.mudar(false);
    expect(poster.dispose).toHaveBeenCalledTimes(1);
  });


  it("reduce antes das fontes usa poster imediato e fontes tardias nao revivem GPU", async () => {
    const cena: { current: Cena | null } = { current: null };
    soltar = acompanharCena(canvas, cena, { current: [0, 0] }, vi.fn());
    movimento.mudar(true);
    expect(motor.iniciarCena).toHaveBeenCalledTimes(1);
    const poster = cena.current!;
    soltar();
    soltar();
    liberarFontes();
    await fontes;
    movimento.mudar(false);
    celular.mudar(false);
    expect(motor.iniciarCena).toHaveBeenCalledTimes(1);
    expect(poster.dispose).toHaveBeenCalledTimes(1);
    expect(cena.current).toBeNull();
  });

  it("cleanup cancela debounce e remove handlers mesmo apos remontagens", async () => {
    const cena: { current: Cena | null } = { current: null };
    soltar = acompanharCena(canvas, cena, { current: [0, 0] }, vi.fn());
    liberarFontes();
    await fontes;
    const primeira = cena.current!;
    janela.dispatchEvent(new Event("resize"));
    celular.mudar(false);
    const ultima = cena.current!;
    janela.dispatchEvent(new Event("resize"));
    soltar();
    janela.dispatchEvent(new Event("scroll"));
    janela.dispatchEvent(new Event("resize"));
    vi.advanceTimersByTime(500);
    expect(primeira.refazerFrase).not.toHaveBeenCalled();
    expect(ultima.refazerFrase).not.toHaveBeenCalled();
    expect(primeira.dispose).toHaveBeenCalledTimes(1);
    expect(ultima.dispose).toHaveBeenCalledTimes(1);
  });

  it("ignora marcos sem caixa e reancora ao abrir ou fechar aprofundamento", async () => {
    let topoDosNos = 1400;
    let avisarLayout!: () => void;
    const observar = vi.fn();
    const desconectar = vi.fn();
    vi.stubGlobal("ResizeObserver", class {
      constructor(callback: () => void) { avisarLayout = callback; }
      observe = observar;
      disconnect = desconectar;
    });
    const raiz = { dataset: {} };
    const alvo = { closest: () => raiz } as unknown as HTMLCanvasElement;
    vi.spyOn(document, "querySelectorAll").mockImplementation(() => [
      { dataset: { marco: "frase" }, getBoundingClientRect: () => ({ top: -janela.scrollY, width: 1, height: 1 }) },
      { dataset: { marco: "mascara" }, getBoundingClientRect: () => ({ top: 0, width: 0, height: 0 }) },
      { dataset: { marco: "nos" }, getBoundingClientRect: () => ({ top: topoDosNos - janela.scrollY, width: 1, height: 1 }) },
      { dataset: { marco: "fecho" }, getBoundingClientRect: () => ({ top: 1600 - janela.scrollY, width: 1, height: 1 }) },
    ] as unknown as NodeListOf<Element>);
    const cena: { current: Cena | null } = { current: null };
    soltar = acompanharCena(alvo, cena, { current: [0, 0] }, vi.fn());
    liberarFontes();
    await fontes;
    const progresso = vi.mocked(cena.current!.definirProgresso);
    expect(observar).toHaveBeenCalledWith(raiz);
    expect(progresso.mock.calls.at(-1)?.[0]).toBeCloseTo(0.304);
    topoDosNos = 1800;
    document.dispatchEvent(new Event("toggle"));
    expect(progresso.mock.calls.at(-1)?.[0]).toBeCloseTo(0.38 * 800 / 1400);
    topoDosNos = 1400;
    document.dispatchEvent(new Event("toggle"));
    expect(progresso.mock.calls.at(-1)?.[0]).toBeCloseTo(0.304);
    topoDosNos = 1800;
    avisarLayout();
    expect(progresso.mock.calls.at(-1)?.[0]).toBeCloseTo(0.38 * 800 / 1400);
    soltar();
    expect(desconectar).toHaveBeenCalledTimes(1);
    progresso.mockClear();
    document.dispatchEvent(new Event("toggle"));
    expect(progresso).not.toHaveBeenCalled();
  });
});
