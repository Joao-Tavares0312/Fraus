import type { ReactNode } from "react";
import { cn } from "../../lib/utils";

/**
 * A FAIXA DE TELEMETRIA: 34px no topo de cada tela, mono em caixa alta.
 *
 * E a assinatura da Regua -- a linha de estado de um instrumento de bancada --
 * e ela carrega so FATOS verdadeiros do produto ("NPS ESTIMATIVA", "LLM 00"),
 * nunca metrica inventada. O dourado marca VALOR (o `00`, o nome da tela); o
 * resto e `muted`. Dourado aqui e marca, nao dado (DESIGN.md 3.3).
 *
 * TAMANHO: 11px, nao os 9,5px do mockup. `lib/tipografia.test.ts` fixa o piso de
 * texto em 11px porque a banca le a interface num projetor, e o piso nao se
 * afrouxa por estetica.
 *
 * Sem estado e sem hook: serve em Server Component. Quem sabe a rota e
 * `TelemetriaDaRota`.
 */
export function TelemetriaTopo({
  esquerda,
  direita,
  className,
}: {
  esquerda: ReactNode;
  direita?: ReactNode;
  className?: string;
}) {
  return (
    <div
      data-slot="telemetria"
      className={cn(
        "sem-impressao flex h-[34px] items-center justify-between gap-4 border-b border-linha bg-background px-4 font-mono text-[0.6875rem] tracking-[0.14em] whitespace-nowrap text-muted-foreground uppercase sm:px-6",
        className,
      )}
    >
      <span className="min-w-0 truncate">{esquerda}</span>
      {direita ? <span className="hidden shrink-0 sm:block">{direita}</span> : null}
    </div>
  );
}

/** Um valor destacado dentro da telemetria: dourado, peso medio. */
export function TelemetriaValor({ children }: { children: ReactNode }) {
  return <b className="font-medium text-primary">{children}</b>;
}
