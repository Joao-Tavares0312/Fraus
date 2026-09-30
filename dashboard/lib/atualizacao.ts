export const CHAVE_ATUALIZACAO = "fraus:dados-atualizados";

/** Somente um aviso de invalidacao, nunca conversa, token ou dado pessoal. */
export function anunciarAtualizacao() {
  window.dispatchEvent(new Event(CHAVE_ATUALIZACAO));
  try { localStorage.setItem(CHAVE_ATUALIZACAO, String(Date.now())); } catch { /* armazenamento indisponivel */ }
}
