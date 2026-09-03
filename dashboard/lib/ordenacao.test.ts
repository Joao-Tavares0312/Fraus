import { describe, expect, it } from "vitest";

import { ausenciaNoFim } from "./ordenacao";

/**
 * O teste NAO exercita so o comparador -- ele reproduz o que o motor faz com a
 * resposta dele. Testar `ausenciaNoFim` isolado provaria apenas que ela devolve
 * os numeros que eu escrevi; o defeito morava justamente na composicao com a
 * inversao do TanStack, e um teste que nao inverte teria passado no codigo
 * quebrado.
 *
 * A linha copiada de @tanstack/table-core/dist/features/row-sorting/
 * createSortedRowModel.js:
 *
 *     if (sortInt !== 0) { if (isDesc) sortInt *= -1; return sortInt }
 */
function ordenarComoATabela(
  valores: (number | null)[],
  descendente: boolean,
): (number | null)[] {
  return [...valores].sort((a, b) => {
    const bruto = ausenciaNoFim(a, b, descendente);
    return descendente ? bruto * -1 : bruto;
  });
}

const COM_BURACOS = [7, null, 2, null, 9];

describe("ausencia sempre no fim", () => {
  it("no crescente, os presentes sobem e o nulo fica atras", () => {
    expect(ordenarComoATabela(COM_BURACOS, false)).toEqual([2, 7, 9, null, null]);
  });

  it("no DESCENDENTE -- o primeiro clique -- o nulo tambem fica atras", () => {
    // O defeito: aqui saia [null, null, 9, 7, 2]. Quem clica em "Nota" para
    // achar os piores atendimentos recebia duas linhas "sem sinal" no topo.
    expect(ordenarComoATabela(COM_BURACOS, true)).toEqual([9, 7, 2, null, null]);
  });

  it("a ordem entre os valores PRESENTES continua invertendo normalmente", () => {
    const crescente = ordenarComoATabela(COM_BURACOS, false).filter((v) => v !== null);
    const decrescente = ordenarComoATabela(COM_BURACOS, true).filter((v) => v !== null);
    expect(decrescente).toEqual([...crescente].reverse());
  });

  it("lista so de ausencias nao explode nem reordena", () => {
    expect(ordenarComoATabela([null, null], true)).toEqual([null, null]);
    expect(ausenciaNoFim(null, null, true)).toBe(0);
    expect(ausenciaNoFim(null, null, false)).toBe(0);
  });

  it("lista sem ausencia nenhuma se comporta como um comparador comum", () => {
    expect(ordenarComoATabela([3, 1, 2], false)).toEqual([1, 2, 3]);
    expect(ordenarComoATabela([3, 1, 2], true)).toEqual([3, 2, 1]);
  });

  it("o zero e um VALOR, e nao pode ser confundido com ausencia", () => {
    // Invariante 2 do projeto pela outra ponta: nota 0 e o pior atendimento
    // possivel, e tem de aparecer no topo do descendente-invertido, nunca no
    // fim junto com quem nao tem nota.
    expect(ordenarComoATabela([5, 0, null], false)).toEqual([0, 5, null]);
    expect(ordenarComoATabela([5, 0, null], true)).toEqual([5, 0, null]);
  });
});
