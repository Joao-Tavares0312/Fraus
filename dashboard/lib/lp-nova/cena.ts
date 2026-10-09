import type { Compute, Draw, Effect, Gpu, StorageBuffer, Surface } from "vgpu";
import { BYTES_POR_PARTICULA, sementeDasParticulas, uniformesDoQuadro } from "./quadro";
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
  let total = 0;
  let progresso = 0;
  let rolagem = 0;
  let humor = 0;
  let cinza = 0;
  let estado: EstadoRegime = { regime: "poster", motivo: "inicial" };
  const saude = new SaudeDeQuadros();
  let frase = opcoes.frase;
  let ressemear = false;

  function dispose() {
    if (encerrada) return;
    encerrada = true;
    if (quadro) cancelAnimationFrame(quadro);
    gpu?.dispose();
  }

  function mudar(novo: EstadoRegime) {
    estado = novo;
    opcoes.aoMudarRegime(novo);
  }

  function semear(vgpu: typeof import("vgpu"), g: Gpu) {
    const faixa = estado.regime === "vivo-baixo" ? PARTICULAS["vivo-baixo"] : PARTICULAS["vivo-alto"];
    total = opcoes.celular ? faixa.celular : faixa.desktop;
    const largura = window.innerWidth;
    const altura = window.innerHeight;
    const novo = vgpu.storage(g, total * BYTES_POR_PARTICULA, "read-write");
    novo.write(sementeDasParticulas(total, origensDaFrase(frase, total, largura, altura), Math.random));
    // O tipo publico nao expoe `destroy`, mas o objeto tem -- o exemplo
    // `fluid` do vgpu libera os buffers pela mesma coercao.
    (buffer as unknown as { destroy(): void } | undefined)?.destroy();
    buffer = novo;
    simular = vgpu.compute(g, simularWgsl, { label: "simular" });
    desenho = vgpu.draw(g, {
      shader: particulasWgsl,
      vertices: 6,
      instances: total,
      blend: { color: { src: "one", dst: "one" }, alpha: { src: "one", dst: "one" } },
      label: "particulas",
    });
  }

  function uniformes(dt: number) {
    return uniformesDoQuadro({
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
  }

  function falhar(causa: unknown) {
    if (encerrada) return;
    // Aviso, nao erro: a pagina segue inteira no poster, e o codigo VGPU ajuda
    // quem for depurar o aparelho.
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
      const vgpu = await import("vgpu");
      if (encerrada) return estado;
      const g = await vgpu.init();
      if (encerrada) {
        g.dispose();
        return estado;
      }
      gpu = g;
      // Pipelines de render nascem preguicosos no primeiro draw; a falha deles
      // chega por aqui, assincrona, e nao pelo try.
      g.onError((erro) => falhar(erro));
      alvo = vgpu.surface(g, canvas, { dpr: [1, opcoes.celular ? 1.5 : 2] });
      orbe = vgpu.effect(g, orbeWgsl, { label: "orbe" });
      mudar(inicial);
      semear(vgpu, g);

      const passo = (agora: number) => {
        if (encerrada) return;
        try {
          if (!document.hidden && simular && desenho && orbe && alvo && buffer) {
            if (ressemear) {
              ressemear = false;
              semear(vgpu, g);
            }
            const dt = Math.min(1 / 30, (agora - anterior) / 1000);
            tempo += dt;
            const u = uniformes(dt);
            simular.set({ cena: u, particulas: buffer }).dispatch(Math.ceil(total / GRUPO));
            desenho.set({ cena: u, particulas: buffer });
            orbe.set({ cena: u });
            const fundo = orbe;
            const campo = desenho;
            vgpu.frame(g, (f) =>
              f.pass(alvo!, (pass) => {
                pass.draw(fundo);
                pass.draw(campo);
              }),
            );
            if (estado.regime === "vivo-alto" && saude.registrar(agora - anterior, agora)) {
              mudar(rebaixar(estado.regime, "quadros"));
              semear(vgpu, g);
            }
          }
        } catch (erro) {
          falhar(erro);
          return;
        }
        anterior = agora;
        quadro = requestAnimationFrame(passo);
      };
      anterior = performance.now();
      quadro = requestAnimationFrame(passo);
      return estado;
    } catch (erro) {
      falhar(erro);
      return estado;
    }
  })();

  return {
    pronto,
    definirProgresso(p, r = 0) {
      progresso = p;
      rolagem = r;
    },
    refazerFrase(nova) {
      frase = nova;
      ressemear = true;
    },
    definirHumor(h, c) {
      humor = h;
      cinza = c;
    },
    dispose,
  };
}
