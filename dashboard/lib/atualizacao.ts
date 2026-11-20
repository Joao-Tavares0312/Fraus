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

/**
 * De quanto em quanto tempo a aba VISIVEL pergunta se chegou atendimento.
 * A pergunta e um agregado so (`GET /conversas/assinatura`); as leituras da
 * pagina so sao refeitas quando a resposta muda.
 */
export const INTERVALO_DE_SONDA_MS = 15_000;

/**
 * A primeira leitura e a base; so uma assinatura DIFERENTE dela pede releitura.
 * Sonda que falhou (`null`) nao e mudanca: API fora do ar nao pode virar uma
 * releitura completa a cada rodada.
 */
export function mudouAAssinatura(anterior: string | null, atual: string | null): boolean {
  return anterior !== null && atual !== null && anterior !== atual;
}
