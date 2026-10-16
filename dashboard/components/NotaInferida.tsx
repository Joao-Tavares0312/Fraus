import { ValorNumerico } from "./ValorNumerico";
import { cn } from "@/lib/utils";

/** Nota inteira recebida do servidor; zero é nota, null é ausência. */
export function NotaInferida({ nota, rotulo = "nota inferida, estimativa", className }: {
  nota: number | null;
  rotulo?: string;
  className?: string;
}) {
  return <ValorNumerico valor={nota === null ? null : String(nota)} rotulo={rotulo} className={cn("text-xl", className)} />;
}
