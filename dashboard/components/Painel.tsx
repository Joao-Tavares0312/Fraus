"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { useEspecular } from "@/hooks/useEspecular";

/**
 * O SISTEMA: a unidade de composicao da interface.
 *
 * Como numa partitura, um sistema e uma faixa de largura total que carrega uma
 * linha e tudo que a anota. A pagina e uma PILHA DE SISTEMAS, nao uma grade de
 * cartoes -- o cartao com borda e fundo proprio deixou de ser o agrupador
 * padrao, e quem agrupa agora e espaco mais regua. Ver DESIGN.md, secao 2.
 *
 * A MUDANCA QUE IMPORTA e a posicao da prosa. Antes, a legenda metodologica
 * ficava no cabecalho, ACIMA do conteudo: somando os paineis, isso empurrava o
 * grafico que carrega a tese da tela para 560px abaixo do topo. Nenhuma
 * explicacao foi removida -- ela virou APARATO, no rodape do sistema e na
 * tipografia menor, que e onde a partitura poe nota de editor.
 *
 * Recolher e permitido; remover nao. O aparato abre com um gesto, e os rotulos
 * curtos que qualificam o numero (`estimativa`, `observado`, `sem sinal`) NAO
 * sao aparato: ficam colados ao dado, sempre visiveis.
 */
export function Painel({
  titulo,
  legenda,
  acessorio,
  rodape,
  semPadding,
  className,
  children,
}: {
  titulo: string;
  /** Metodo e ressalvas. Vai para o aparato, nunca acima do dado. */
  legenda?: ReactNode;
  acessorio?: ReactNode;
  rodape?: ReactNode;
  /** Para tabela e grafico, que gerenciam o proprio respiro. */
  semPadding?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const temAparato = Boolean(legenda || rodape);
  const refEspecular = useEspecular<HTMLElement>();

  return (
    <section
      ref={refEspecular}
      className={cn(
        "vidro especular quebra-evitar min-w-0 rounded-lg p-4 sm:p-5",
        className,
      )}
    >
      {/* A regua do sistema. Mais espaco acima do titulo do que abaixo. */}
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-linha pb-2">
        <h2 className="text-sm font-semibold tracking-tight text-foreground">
          {titulo}
        </h2>
        {acessorio ? <div className="shrink-0">{acessorio}</div> : null}
      </header>

      <div
        className={cn(
          "min-w-0",
          semPadding ? "-mx-4 pt-3 sm:-mx-5" : "pt-4",
        )}
      >
        {children}
      </div>

      {temAparato ? (
        <details className="group mt-3 border-t border-compasso pt-2">
          <summary className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-sm text-xs text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring">
            <span
              aria-hidden
              className="inline-block transition-transform duration-200 group-open:rotate-90"
            >
              ›
            </span>
            Método e ressalvas
          </summary>
          <div className="mt-2 max-w-[72ch] space-y-2 text-xs leading-relaxed text-muted-foreground">
            {legenda}
            {rodape}
          </div>
        </details>
      ) : null}
    </section>
  );
}
