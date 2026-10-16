import { cn } from "@/lib/utils";

/** Apresenta a string já formatada: ausência nunca vira zero ou medição. */
export function ValorNumerico({
  valor,
  rotulo,
  cor = "medido",
  className,
  ausencia = "Sem sinal",
}: {
  valor: string | null;
  rotulo: string;
  cor?: "medido" | "marca" | "tinta" | "erro";
  className?: string;
  ausencia?: string;
}) {
  return (
    <span
      aria-label={`${rotulo}: ${valor === null ? ausencia : valor}`}
      className={cn(
        "valor-numerico",
        valor === null ? "text-muted-foreground" : {
          medido: "text-medido-texto",
          marca: "text-primary",
          tinta: "text-foreground",
          erro: "text-destructive",
        }[cor],
        className,
      )}
    >
      {valor === null ? ausencia : valor}
    </span>
  );
}
