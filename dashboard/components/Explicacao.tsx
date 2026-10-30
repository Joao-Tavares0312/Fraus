"use client";

import type { ReactNode } from "react";
import { Popover } from "@base-ui/react/popover";
import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * O ⓘ: a explicacao recolhida ao lado do rotulo.
 *
 * KISS (30/10/2026): o texto de honestidade NAO sai da tela -- sai da frente
 * do dado. A etiqueta curta ("estimativa", "sem sinal") continua colada ao
 * numero; o porque mora aqui, a um clique. Popover e nao tooltip: tooltip nao
 * abre no toque, e a explicacao precisa existir no celular tambem.
 */
export function Explicacao({
  rotulo,
  children,
  className,
}: {
  /** Nome acessivel do botao: "Sobre o NPS inferido". */
  rotulo: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Popover.Root>
      <Popover.Trigger
        openOnHover
        delay={150}
        aria-label={rotulo}
        // Dentro de linha clicavel (tabela de atendimentos), abrir o ⓘ nao
        // pode navegar.
        onClick={(evento) => evento.stopPropagation()}
        className={cn(
          "inline-flex size-5 shrink-0 cursor-help items-center justify-center rounded-full align-middle text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring data-[popup-open]:text-foreground",
          className,
        )}
      >
        <Info aria-hidden className="size-3.5" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner side="top" sideOffset={6} className="isolate z-50">
          <Popover.Popup className="superficie-flutuante max-w-xs px-3 py-2 text-xs leading-relaxed text-muted-foreground outline-none [&_strong]:font-medium [&_strong]:text-foreground">
            {children}
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
