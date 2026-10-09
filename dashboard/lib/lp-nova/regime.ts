/**
 * O REGIME DA CENA da LP nova: quanto a GPU pode gastar, e por que.
 *
 * Tres regimes. `vivo-alto` e onde todo visitante com WebGPU comeca;
 * `vivo-baixo` e a descida UNICA quando o aparelho nao segura (o padrao
 * `adaptive-quality` do vgpu: nada sobe sozinho, entao nao ha oscilacao nem
 * histerese para ajustar); `poster` e o PNG renderizado do mesmo WGSL, para
 * quem nao tem WebGPU ou pediu movimento reduzido.
 *
 * O motivo viaja junto porque a pagina o ESCREVE: estado vazio nomeia o que
 * falta, e uma cena parada sem explicacao parece pagina quebrada.
 */
export type Regime = "vivo-alto" | "vivo-baixo" | "poster";
export type MotivoRegime =
  | "inicial"
  | "sem-webgpu"
  | "falha-gpu"
  | "movimento-reduzido"
  | "quadros"
  | "bateria";
export type Sinais = { temWebGpu: boolean; movimentoReduzido: boolean; falhouInit: boolean };
export type EstadoRegime = { regime: Regime; motivo: MotivoRegime };

export const PARTICULAS: Record<"vivo-alto" | "vivo-baixo", { desktop: number; celular: number }> = {
  "vivo-alto": { desktop: 120_000, celular: 16_000 },
  "vivo-baixo": { desktop: 30_000, celular: 4_000 },
};

export function regimeInicial(s: Sinais): EstadoRegime {
  // Movimento reduzido congela, nao desacelera (DESIGN.md): vence ate a GPU boa.
  if (s.movimentoReduzido) return { regime: "poster", motivo: "movimento-reduzido" };
  if (!s.temWebGpu) return { regime: "poster", motivo: "sem-webgpu" };
  if (s.falhouInit) return { regime: "poster", motivo: "falha-gpu" };
  return { regime: "vivo-alto", motivo: "inicial" };
}

export function rebaixar(atual: Regime, motivo: "quadros" | "bateria"): EstadoRegime {
  if (atual === "vivo-alto") return { regime: "vivo-baixo", motivo };
  // Baixo nao desce para poster (o visitante ja viu a cena viva) e nada sobe.
  return { regime: atual, motivo };
}

const DESCRICAO: Record<MotivoRegime, string | null> = {
  inicial: null,
  "sem-webgpu": "sem WebGPU",
  "falha-gpu": "a GPU recusou",
  "movimento-reduzido": "movimento reduzido",
  quadros: "quadros lentos",
  bateria: "bateria baixa",
};

export function rotuloDoRegime(regime: Regime, motivo: MotivoRegime): string {
  const partes =
    regime === "poster" ? ["pôster"] : ["GPU", regime === "vivo-alto" ? "alto" : "baixo"];
  const descricao = DESCRICAO[motivo];
  if (descricao) partes.push(descricao);
  return partes.join(" · ");
}

const ORCAMENTO_MS = 24; // acima disso por 2 s seguidos, o aparelho nao segura
const JANELA_QUADROS = 120;
// Um "quadro" maior que isto nao e lentidao: e a aba voltando de oculta, ou a
// primeira compilacao de pipeline. Contado, ele rebaixaria um aparelho bom
// para sempre (nada sobe sozinho).
const QUADRO_ANOMALO_MS = 250;

/**
 * A SAUDE DE QUADROS: decide a descida unica do padrao `adaptive-quality`.
 * Media movel de 120 quadros acima do orcamento por mais de 2 s seguidos.
 */
export class SaudeDeQuadros {
  private duracoes: number[] = [];
  private lentoDesde = 0;

  /** Registra um quadro; devolve true no quadro em que a descida deve acontecer. */
  registrar(ms: number, agora: number): boolean {
    if (ms > QUADRO_ANOMALO_MS) {
      this.duracoes = [];
      this.lentoDesde = 0;
      return false;
    }
    this.duracoes.push(ms);
    if (this.duracoes.length > JANELA_QUADROS) this.duracoes.shift();
    if (this.duracoes.length < JANELA_QUADROS) return false;
    const media = this.duracoes.reduce((a, b) => a + b, 0) / this.duracoes.length;
    if (media <= ORCAMENTO_MS) {
      this.lentoDesde = 0;
      return false;
    }
    if (!this.lentoDesde) this.lentoDesde = agora;
    return agora - this.lentoDesde > 2000;
  }
}
