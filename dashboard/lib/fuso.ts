/**
 * O fuso do produto: Brasilia, fixo em -03:00.
 *
 * Espelha `fraus/fuso.py`. A API agrupa a serie diaria e recorta o periodo
 * pelo dia de Brasilia; se a tela usasse o fuso do navegador, uma conversa das
 * 22:30 apareceria num dia no grafico e em outro na tabela para quem abre o
 * painel de outro fuso -- e no servidor (UTC) o HTML da primeira carga
 * discordaria do que o navegador pinta depois.
 *
 * Offset fixo, e nao "America/Sao_Paulo": o Python usa -03:00 para toda data,
 * e o fuso nomeado devolveria -02:00 nos veroes anteriores a 2019.
 */

const DESLOCAMENTO_MS = -3 * 60 * 60 * 1000;

/**
 * O instante deslocado para Brasilia. Leia com os metodos `getUTC*` ou formate
 * com `timeZone: "UTC"` -- os metodos locais somariam o fuso do navegador.
 */
export function noFusoDoProduto(iso: string): Date {
  return new Date(new Date(iso).getTime() + DESLOCAMENTO_MS);
}

/** Dia (AAAA-MM-DD) de um instante no fuso do produto. */
export function diaDoProduto(iso: string): string {
  return noFusoDoProduto(iso).toISOString().slice(0, 10);
}
