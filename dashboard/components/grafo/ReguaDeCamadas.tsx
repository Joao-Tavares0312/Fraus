"use client";

import type { Camada, MetaDoGrafo } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * A REGUA: escolhe qual camada fica em foco, e declara o corte do lexico.
 *
 * Ela nao filtra o grafo -- quem apaga e o canvas, e apagar e diferente de
 * remover (ver `GrafoDaMemoria`). Por isso o controle e um foco, nao um
 * filtro: "todas" continua sendo um estado valido e e o inicial.
 *
 * O aviso de truncamento fica AQUI, visivel, e nao no aparato: um grafo que
 * mostra 120 de 3.000 termos e um grafo parcial, e parcialidade nao e nota de
 * editor -- e a legenda do que se esta olhando.
 */
const ROTULO: Record<Camada, string> = {
  lexico: "Léxico",
  dominio: "Domínio",
  proveniencia: "Proveniência",
};

/** O que cada camada guarda, para quem chegou na tela sem ler a spec. */
const DESCRICAO: Record<Camada, string> = {
  lexico: "termos e emojis que apareceram na fala",
  dominio: "conversas, categorias, canais e desfechos",
  proveniencia: "de onde o dado veio — fontes e importações",
};

export function ReguaDeCamadas({
  camadas,
  foco,
  aoFocar,
  meta,
}: {
  camadas: Camada[];
  foco: Camada | "todas";
  aoFocar: (foco: Camada | "todas") => void;
  meta: MetaDoGrafo;
}) {
  const opcoes: Array<{ valor: Camada | "todas"; rotulo: string; titulo?: string }> = [
    { valor: "todas", rotulo: "Todas" },
    ...camadas.map((camada) => ({
      valor: camada,
      rotulo: ROTULO[camada],
      titulo: DESCRICAO[camada],
    })),
  ];

  return (
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
      <div
        role="group"
        aria-label="Camada em foco"
        className="flex flex-wrap items-center gap-1"
      >
        {opcoes.map((opcao) => {
          const ativa = foco === opcao.valor;
          return (
            <button
              key={opcao.valor}
              type="button"
              title={opcao.titulo}
              aria-pressed={ativa}
              onClick={() => aoFocar(opcao.valor)}
              className={cn(
                "border px-3 py-1.5 font-mono text-[0.6875rem] tracking-[0.1em] whitespace-nowrap uppercase transition-colors duration-150 ease-fluid",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                ativa
                  ? "border-primary bg-primary/10 font-medium text-foreground"
                  : "border-linha text-muted-foreground hover:border-primary hover:text-foreground",
              )}
            >
              {opcao.rotulo}
            </button>
          );
        })}
      </div>

      <p className="num text-xs text-muted-foreground">
        {meta.termos_exibidos} de {meta.termos_totais} termos
        {meta.truncado ? (
          <span className="ml-2 font-sans text-warning-rich-text">
            grafo truncado
          </span>
        ) : null}
      </p>
    </div>
  );
}
