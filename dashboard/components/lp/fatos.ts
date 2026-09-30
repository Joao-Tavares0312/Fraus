/**
 * OS FATOS DO PRODUTO QUE A VITRINE ANUNCIA, num lugar so.
 *
 * Sao os numeros do CLAUDE.md, e a vitrine promete "nenhum numero inventado".
 * Um literal solto em cada componente era o que deixava o "39" divergir de
 * `NOMES_FEATURES` sem ninguem ver: em 04/09/2026 o contrato caiu de 40 para
 * 38 e a LP seguiu anunciando 35.
 *
 * `tests/test_derivacoes_dashboard.py` le ESTE arquivo como texto e compara
 * `features` com `len(NOMES_FEATURES)`, e varre a vitrine inteira atras de
 * qualquer outro "N features" digitado a mao. Nao formate os numeros de forma
 * que essa busca deixe de achar -- se o formato mudar, atualize o teste, nao
 * apague a guarda.
 */
export const FATOS_DO_MODELO = {
  familias: 7,
  features: 39,
  bertimbau: 3,
  llms: 0,
} as const;

/** Em duas casas ("07", "00"), como o LED e a telemetria os mostram. */
export function emDuasCasas(n: number): string {
  return String(n).padStart(2, "0");
}
