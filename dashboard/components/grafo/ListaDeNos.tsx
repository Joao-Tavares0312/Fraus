"use client";

import type { NoDoGrafo } from "@/lib/api";

/**
 * Os nos em forma de LISTA -- o caminho de quem nao ve o canvas.
 *
 * O canvas e opaco para leitor de tela: ele e um bitmap, e nenhuma tecnologia
 * assistiva enxerga o que foi pintado nele. Sem esta lista a tela inteira
 * seria inacessivel por construcao, e este e um trabalho academico que sera
 * apresentado -- "a visualizacao nao e navegavel por teclado" e pergunta de
 * banca, nao detalhe.
 *
 * Ela nao e um consolo: seleciona o MESMO no que o clique no canvas
 * selecionaria, abrindo a mesma ficha (Task 8).
 */
export function ListaDeNos({
  nos,
  aoSelecionar,
}: {
  nos: NoDoGrafo[];
  aoSelecionar?: (no: NoDoGrafo) => void;
}) {
  return (
    <ul className="flex flex-col gap-1">
      {nos.map((no) => (
        <li key={no.id}>
          <button
            type="button"
            onClick={() => aoSelecionar?.(no)}
            className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-sm text-foreground transition-colors duration-150 ease-fluid hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span className="min-w-0 truncate">{no.rotulo}</span>
            <span className="num shrink-0 text-xs text-muted-foreground">
              {no.tipo}, {no.grau} conexões
              {no.sem_sinal ? ", sem sinal" : ""}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
