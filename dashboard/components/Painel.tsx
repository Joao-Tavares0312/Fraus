import type { ReactNode } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * Painel de conteudo: titulo, subtitulo com o metodo quando o numero e
 * derivado, corpo e rodape opcional.
 *
 * Elevacao por BORDA e superficie, nunca por sombra difusa -- o `Card` do
 * chassi ja e assim. O subtitulo nao e decoracao: quando o numero do painel foi
 * derivado no cliente e nao lido de um endpoint, e nele que isso esta escrito.
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
  legenda?: ReactNode;
  acessorio?: ReactNode;
  rodape?: ReactNode;
  /** Para tabela e grafico, que gerenciam o proprio respiro. */
  semPadding?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Card className={cn("quebra-evitar gap-0 overflow-hidden py-0", className)}>
      <CardHeader className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-b border-border px-5 py-4">
        <div className="min-w-0 flex-1">
          <CardTitle className="text-sm font-semibold tracking-tight">
            {titulo}
          </CardTitle>
          {legenda ? (
            <CardDescription className="mt-1 max-w-[80ch] text-xs leading-relaxed">
              {legenda}
            </CardDescription>
          ) : null}
        </div>
        {acessorio ? <div className="shrink-0">{acessorio}</div> : null}
      </CardHeader>

      <CardContent className={cn("min-w-0", semPadding ? "p-0" : "p-5")}>
        {children}
      </CardContent>

      {rodape ? (
        <div className="border-t border-border px-5 py-3 text-xs leading-relaxed text-muted-foreground">
          {rodape}
        </div>
      ) : null}
    </Card>
  );
}
