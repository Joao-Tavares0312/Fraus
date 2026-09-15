import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { ResumoConversa } from "@/lib/api";
import { DEFINICAO_SEM_SINAL_AGREGADO, formatarDataHora } from "@/lib/formato";
import { EstadoVazio } from "./EstadoVazio";
import { EtiquetaCategoria } from "./EtiquetaCategoria";

/**
 * Os atendimentos com a menor nota inferida no periodo.
 *
 * Conversa sem nota NAO aparece aqui e nao e contada como "pior": ordenar os
 * mudos para o topo seria o `?? 0` que o produto combate. Elas continuam
 * visiveis na tabela de Atendimentos, marcadas como "sem sinal".
 *
 * O link preserva o periodo para que voltar nao perca o recorte.
 */
export function PioresAtendimentos({
  piores,
  semSinal,
  sufixoDeQuery,
}: {
  piores: ResumoConversa[];
  semSinal: number;
  sufixoDeQuery: string;
}) {
  if (piores.length === 0) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="Nenhum atendimento pontuado no período"
        explicacao={
          semSinal > 0
            ? `Os ${semSinal} atendimento(s) do período estão sem sinal — ${DEFINICAO_SEM_SINAL_AGREGADO}. Sem nota, não há "pior" a apontar — e chamar de pior quem não disse nada avaliável seria inventar o veredito.`
            : "Nenhum atendimento sobrou no recorte de período atual."
        }
      />
    );
  }

  return (
    <ul className="divide-y divide-border">
      {piores.map((conversa) => (
        <li key={conversa.id}>
          <Link
            href={`/dashboard/atendimentos/${encodeURIComponent(conversa.id)}${sufixoDeQuery}`}
            className="flex items-center gap-3 px-5 py-2.5 outline-none transition-colors duration-150 ease-fluid hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
          >
            <span className="num w-8 shrink-0 text-lg font-semibold text-foreground">
              {conversa.nota}
            </span>
            <span className="min-w-0 flex-1">
              <span className="num block truncate text-xs text-foreground">
                {conversa.id}
              </span>
              <span className="block truncate text-xs text-muted-foreground">
                {conversa.canal} · {formatarDataHora(conversa.iniciada_em)}
              </span>
            </span>
            <EtiquetaCategoria
              categoria={conversa.categoria}
              className="shrink-0 text-xs"
            />
            <ChevronRight
              aria-hidden
              className="size-4 shrink-0 text-muted-foreground"
            />
          </Link>
        </li>
      ))}
    </ul>
  );
}
