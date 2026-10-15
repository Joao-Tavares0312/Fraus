import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { iniciarCena, type CenaLeitura } from "./cena";

const vgpu = vi.hoisted(() => ({
  init: vi.fn(),
  storage: vi.fn(),
  compute: vi.fn(),
  draw: vi.fn(),
  effect: vi.fn(),
  surface: vi.fn(),
  frame: vi.fn(),
}));
vi.mock("vgpu", () => vgpu);
vi.mock("./shaders/orbe.wgsl", () => ({ default: "orbe" }));
vi.mock("./shaders/particulas.wgsl", () => ({ default: "particulas" }));
vi.mock("./shaders/simular.wgsl", () => ({ default: "simular" }));

// Dubles de scheduling/lifecycle, nao um benchmark: a cadencia e fornecida
// pelo teste e nao mede performance, validacao WGSL ou assentamento visual.
const gpu = { dispose: vi.fn(), onError: vi.fn() };
const computacao = { set: vi.fn(), dispatch: vi.fn() };
const desenho = { set: vi.fn() };
const orbe = { set: vi.fn() };
const canvas = { clientWidth: 390, clientHeight: 844 } as HTMLCanvasElement;
const opcoes = { celular: true, movimentoReduzido: false, frase: null, aoMudarRegime: vi.fn() };
let documento: EventTarget & { hidden: boolean };
let janela: EventTarget & { innerWidth: number; innerHeight: number };
let agendados: Map<number, FrameRequestCallback>;
let agora: number;
let cenas: CenaLeitura[];

function avancar(ms = 16) {
  agora += ms;
  const callbacks = [...agendados.values()];
  agendados.clear();
  for (const callback of callbacks) callback(agora);
}

beforeEach(() => {
  vi.resetAllMocks();
  cenas = [];
  agora = 0;
  agendados = new Map();
  let id = 0;
  documento = Object.assign(new EventTarget(), { hidden: false });
  janela = Object.assign(new EventTarget(), { innerWidth: 390, innerHeight: 844 });
  vi.stubGlobal("document", documento);
  vi.stubGlobal("window", janela);
  vi.stubGlobal("navigator", { gpu: {} });
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    agendados.set(++id, callback);
    return id;
  });
  vi.stubGlobal("cancelAnimationFrame", (quadro: number) => agendados.delete(quadro));
  vi.spyOn(performance, "now").mockImplementation(() => agora);
  vi.spyOn(console, "warn").mockImplementation(() => {});
  vgpu.init.mockResolvedValue(gpu);
  vgpu.storage.mockImplementation(() => ({ write: vi.fn(), destroy: vi.fn() }));
  computacao.set.mockReturnValue(computacao);
  desenho.set.mockReturnValue(desenho);
  orbe.set.mockReturnValue(orbe);
  vgpu.compute.mockReturnValue(computacao);
  vgpu.draw.mockReturnValue(desenho);
  vgpu.effect.mockReturnValue(orbe);
  vgpu.surface.mockReturnValue({});
});

