import type { ReactNode } from "react";

/**
 * Casca unica de painel: filete de 1px, sem sombra, sem raio grande.
 * Existe para que toda a superficie use a MESMA moldura -- consistencia vale
 * mais que variedade numa tela de operacao.
 */
export function Painel({
  titulo,
  legenda,
  acessorio,
  children,
  className = "",
}: {
  titulo: string;
  legenda?: ReactNode;
  acessorio?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`quebra-evitar border border-[var(--filete)] bg-[var(--superficie)] ${className}`}
    >
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--filete)] px-5 py-3.5">
        <div className="min-w-0">
          <h2 className="text-[0.9375rem] font-semibold tracking-[-0.01em] text-[var(--tinta)]">
            {titulo}
          </h2>
          {legenda ? (
            <p className="mt-1 max-w-[68ch] text-[0.8125rem] leading-[1.45] text-[var(--tinta-2)]">
              {legenda}
            </p>
          ) : null}
        </div>
        {acessorio ? <div className="shrink-0">{acessorio}</div> : null}
      </header>
      {children}
    </section>
  );
}

/** Rotulo de secao/eixo: pequeno, discreto, sem caixa alta decorativa. */
export function Rotulo({ children }: { children: ReactNode }) {
  return (
    <span className="text-[0.6875rem] font-medium text-[var(--tinta-3)]">
      {children}
    </span>
  );
}
