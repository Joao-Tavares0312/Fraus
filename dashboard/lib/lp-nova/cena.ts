import type { Compute, Draw, Effect, Gpu, StorageBuffer, Surface } from "vgpu";
import { distribuirEnxames } from "./enxames";
import { pesosDasFases } from "./fases";
import { PARTICULAS, rebaixar, regimeInicial, type EstadoRegime } from "./regime";
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
 * `dispose` idempotente, relogio zerado com a aba oculta para o laco nao
 * "correr atras" do tempo perdido.
 *
 * Qualidade adaptativa no padrao `adaptive-quality`: comeca no alto e desce
 * UMA vez se o quadro medio passar do orcamento; nada sobe sozinho.
 */

const BYTES_POR_PARTICULA = 40; // Particula em comum.wgsl: 3 x vec2f + u32 + 3 x f32
const GRUPO = 256; // @workgroup_size de simular.wgsl
const ORCAMENTO_MS = 24; // acima disso por 2 s seguidos, o aparelho nao segura
const JANELA_QUADROS = 120;

export type Frase = { texto: string; caixa: DOMRect; fonte: string };

export type OpcoesCena = {
  celular: boolean;
  movimentoReduzido: boolean;
  frase: Frase | null;
  aoMudarRegime(estado: EstadoRegime): void;
};

export type CenaLeitura = {
  pronto: Promise<EstadoRegime>;
  definirProgresso(progresso: number): void;
  /** humor em [-1, 1] (detrator .. promotor); cinza = 1 na leitura sem sinal. */
  definirHumor(humor: number, cinza: number): void;
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

function sementeDasParticulas(total: number, origens: Float32Array): ArrayBuffer {
  const bruto = new ArrayBuffer(total * BYTES_POR_PARTICULA);
  const f32 = new Float32Array(bruto);
  const u32 = new Uint32Array(bruto);
  for (const enxame of distribuirEnxames(total)) {
    for (let i = enxame.inicio; i < enxame.inicio + enxame.particulas; i++) {
      const b = (i * BYTES_POR_PARTICULA) / 4;
      f32[b] = origens[i * 2];
      f32[b + 1] = origens[i * 2 + 1];
      f32[b + 2] = 0;
      f32[b + 3] = 0;
      f32[b + 4] = origens[i * 2];
      f32[b + 5] = origens[i * 2 + 1];
      u32[b + 6] = indiceDaFamilia(enxame.chave);
      f32[b + 7] = Math.random();
      f32[b + 8] = 0;
      f32[b + 9] = 0;
    }
  }
  return bruto;
}

const ORDEM_FAMILIAS = distribuirEnxames(7).map((e) => e.chave);
function indiceDaFamilia(chave: string): number {
  return ORDEM_FAMILIAS.indexOf(chave);
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
  let humor = 0;
  let cinza = 0;
  let estado: EstadoRegime = { regime: "poster", motivo: "inicial" };
  const duracoes: number[] = [];
  let lentoDesde = 0;
  let desceu = false;

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
    novo.write(sementeDasParticulas(total, origensDaFrase(opcoes.frase, total, largura, altura)));
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
    const aspecto = canvas.clientWidth / Math.max(1, canvas.clientHeight);
    const p = pesosDasFases(progresso);
    // Desktop: o orbe mora no terco direito, ao lado do texto. Celular: no alto.
    const foco = opcoes.celular ? [0, 0.42] : [aspecto * 0.42, 0];
    const raio = opcoes.celular ? 0.24 : 0.3;
    const escala = opcoes.celular ? 0.8 : 1;
    const centros = distribuirEnxames(7).map((e) => [
      foco[0] + (e.centro[0] - 0.5) * 2 * 0.62 * escala,
      foco[1] - (e.centro[1] - 0.5) * 2 * 0.62 * escala,
      0,
      0,
    ]);
    return {
      tempo,
      dt,
      aspecto,
      total,
      destino: [p.frase, p.disperso, p.enxame, p.orbe],
      leitura: [p.leitura, p.brilho, p.respira, humor],
      foco: [foco[0], foco[1], raio, cinza],
      // Ganho de alfa: a luz somada do campo fica parecida com 4 mil ou 120 mil.
      ponto: [((opcoes.celular ? 2.2 : 1.6) / Math.max(1, canvas.clientHeight)) * 2, escala, Math.min(1, 6000 / total), 0],
      // Desktop: metade direita, o texto mora na esquerda. Celular: faixa de cima.
      campo: opcoes.celular ? [0, 0.55, aspecto * 0.95, 0.4] : [aspecto * 0.5, 0, aspecto * 0.5, 0.9],
      centros,
    };
  }

  function medir(ms: number, agora: number) {
    if (estado.regime !== "vivo-alto") return;
    duracoes.push(ms);
    if (duracoes.length > JANELA_QUADROS) duracoes.shift();
    if (duracoes.length < JANELA_QUADROS) return;
    const media = duracoes.reduce((a, b) => a + b, 0) / duracoes.length;
    if (media <= ORCAMENTO_MS) {
      lentoDesde = 0;
      return;
    }
    if (!lentoDesde) lentoDesde = agora;
    if (agora - lentoDesde > 2000) desceu = true;
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
      alvo = vgpu.surface(g, canvas, { dpr: [1, opcoes.celular ? 1.5 : 2] });
      orbe = vgpu.effect(g, orbeWgsl, { label: "orbe" });
      mudar(inicial);
      semear(vgpu, g);

      const passo = (agora: number) => {
        if (encerrada) return;
        if (!document.hidden && simular && desenho && orbe && alvo && buffer) {
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
          medir(agora - anterior, agora);
          if (desceu) {
            desceu = false;
            mudar(rebaixar(estado.regime, "quadros"));
            semear(vgpu, g);
          }
        }
        anterior = agora;
        quadro = requestAnimationFrame(passo);
      };
      anterior = performance.now();
      quadro = requestAnimationFrame(passo);
      return estado;
    } catch {
      if (encerrada) return estado;
      dispose();
      const falhou = regimeInicial({ temWebGpu, movimentoReduzido: false, falhouInit: true });
      mudar(falhou);
      return falhou;
    }
  })();

  return {
    pronto,
    definirProgresso(p) {
      progresso = p;
    },
    definirHumor(h, c) {
      humor = h;
      cinza = c;
    },
    dispose,
  };
}
