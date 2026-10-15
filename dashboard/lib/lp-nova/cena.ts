import type { Compute, Draw, Effect, Frame, FramePass, Gpu, StorageBuffer, Surface } from "vgpu";
import type * as Vgpu from "vgpu";
import { BYTES_POR_PARTICULA, sementeDasParticulas, uniformesDoQuadro, type UniformesQuadro } from "./quadro";
import { PARTICULAS, SaudeDeQuadros, rebaixar, regimeInicial, type EstadoRegime } from "./regime";
import orbeWgsl from "./shaders/orbe.wgsl";
import particulasWgsl from "./shaders/particulas.wgsl";
import simularWgsl from "./shaders/simular.wgsl";

/**
 * A CENA DA LP NOVA: o lado imperativo, com vgpu.
 *
 * Um storage buffer guarda o estado de cada particula; um compute shader o
 * avanca a cada quadro e UM `draw` instanciado o le direto da GPU -- a CPU
 * nunca toca uma posicao depois da semente. A historia chega por uniforms: o
 * progresso da rolagem vira pesos (`fases.ts`, puro e testado) e a leitura
 * escolhida vira o humor do campo.
 *
 * Molde: o `renderer.ts` do exemplo `fluid` do vgpu -- import dinamico,
 * `dispose` idempotente, passo limitado a 1/30 s para a volta de uma aba
 * oculta nao "correr atras" do tempo perdido.
 *
 * Qualquer falha DEPOIS do init (device perdido, pipeline recusado na criacao
 * preguicosa, descida de qualidade) derruba a cena para o poster com o motivo
 * escrito -- nunca uma cena congelada com a frase do hero transparente.
 *
 * Qualidade adaptativa no padrao `adaptive-quality`: comeca no alto e desce
 * UMA vez se o quadro medio passar do orcamento; nada sobe sozinho.
 */

const GRUPO = 64; // @workgroup_size de simular.wgsl: 64 cabe em qualquer adaptador, ate no modo de compatibilidade
// Janela de simulacao apos gesto/mudanca: assenta a mola sem manter o fosforo
// e as manchas animando para sempre enquanto a pessoa le.
const ASSENTAMENTO_S = 6;
const CANAIS_SUAVES = ["destino", "orbe", "paleta"] as const;

/** Amortecimento exponencial: mesmo ritmo em qualquer cadencia, sem overshoot. */
function aproximarCanais(atual: number[], alvo: number[], fator: number, inicio = 0, fim = atual.length): boolean {
  let movendo = false;
  for (let i = inicio; i < fim; i++) {
    const delta = alvo[i] - atual[i];
    if (Math.abs(delta) <= 0.0001) atual[i] = alvo[i];
    else {
      atual[i] += delta * fator;
      movendo = true;
    }
  }
  return movendo;
}

/** A caixa vem em coordenadas de DOCUMENTO (top + scrollY): a frase mora no topo da pagina. */
export type Frase = { texto: string; caixa: { left: number; top: number; width: number; height: number }; fonte: string };

export type OpcoesCena = {
  celular: boolean;
  movimentoReduzido: boolean;
  frase: Frase | null;
  aoMudarRegime(estado: EstadoRegime): void;
};

export type CenaLeitura = {
  pronto: Promise<EstadoRegime>;
  definirProgresso(progresso: number, rolagemPx?: number): void;
  /** humor em [-1, 1] (detrator .. promotor); cinza = 1 na leitura sem sinal. */
  definirHumor(humor: number, cinza: number): void;
  /** Ressemeia as particulas com a frase medida de novo (depois de um resize). */
  refazerFrase(frase: Frase | null): void;
  dispose(): void;
};

