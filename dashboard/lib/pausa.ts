/**
 * A PAUSA NOTADA: o comprimento de uma espera, como fracao de uma regua.
 *
 * Na notacao do DESIGN.md a pausa e "silencio com duracao notada" -- e a espera
 * do cliente, e o comprimento dela e a informacao. Este arquivo so decide QUANTO
 * da regua a espera ocupa; quem a desenha e `Transcricao`.
 *
 * A REGUA NAO E DIGITADA AQUI. O fundo de escala e o limiar de DEGRADACAO
 * vigente (`LimiaresLatencia.degradando`, lido de `GET /configuracoes`): uma
 * espera que chega ao limiar ocupa a regua inteira, e uma que o passa continua
 * ocupando so ela (o excesso nao cresce -- a regua e o teto, nao uma escala
 * aberta). Digitar 180 s aqui seria copiar em TypeScript uma regra que a tela
 * de Configuracoes move, e a copia divergiria no primeiro ajuste (mesma
 * disciplina da invariante 4).
 *
 * Latencia nunca e persistida (invariante 5): o `segundos` que chega aqui foi
 * derivado dos timestamps na leitura, e a fracao tambem e derivada na hora.
 */
import type { LimiaresLatencia } from "./derivacoes";

/** Piso visivel: uma pausa de 1 s e uma pausa, e nao pode virar risco de 0 px. */
const FRACAO_MINIMA = 0.02;

export function fracaoDaPausa(
  segundos: number,
  limiares: LimiaresLatencia,
): number {
  if (!Number.isFinite(segundos) || segundos <= 0) return FRACAO_MINIMA;
  const teto = limiares.degradando;
  if (!Number.isFinite(teto) || teto <= 0) return 1;
  return Math.min(1, Math.max(FRACAO_MINIMA, segundos / teto));
}
