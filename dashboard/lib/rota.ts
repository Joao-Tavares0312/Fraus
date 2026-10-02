/**
 * O id de um atendimento como ele chega no parametro dinamico da rota.
 *
 * Todo link para `/dashboard/atendimentos/[id]` e montado com
 * `encodeURIComponent`, e o Next entrega o segmento AINDA codificado
 * (`analise%3A...`). `obterConversa` codifica de novo para a API -- sem desfazer
 * aqui, `:` virava `%253A` e a API respondia 404. Foi assim em producao ate
 * 02/10/2026: nenhum atendimento salvo pela tela de Analisar abria.
 *
 * Percent solto (`100%`) nao e codificacao valida e passa como veio, em vez de
 * derrubar a pagina com `URIError`.
 */
export function idDaRota(segmento: string): string {
  try {
    return decodeURIComponent(segmento);
  } catch {
    return segmento;
  }
}
