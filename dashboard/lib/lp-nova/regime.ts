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
