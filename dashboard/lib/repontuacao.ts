/**
 * O progresso da repontuacao, lido do servidor e traduzido para a tela.
 *
 * Desde 15/09/2026 `POST /conversas/repontuar` responde 202 e sai; o trabalho
 * roda em segundo plano e `GET` na mesma rota diz onde ele esta. O que mora
 * aqui e so a TRADUCAO -- funcao pura, sem fetch e sem relogio -- para ser
 * testada sem servidor. Quem busca e quem espera e o componente.
 *
 * Nada aqui calcula nota (invariante 3): `feitas` e `total` sao contagens do
 * servidor, e a fracao existe so para a barra.
 */

export type EstadoDoServidor = {
  estado: "rodando" | "concluido" | "falhou";
  total: number;
  feitas: number;
  erro: string | null;
};

export type Leitura =
  | { tipo: "parado" }
  | { tipo: "rodando"; feitas: number; total: number; fracao: number }
  | { tipo: "concluido"; total: number }
  | { tipo: "falhou"; feitas: number; total: number; mensagem: string };

/** Intervalo entre consultas. Um BERTimbau por conversa leva centenas de ms:
 * consultar mais rapido que isso so repete o mesmo numero. */
export const INTERVALO_DE_CONSULTA_MS = 1000;

/**
 * `null` e o 404 do servidor: nenhuma repontuacao desde que a API subiu.
 */
export function lerProgresso(corpo: EstadoDoServidor | null): Leitura {
  if (corpo === null) return { tipo: "parado" };
  if (corpo.estado === "concluido") return { tipo: "concluido", total: corpo.total };
  if (corpo.estado === "falhou") {
    return {
      tipo: "falhou",
      feitas: corpo.feitas,
      total: corpo.total,
      mensagem: corpo.erro ?? "a repontuação parou sem dizer por quê",
    };
  }
  // Banco vazio rodando e um instante: fracao 0, nunca divisao por zero.
  const fracao = corpo.total > 0 ? Math.min(1, corpo.feitas / corpo.total) : 0;
  return { tipo: "rodando", feitas: corpo.feitas, total: corpo.total, fracao };
}