/** Pixels da frase do hero, no espaco da cena: as particulas nascem nela. */
function origensDaFrase(frase: Frase | null, total: number, largura: number, altura: number): Float32Array {
  const origens = new Float32Array(total * 2);
  const aspecto = largura / altura;
  const pontos: number[] = [];
  if (frase && frase.caixa.width > 0) {
    const w = Math.ceil(frase.caixa.width);
    const h = Math.ceil(frase.caixa.height);
    const tela = document.createElement("canvas");
    tela.width = w;
    tela.height = h;
    const ctx = tela.getContext("2d", { willReadFrequently: true });
    if (ctx) {
      ctx.font = frase.fonte;
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#fff";
      ctx.fillText(frase.texto, 0, h / 2);
      const { data } = ctx.getImageData(0, 0, w, h);
      for (let y = 0; y < h; y += 2) {
        for (let x = 0; x < w; x += 2) {
          if (data[(y * w + x) * 4 + 3] > 128) {
            const px = frase.caixa.left + x;
            const py = frase.caixa.top + y;
            pontos.push(((px / largura) * 2 - 1) * aspecto, 1 - (py / altura) * 2);
          }
        }
      }
    }
  }
  for (let i = 0; i < total; i++) {
    if (pontos.length > 0) {
      const j = (i % (pontos.length / 2)) * 2;
      // Particulas a mais que pixels repetem o glifo com um tremor minimo.
      origens[i * 2] = pontos[j] + (Math.random() - 0.5) * 0.004;
      origens[i * 2 + 1] = pontos[j + 1] + (Math.random() - 0.5) * 0.004;
    } else {
      origens[i * 2] = (Math.random() - 0.5) * 0.4 * aspecto;
      origens[i * 2 + 1] = (Math.random() - 0.5) * 0.2;
    }
  }
  return origens;
}

