/** Dados puros da coreografia da LP: o que o GSAP anima, sem tocar no DOM. */

/** Numeros do contrato do motor (CLAUDE.md, invariantes 1 e 9). Guardados por
 * `tests/test_lp_fatos.py` contra `NOMES_FEATURES`: se o fusor mudar, a LP falha. */
export const FATOS_LP = [
  { valor: 7, rotulo: "famílias de sinal" },
  { valor: 39, rotulo: "features no fusor" },
  { valor: 3, rotulo: "BERTimbau fine-tunados" },
  { valor: 0, rotulo: "LLMs na inferência" },
] as const;

/** sessionStorage: o preloader toca uma vez por sessao (script inline + cliente). */
export const CHAVE_PRELOADER = "fraus:lp-preloader";

/** Vai no <head> do layout raiz: script dentro de componente nao roda na
 * navegacao cliente (o React avisa). Custo em outras rotas: um getItem. */
export const SCRIPT_PRELOADER = `try{if(sessionStorage.getItem(${JSON.stringify(CHAVE_PRELOADER)}))document.documentElement.dataset.lpPre="visto"}catch(e){}`;

export function formatarContador(valor: number, casas: number) {
  return String(Math.max(0, Math.round(valor))).padStart(casas, "0");
}

/** Ordem do indice lateral; `faixa` e a vitrine horizontal fixada. */
export const SECOES_INDICE = ["inicio", "como-funciona", "sinais", "faixa", "na-pratica", "limites", "fecho"] as const;

export function rotuloIndice(posicao: number) {
  const total = String(SECOES_INDICE.length).padStart(2, "0");
  return `${String(posicao + 1).padStart(2, "0")} / ${total}`;
}

/** Pose do FR em unidades de cena: rotacao em radianos, `x`/`y` na altura do
 * objeto, `gap` entre as cinco placas e `inv` (0 marca, 1 relevo dourado no fecho).
 * As cinco placas sao arte da marca, nunca familias ou features do modelo. */
export type PoseFR = { rx: number; ry: number; rz: number; x: number; y: number; s: number; gap: number; inv: number };
type PoseSecao = Pick<PoseFR, "rx" | "ry" | "rz" | "x" | "s" | "gap">;

export const POSE_INICIAL: PoseFR = { rx: 0.15, ry: -0.5, rz: 0, x: 2.4, y: 0, s: 1, gap: 0.26, inv: 0 };

/** Um alvo por passagem de secao; `x` e multiplicado por 0 no celular. */
export const POSES_POR_SECAO: readonly PoseSecao[] = [
  { rx: 0.1, ry: 0.7, rz: 0, x: -2.6, s: 1, gap: 0.9 },
  { rx: 0.28, ry: -0.9, rz: 0.05, x: 2.6, s: 1, gap: 1.5 },
  { rx: 0, ry: 3.4, rz: 0.1, x: 2.6, s: 1.1, gap: 2 },
  { rx: -0.1, ry: 1.4, rz: 0, x: -2.4, s: 1, gap: 0.5 },
  { rx: 0.05, ry: 0.15, rz: 0, x: 2.7, s: 0.9, gap: 0.15 },
  { rx: 0, ry: Math.PI * 2, rz: 0, x: 0, s: 1.3, gap: 0.26 },
];

/** Campo de poeira dourada: anel de raio 4..11 em torno do FR. PRNG fixo, para
 * que a captura de QA e a pagina publicada mostrem o mesmo ceu. */
export function criarParticulas(quantidade: number) {
  let semente = 0x5f3759df;
  const aleatorio = () => {
    semente = (semente + 0x6d2b79f5) | 0;
    let t = Math.imul(semente ^ (semente >>> 15), 1 | semente);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const pontos = new Float32Array(quantidade * 3);
  for (let i = 0; i < quantidade; i++) {
    const raio = 4 + aleatorio() * 7, angulo = aleatorio() * Math.PI * 2;
    pontos[i * 3] = Math.cos(angulo) * raio;
    pontos[i * 3 + 1] = (aleatorio() - 0.5) * 10;
    pontos[i * 3 + 2] = Math.sin(angulo) * raio - 2;
  }
  return pontos;
}
