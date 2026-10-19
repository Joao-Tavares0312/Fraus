import type { FonteIntegracao } from "@/lib/api";

/** A fonte do TARS é a de canal `tars`; a mais antiga vence se houver duas. */
export function fonteDoTars(fontes: FonteIntegracao[]): FonteIntegracao | null {
  return fontes.filter((fonte) => fonte.canal === "tars").sort((a, b) => a.id - b.id)[0] ?? null;
}

/** O endereço que o TARS chama — a API pública, nunca o proxy da dashboard. */
export function urlDeIngestao(baseDaApi: string): string {
  return `${baseDaApi.replace(/\/+$/, "")}/ingestao`;
}
