/**
 * Da CATEGORIA que o servidor gravou para o humor do campo de particulas.
 *
 * Parte da categoria, nao da nota: a faixa ja foi aplicada no servidor
 * (invariante 3), e reaplicar limiar aqui seria a segunda copia da regra que
 * ja divergiu uma vez nas fronteiras 6/7 e 8/9. Sem categoria -- a leitura sem
 * fala do cliente -- o campo fica cinza e parado: ausencia nao e insatisfacao.
 */
export function humorDaCategoria(categoria: string | null): { humor: number; cinza: number } {
  switch (categoria) {
    case "detrator":
      return { humor: -1, cinza: 0 };
    case "neutro":
      return { humor: -0.2, cinza: 0 };
    case "promotor":
      return { humor: 1, cinza: 0 };
    default:
      return { humor: 0, cinza: 1 };
  }
}
