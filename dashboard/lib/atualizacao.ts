export const CHAVE_ATUALIZACAO = "fraus:dados-atualizados";

/** Somente um aviso de invalidacao, nunca conversa, token ou dado pessoal. */
export function anunciarAtualizacao() {
  window.dispatchEvent(new Event(CHAVE_ATUALIZACAO));
  try { localStorage.setItem(CHAVE_ATUALIZACAO, String(Date.now())); } catch { /* armazenamento indisponivel */ }
}

/** Voltar a uma aba que acabou de ser lida nao justifica reler tudo. */
export const INTERVALO_MINIMO_FOCO_MS = 60_000;

export function deveAtualizarNoFoco(agora: number, ultima: number): boolean {
  return agora - ultima >= INTERVALO_MINIMO_FOCO_MS;
}
