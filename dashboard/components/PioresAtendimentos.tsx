import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { ResumoConversa } from "@/lib/api";
import { DEFINICAO_SEM_SINAL_AGREGADO, formatarDataHora } from "@/lib/formato";
import { EstadoVazio } from "./EstadoVazio";
import { EtiquetaCategoria } from "./EtiquetaCategoria";
import { NotaLED } from "./NotaLED";

/**
 * Os atendimentos com a menor nota inferida no periodo.
 *
 * Conversa sem nota NAO aparece aqui e nao e contada como "pior": ordenar os
 * mudos para o topo seria o `?? 0` que o produto combate. Elas continuam
 * visiveis na tabela de Atendimentos, marcadas como "sem sinal".
 *
 * A NOTA E LED, e a cabeca vem do slot unico (`EtiquetaCategoria`) COM o motivo
 * da evidencia fraca impresso: um "detrator" sustentado por uma unica fala do
 * cliente nao pode parecer tao firme quanto um de quarenta turnos, e "evidencia
 * fraca" solto nao aciona ninguem -- "uma unica mensagem do cliente" aciona.
 * `evidencia_fraca` e `motivos_evidencia_fraca` vem do servidor (a regra mora em
 * `fraus/evidencia.py`); aqui so se desenha.
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
    <ul className="divide-y divide-compasso">
      {piores.map((conversa) => (
        <li key={conversa.id}>
          <Link
            href={`/dashboard/atendimentos/${encodeURIComponent(conversa.id)}${sufixoDeQuery}`}
            className="group grid grid-cols-[3.25rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-4 py-3 outline-none transition-colors duration-150 ease-fluid hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset sm:px-5"
          >
            {/* Duas celulas fixas: a coluna de LED nao dança entre 9 e 10. */}
            <NotaLED nota={conversa.nota} altura={26} />
            <span className="min-w-0">
              <span className="num block truncate text-xs text-foreground">
                {conversa.id}
              </span>
              <span className="block truncate text-xs text-muted-foreground">
                {conversa.canal} · {formatarDataHora(conversa.iniciada_em)}
              </span>
            </span>
            <ChevronRight
              aria-hidden
              className="size-4 shrink-0 text-muted-foreground transition-transform duration-150 group-hover:translate-x-0.5"
            />
            {/* O rotulo (e o motivo) desce para a linha de baixo: ao lado do LED
                ele empurraria o id para fora da coluna em telas estreitas. */}
            <EtiquetaCategoria
              categoria={conversa.categoria}
              evidenciaFraca={conversa.evidencia_fraca}
              motivosEvidencia={conversa.motivos_evidencia_fraca}
              className="col-start-2 col-end-4 min-w-0 flex-wrap text-xs whitespace-normal"
            />
          </Link>
        </li>
      ))}
    </ul>
  );
}
