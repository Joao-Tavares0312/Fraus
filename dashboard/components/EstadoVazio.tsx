import { CircleSlash } from "lucide-react";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { cn } from "@/lib/utils";

/**
 * Estado vazio HONESTO.
 *
 * Este componente e uma posicao de projeto, nao um placeholder: quando a API
 * nao expoe o dado, a dashboard diz o que falta e qual endpoint ou etapa
 * resolveria, em vez de renderizar um numero plausivel. Numa ferramenta cujo
 * nome vem do daemon do engano, inventar dado seria a pior falha possivel.
 *
 * Ele e tambem o modo de FALHA ISOLADA: um painel que nao carrega mostra o
 * proprio erro aqui dentro e os vizinhos continuam de pe.
 */
export function EstadoVazio({
  titulo,
  explicacao,
  endpoint,
  etapa,
  className,
}: {
  titulo: string;
  explicacao: string;
  /** Rota que passaria a devolver este dado, quando houver. */
  endpoint?: string;
  /** Etapa do projeto que falta rodar, quando o que falta nao e uma rota. */
  etapa?: string;
  className?: string;
}) {
  return (
    <Empty
      className={cn(
        "items-start border border-dashed border-border text-left",
        className,
      )}
    >
      <EmptyHeader className="max-w-[62ch] items-start text-left">
        <EmptyMedia variant="icon" className="mb-0">
          <CircleSlash aria-hidden />
        </EmptyMedia>
        <EmptyTitle className="text-sm text-foreground">{titulo}</EmptyTitle>
        <EmptyDescription className="text-xs">{explicacao}</EmptyDescription>
        {endpoint ? (
          <EmptyDescription className="text-xs">
            Resolvido por{" "}
            <code className="num rounded-sm bg-muted px-1 py-0.5 text-foreground">
              {endpoint}
            </code>
            .
          </EmptyDescription>
        ) : null}
        {etapa ? (
          <EmptyDescription className="text-xs">
            Falta rodar: <span className="text-foreground">{etapa}</span>.
          </EmptyDescription>
        ) : null}
      </EmptyHeader>
    </Empty>
  );
}
