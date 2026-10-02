/**
 * Texto que vai para um lugar que o interpreta como HTML.
 *
 * O React escapa sozinho o que renderiza. Isto existe para a UNICA saida da
 * dashboard que nao passa por ele: o tooltip do grafo (`nodeLabel` do
 * force-graph), que a biblioteca escreve com `innerHTML`. O rotulo de um no
 * carrega o id da conversa e o canal, e os dois vem de fora -- de uma chave de
 * fonte em `POST /ingestao` ou do arquivo de um analista. Em 02/10/2026 um id
 * `<img src=x onerror=...>` rodava na sessao de quem passasse o mouse no no.
 */
const ENTIDADES: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

export function escaparHtml(texto: string): string {
  return texto.replace(/[&<>"']/g, (caractere) => ENTIDADES[caractere]);
}