afterEach(() => {
  for (const cena of cenas) cena.dispose();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("ciclo de vida da cena", () => {
  it("reduce nao inicializa GPU nem agenda quadros", async () => {
    const cena = iniciarCena(canvas, { ...opcoes, movimentoReduzido: true });
    cenas.push(cena);
    expect(await cena.pronto).toEqual({ regime: "poster", motivo: "movimento-reduzido" });
    expect(vgpu.init).not.toHaveBeenCalled();
    expect(agendados.size).toBe(0);
    cena.definirHumor(-1, 0);
    cena.refazerFrase(null);
    expect(agendados.size).toBe(0);
  });

  it("dispose durante init tardio destroi o device recebido e nunca o monta", async () => {
    let liberar!: (valor: typeof gpu) => void;
    const pendente = new Promise<typeof gpu>((resolve) => { liberar = resolve; });
    let avisarInicio!: () => void;
    const iniciou = new Promise<void>((resolve) => { avisarInicio = resolve; });
    vgpu.init.mockImplementationOnce(() => {
      avisarInicio();
      return pendente;
    });
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    await iniciou;
    cena.dispose();
    cena.dispose();
    liberar(gpu);
    await cena.pronto;
    expect(gpu.dispose).toHaveBeenCalledTimes(1);
    expect(vgpu.surface).not.toHaveBeenCalled();
    expect(agendados.size).toBe(0);
    expect(opcoes.aoMudarRegime).not.toHaveBeenCalled();
  });

  it("interpola a mudanca de etapa e aceita reversao sem teletransporte", async () => {
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    cena.definirProgresso(0);
    await cena.pronto;
    avancar();
    const raioInicial = computacao.set.mock.lastCall![0].cena.orbe[2];
    cena.definirProgresso(0.26);
    avancar();
    const raioIntermediario = computacao.set.mock.lastCall![0].cena.orbe[2];
    expect(raioIntermediario).toBeLessThan(raioInicial);
    expect(raioIntermediario).toBeGreaterThan(0.25 * 0.18);
    for (let i = 0; i < 100; i++) avancar();
    const raioAssentado = computacao.set.mock.lastCall![0].cena.orbe[2];
    expect(raioAssentado).toBeCloseTo(0.25 * 0.18, 4);
    cena.definirProgresso(0);
    avancar();
    const raioNaVolta = computacao.set.mock.lastCall![0].cena.orbe[2];
    expect(raioNaVolta).toBeGreaterThan(raioAssentado);
    expect(raioNaVolta).toBeLessThan(raioInicial);
  });

  it("mantem o mesmo ritmo em 30 e 60 quadros por segundo", async () => {
    async function raioDepoisDeUmSegundo(fps: number) {
      const cena = iniciarCena(canvas, opcoes);
      cenas.push(cena);
      cena.definirProgresso(0);
      await cena.pronto;
      avancar();
      cena.definirProgresso(0.26);
      for (let i = 0; i < fps; i++) avancar(1000 / fps);
      const raio = computacao.set.mock.lastCall![0].cena.orbe[2];
      cena.dispose();
      return raio;
    }
    expect(await raioDepoisDeUmSegundo(30)).toBeCloseTo(await raioDepoisDeUmSegundo(60), 5);
  });

  it("entra na etapa restaurada sem reproduzir a historia desde o topo", async () => {
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    cena.definirProgresso(0.26, 900);
    await cena.pronto;
    avancar();
    expect(computacao.set.mock.lastCall![0].cena.orbe[2]).toBeCloseTo(0.25 * 0.18);
  });

  it("assenta, para o laço e retoma por gesto sem perder progresso ou humor", async () => {
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    cena.definirProgresso(0.6, 1200);
    cena.definirHumor(-0.8, 0);
    await cena.pronto;
    for (let i = 0; i < 400; i++) avancar();
    expect(agendados.size).toBe(0);
    expect(opcoes.aoMudarRegime).toHaveBeenLastCalledWith({ regime: "vivo-alto", motivo: "inicial", pausa: "repouso" });
    const submits = vgpu.frame.mock.calls.length;
    avancar(120_000);
    expect(vgpu.frame).toHaveBeenCalledTimes(submits);
    janela.dispatchEvent(new Event("pointermove"));
    expect(agendados.size).toBe(0);
    janela.dispatchEvent(new Event("pointerdown"));
    expect(agendados.size).toBe(1);
    avancar();
    const u = computacao.set.mock.lastCall![0].cena;
    expect(u.leitura[3]).toBe(-0.8);
    expect(u.extra[1]).toBeCloseTo((1200 / 844) * 2);
    expect(u.dt).toBeCloseTo(0.016);
    expect(opcoes.aoMudarRegime).toHaveBeenLastCalledWith({ regime: "vivo-alto", motivo: "inicial" });
    cena.dispose();
    cena.dispose();
    janela.dispatchEvent(new Event("keydown"));
    expect(agendados.size).toBe(0);
    expect(gpu.dispose).toHaveBeenCalledTimes(1);
  });

  it("ocultar cancela imediatamente; interacao oculta nao religa o laço", async () => {
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    await cena.pronto;
    avancar();
    const submits = vgpu.frame.mock.calls.length;
    documento.hidden = true;
    documento.dispatchEvent(new Event("visibilitychange"));
    expect(agendados.size).toBe(0);
    janela.dispatchEvent(new Event("keydown"));
    cena.definirHumor(0.6, 0);
    avancar(60_000);
    expect(vgpu.frame).toHaveBeenCalledTimes(submits);
    documento.hidden = false;
    documento.dispatchEvent(new Event("visibilitychange"));
    expect(agendados.size).toBe(1);
    avancar();
    expect(computacao.set.mock.lastCall![0].cena.dt).toBeCloseTo(0.016);
    expect(computacao.set.mock.lastCall![0].cena.leitura[3]).toBe(0.6);
    cena.dispose();
    documento.dispatchEvent(new Event("visibilitychange"));
    expect(agendados.size).toBe(0);
  });

  it("inicio oculto espera visibilidade sem manter um rAF de espera", async () => {
    documento.hidden = true;
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    expect((await cena.pronto).pausa).toBe("aba-oculta");
    expect(agendados.size).toBe(0);
    expect(vgpu.frame).not.toHaveBeenCalled();
    documento.hidden = false;
    documento.dispatchEvent(new Event("visibilitychange"));
    expect(agendados.size).toBe(1);
  });


  it("ressemeia a frase, libera o buffer anterior e preserva a leitura", async () => {
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    cena.definirProgresso(0.6, 1200);
    cena.definirHumor(-0.8, 0);
    await cena.pronto;
    avancar();
    const bufferAnterior = vgpu.storage.mock.results[0].value;
    cena.refazerFrase(null);
    avancar();
    expect(bufferAnterior.destroy).toHaveBeenCalledTimes(1);
    const uniformes = computacao.set.mock.lastCall![0].cena;
    expect(uniformes.leitura[3]).toBe(-0.8);
    expect(uniformes.extra[1]).toBeCloseTo((1200 / 844) * 2);
  });

  it("device lost cai no poster e remove qualquer retomada", async () => {
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    await cena.pronto;
    const aoErro = gpu.onError.mock.lastCall![0];
    aoErro(new Error("device lost"));
    expect(opcoes.aoMudarRegime).toHaveBeenLastCalledWith({ regime: "poster", motivo: "falha-gpu" });
    expect(agendados.size).toBe(0);
    janela.dispatchEvent(new Event("pointerdown"));
    documento.dispatchEvent(new Event("visibilitychange"));
    expect(agendados.size).toBe(0);
    aoErro(new Error("erro tardio"));
    expect(gpu.dispose).toHaveBeenCalledTimes(1);
  });

  it("falha de init nao deixa quadro agendado", async () => {
    vgpu.init.mockRejectedValueOnce(new Error("GPU recusou"));
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    expect(await cena.pronto).toEqual({ regime: "poster", motivo: "falha-gpu" });
    expect(agendados.size).toBe(0);
  });

  it("erro sincrono no submit encerra o laço", async () => {
    vgpu.frame.mockImplementationOnce(() => { throw new Error("pipeline recusado"); });
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    await cena.pronto;
    avancar();
    expect(opcoes.aoMudarRegime).toHaveBeenLastCalledWith({ regime: "poster", motivo: "falha-gpu" });
    expect(agendados.size).toBe(0);
    expect(gpu.dispose).toHaveBeenCalledTimes(1);
  });

  it("erro notificado durante o frame nao agenda outro depois do dispose", async () => {
    vgpu.frame.mockImplementationOnce(() => {
      gpu.onError.mock.lastCall![0](new Error("device lost durante submit"));
    });
    const cena = iniciarCena(canvas, opcoes);
    cenas.push(cena);
    await cena.pronto;
    avancar();
    expect(opcoes.aoMudarRegime).toHaveBeenLastCalledWith({ regime: "poster", motivo: "falha-gpu" });
    expect(agendados.size).toBe(0);
    expect(gpu.dispose).toHaveBeenCalledTimes(1);
  });
});
