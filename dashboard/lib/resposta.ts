/**
 * Le uma resposta que DEVERIA ser uma lista, sem confundir falha com vazio.
 *
 * O idioma que isto substitui era `Array.isArray(corpo) ? corpo : []` logo
 * depois de `resposta.json()`, sem olhar `resposta.ok`. O proxy devolve
 * `{detail}` em erro, que nao e array -- entao API fora do ar, 401 e 403
 * viravam lista vazia e a tela escrevia "Nenhum termo curado" / "Nenhuma chave
 * de acesso emitida". Afirmar que nao ha nada, sem ter conseguido ler, e a
 * invariante 2 pelo outro lado: ausencia de LEITURA nao e ausencia de dado.
 */
export type LeituraDeLista<T> =
  | { ok: true; itens: T[] }
  | { ok: false; erro: string };

export async function lerListaDaResposta<T>(
  resposta: Response,
): Promise<LeituraDeLista<T>> {
  const corpo: unknown = await resposta.json().catch(() => null);

  if (!resposta.ok) {
    // A frase da API sobe como veio quando e texto (ela e a instrucao: "esta
    // rota exige a chave mestra"). `detail` de validacao e uma LISTA de
    // objetos, e entregar isso ao React como filho derrubaria a tela.
    const detalhe =
      typeof corpo === "object" && corpo !== null && "detail" in corpo
        ? corpo.detail
        : null;
    return {
      ok: false,
      erro:
        typeof detalhe === "string"
          ? detalhe
          : `a API respondeu ${resposta.status}`,
    };
  }

  if (!Array.isArray(corpo)) {
    return {
      ok: false,
      erro: "a API respondeu fora do contrato: era esperada uma lista",
    };
  }
  return { ok: true, itens: corpo as T[] };
}
