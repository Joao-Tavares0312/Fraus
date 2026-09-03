/**
 * Ordenacao que manda AUSENCIA para o fim NOS DOIS SENTIDOS.
 *
 * A regra de produto, escrita na propria tela de Atendimentos: "ordenar por
 * nota ou por espera manda a ausencia para o fim nos dois sentidos --
 * atendimento sem fala do cliente nao e o pior atendimento, e conversa que
 * nunca teve resposta humana nao e a mais rapida da operacao". E a invariante 2
 * do projeto aplicada a ordenacao: ausencia de dado nao e um valor ruim, e a
 * falta de um valor.
 *
 * POR QUE O SENTIDO PRECISA CHEGAR AQUI. O comparador antigo devolvia sempre
 * `+1` para o nulo e resolvia o caso crescente. So que o motor do TanStack
 * inverte o comparador INTEIRO no descendente:
 *
 *     if (isDesc) sortInt *= -1
 *     // @tanstack/table-core/dist/features/row-sorting/createSortedRowModel.js
 *
 * ...e o sentinela ia junto. O resultado e que "sem sinal" subia para o TOPO
 * exatamente no descendente -- que e o PRIMEIRO clique da coluna de nota, o
 * clique de quem esta procurando os piores atendimentos. A tela prometia por
 * escrito o contrario do que fazia.
 *
 * Invertendo o sentinela de antemao, a multiplicacao do motor o traz de volta
 * ao lugar certo. A comparacao entre dois valores presentes segue intacta e
 * continua sendo invertida normalmente -- e so a ausencia que fica imune.
 *
 * (A biblioteca tem `sortUndefined: "last"`, que retorna antes da inversao e
 * resolveria isto sozinho. Ele testa `=== undefined`, e a ausencia neste
 * projeto e `null` em todo lugar -- do payload da API a celula. Trocar o
 * significado de nulo na tabela inteira para agradar uma opcao de ordenacao
 * seria pagar caro no lugar errado.)
 */
export function ausenciaNoFim(
  a: number | null,
  b: number | null,
  descendente: boolean,
): number {
  if (a === null && b === null) return 0;
  if (a === null) return descendente ? -1 : 1;
  if (b === null) return descendente ? 1 : -1;
  return a - b;
}