export function iniciarCena(canvas: HTMLCanvasElement, opcoes: OpcoesCena): CenaLeitura {
  let encerrada = false;
  let gpu: Gpu | undefined;
  let alvo: Surface | undefined;
  let simular: Compute | undefined;
  let desenho: Draw | undefined;
  let orbe: Effect | undefined;
  let buffer: StorageBuffer | undefined;
  let quadro = 0;
  let anterior = 0;
  let tempo = 0;
  let restante = ASSENTAMENTO_S;
  let total = 0;
  let progresso = 0;
  let rolagem = 0;
  let humor = 0;
  let cinza = 0;
  let estado: EstadoRegime = { regime: "poster", motivo: "inicial" };
  const saude = new SaudeDeQuadros();
  let frase = opcoes.frase;
  let ressemear = false;
  let uniformesSujos = true;
  let u: UniformesQuadro | undefined;
  let uniformesAlvo: UniformesQuadro | undefined;
  let emTransicao = false;
  let passo: FrameRequestCallback | undefined;

  function dispose() {
    if (encerrada) return;
    encerrada = true;
    if (quadro) cancelAnimationFrame(quadro);
    quadro = 0;
    document.removeEventListener("visibilitychange", aoMudarVisibilidade);
    window.removeEventListener("pointerdown", retomar);
    window.removeEventListener("keydown", retomar);
    gpu?.dispose();
  }

  function mudar(novo: EstadoRegime) {
    estado = novo;
    opcoes.aoMudarRegime(novo);
  }

  function pausar(pausa: NonNullable<EstadoRegime["pausa"]>) {
    if (quadro) cancelAnimationFrame(quadro);
    quadro = 0;
    anterior = 0;
    saude.reiniciar();
    if (!encerrada && estado.regime !== "poster" && estado.pausa !== pausa) {
      mudar({ ...estado, pausa });
    }
  }

  function retomar() {
    if (encerrada) return;
    restante = ASSENTAMENTO_S;
    if (!passo || quadro || document.hidden) return;
    // O intervalo parado nao pertence a cadencia da GPU, nem deve acelerar a
    // simulacao. Medir so quadros consecutivos depois da retomada.
    saude.reiniciar();
    anterior = performance.now();
    if (estado.pausa) mudar({ regime: estado.regime, motivo: estado.motivo });
    quadro = requestAnimationFrame(passo);
  }

  function aoMudarVisibilidade() {
    if (document.hidden) pausar("aba-oculta");
    else retomar();
  }

  function semear(vgpu: typeof Vgpu, g: Gpu) {
    const faixa = estado.regime === "vivo-baixo" ? PARTICULAS["vivo-baixo"] : PARTICULAS["vivo-alto"];
    const quantidade = opcoes.celular ? faixa.celular : faixa.desktop;
    const novo = vgpu.storage(g, quantidade * BYTES_POR_PARTICULA, "read-write");
    novo.write(sementeDasParticulas(
      quantidade,
      origensDaFrase(frase, quantidade, window.innerWidth, window.innerHeight),
      Math.random,
    ));
    // O tipo publico nao expoe `destroy`, mas o objeto tem -- o exemplo
    // `fluid` do vgpu libera os buffers pela mesma coercao.
    (buffer as unknown as { destroy(): void } | undefined)?.destroy();
    buffer = novo;
    simular ??= vgpu.compute(g, simularWgsl, { label: "simular" });
    // Resize refaz somente a semente. Pipeline/draw novos so se a contagem
    // mudar (descida de qualidade); nunca no caminho quente de um quadro.
    if (!desenho || total !== quantidade) {
      desenho = vgpu.draw(g, {
        shader: particulasWgsl,
        vertices: 6,
        instances: quantidade,
        blend: { color: { src: "one", dst: "one" }, alpha: { src: "one", dst: "one" } },
        label: "particulas",
      });
    }
    total = quantidade;
    uniformesSujos = true;
    restante = ASSENTAMENTO_S;
  }

  function uniformes(dt: number) {
    if (!uniformesAlvo || uniformesSujos) {
      uniformesAlvo = uniformesDoQuadro({
        aspecto: canvas.clientWidth / Math.max(1, canvas.clientHeight),
        alturaPx: canvas.clientHeight,
        total,
        celular: opcoes.celular,
        progresso,
        rolagemPx: rolagem,
        humor,
        cinza,
        tempo,
        dt,
      });
      if (!u) u = uniformesAlvo;
      // Camera, layout e escolha da leitura sao imediatos. So a cenografia
      // interpola: nunca atrasar o scroll real ou o dado escolhido.
      u.aspecto = uniformesAlvo.aspecto;
      u.total = uniformesAlvo.total;
      u.foco = uniformesAlvo.foco;
      u.ponto = uniformesAlvo.ponto;
      u.campo = uniformesAlvo.campo;
      u.extra[1] = uniformesAlvo.extra[1];
      u.leitura[3] = uniformesAlvo.leitura[3];
      u.fosforo[0] = uniformesAlvo.fosforo[0];
      u.fosforo[1] = uniformesAlvo.fosforo[1];
      emTransicao = true;
      uniformesSujos = false;
    }
    if (emTransicao) {
      const fator = 1 - Math.exp(-dt / 0.18);
      emTransicao = false;
      for (const canal of CANAIS_SUAVES) {
        emTransicao = aproximarCanais(u![canal], uniformesAlvo[canal], fator) || emTransicao;
      }
      emTransicao = aproximarCanais(u!.extra, uniformesAlvo.extra, fator, 0, 1) || emTransicao;
      emTransicao = aproximarCanais(u!.leitura, uniformesAlvo.leitura, fator, 0, 3) || emTransicao;
      emTransicao = aproximarCanais(u!.fosforo, uniformesAlvo.fosforo, fator, 2, 4) || emTransicao;
    }
    // Vetores reutilizados durante a transicao e no repouso: nenhum objeto
    // ou buffer novo por quadro. Uma rolagem reversa troca o alvo, nao enfileira.
    u!.tempo = tempo;
    u!.dt = dt;
    return u!;
  }

  function falhar(causa: unknown) {
    if (encerrada) return;
    console.warn("lp-nova: a cena caiu para o poster", causa);
    dispose();
    mudar(regimeInicial({ temWebGpu: true, movimentoReduzido: false, falhouInit: true }));
  }

  const pronto = (async (): Promise<EstadoRegime> => {
    const temWebGpu = typeof navigator !== "undefined" && "gpu" in navigator;
    const inicial = regimeInicial({ temWebGpu, movimentoReduzido: opcoes.movimentoReduzido, falhouInit: false });
    if (inicial.regime === "poster") {
      mudar(inicial);
      return inicial;
    }
    try {
      // vgpu depende da plataforma WebGPU do navegador: carregar so depois
      // desse gate mantem o poster utilizavel em plataformas sem essa API.
      const vgpu = await import("vgpu");
      if (encerrada) return estado;
      const g = await vgpu.init();
      if (encerrada) {
        g.dispose();
        return estado;
      }
      gpu = g;
      // Pipelines de render nascem preguicosos; a falha assincrona tambem
      // desfaz listeners e o rAF, e mantem toda a pagina legivel no poster.
      g.onError(falhar);
      alvo = vgpu.surface(g, canvas, { dpr: [1, opcoes.celular ? 1.5 : 2] });
      orbe = vgpu.effect(g, orbeWgsl, { label: "orbe" });
      mudar(inicial);
      semear(vgpu, g);
      if (encerrada) return estado;

      const recursos = { cena: uniformes(0), particulas: buffer! };
      const fundo = { cena: recursos.cena };
      let bufferVinculado: StorageBuffer | undefined;
      // Callbacks/bags estaveis, inclusive os que codificam o render pass.
      const desenhar = (pass: FramePass) => {
        pass.draw(orbe!);
        pass.draw(desenho!);
      };
      const renderizar = (frame: Frame) => frame.pass(alvo!, desenhar);
      passo = (agora: number) => {
        quadro = 0;
        if (encerrada) return;
        if (document.hidden) {
          pausar("aba-oculta");
          return;
        }
        try {
          if (ressemear) {
            ressemear = false;
            semear(vgpu, g);
          }
          const ms = agora - anterior;
          const dt = Math.min(1 / 30, Math.max(0, ms / 1000));
          tempo += dt;
          recursos.cena = uniformes(dt);
          recursos.particulas = buffer!;
          fundo.cena = recursos.cena;
          if (bufferVinculado !== buffer) {
            simular!.set(recursos);
            desenho!.set(recursos);
            bufferVinculado = buffer;
          } else {
            // Storage nao mudou: nao refazer watchers/bindings de recurso
            // a cada quadro. So os uniforms precisam de outra escrita.
            simular!.set(fundo);
            desenho!.set(fundo);
          }
          simular!.dispatch(Math.ceil(total / GRUPO));
          orbe!.set(fundo);
          vgpu.frame(g, renderizar);
          if (encerrada) return;
          restante -= dt;
          if (estado.regime === "vivo-alto" && saude.registrar(ms, agora)) {
            mudar(rebaixar(estado.regime, "quadros"));
            semear(vgpu, g);
          }
        } catch (erro) {
          falhar(erro);
          return;
        }
        anterior = agora;
        if (restante > 0) quadro = requestAnimationFrame(passo!);
        else pausar("repouso");
      };
      document.addEventListener("visibilitychange", aoMudarVisibilidade);
      window.addEventListener("pointerdown", retomar, { passive: true });
      window.addEventListener("keydown", retomar);
      if (document.hidden) pausar("aba-oculta");
      else retomar();
      return estado;
    } catch (erro) {
      falhar(erro);
      return estado;
    }
  })();

  return {
    pronto,
    definirProgresso(p, r = 0) {
      if (encerrada || (progresso === p && rolagem === r)) return;
      progresso = p;
      rolagem = r;
      uniformesSujos = true;
      retomar();
    },
    refazerFrase(nova) {
      if (encerrada) return;
      frase = nova;
      ressemear = true;
      uniformesSujos = true;
      retomar();
    },
    definirHumor(h, c) {
      if (encerrada || (humor === h && cinza === c)) return;
      humor = h;
      cinza = c;
      uniformesSujos = true;
      retomar();
    },
    dispose,
  };
}
