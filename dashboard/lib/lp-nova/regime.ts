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
export type EstadoRegime = {
  regime: Regime;
  motivo: MotivoRegime;
  /** O device continua valido; so a animacao ambiental esta suspensa. */
  pausa?: "repouso" | "aba-oculta";
};

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

export function rotuloDoRegime(regime: Regime, motivo: MotivoRegime, pausa?: EstadoRegime["pausa"]): string {
  const partes =
    regime === "poster" ? ["pôster"] : ["GPU", regime === "vivo-alto" ? "alto" : "baixo"];
  const descricao = DESCRICAO[motivo];
  if (descricao) partes.push(descricao);
  if (regime !== "poster" && pausa) partes.push(pausa === "repouso" ? "em repouso" : "aba oculta");
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
  private duracoes = new Float64Array(JANELA_QUADROS);
  private indice = 0;
  private quantidade = 0;
  private soma = 0;
  private lentoDesde: number | null = null;

  /** Pausa voluntaria nao e um quadro lento nem continuidade da janela. */
  reiniciar() {
    this.indice = 0;
    this.quantidade = 0;
    this.soma = 0;
    this.lentoDesde = null;
  }

  /** Registra um quadro; devolve true no quadro em que a descida deve acontecer. */
  registrar(ms: number, agora: number): boolean {
    if (ms > QUADRO_ANOMALO_MS) {
      this.reiniciar();
      return false;
    }
    if (this.quantidade === JANELA_QUADROS) this.soma -= this.duracoes[this.indice];
    else this.quantidade++;
    this.duracoes[this.indice] = ms;
    this.soma += ms;
    this.indice = (this.indice + 1) % JANELA_QUADROS;
    if (this.quantidade < JANELA_QUADROS) return false;
    const media = this.soma / this.quantidade;
    if (media <= ORCAMENTO_MS) {
      this.lentoDesde = null;
      return false;
    }
    if (this.lentoDesde === null) this.lentoDesde = agora;
    return agora - this.lentoDesde > 2000;
  }
}
