import type { ReactNode } from "react";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { FiltroPeriodo } from "./FiltroPeriodo";
import { rotuloPeriodo, type Extensao, type Periodo } from "@/lib/periodo";

/**
 * Cabecalho de secao.
 *
 * Fica `sticky` porque o filtro de periodo governa tudo que esta abaixo: se
 * ele sai de vista ao rolar, o numero na tela perde a legenda que diz de que
 * recorte ele fala.
 *
 * `periodo` e opcional: a tela Modelo descreve o MODELO, nao um recorte de
 * atendimentos, e mostrar um filtro que nao afeta nada seria a mesma promessa
 * vazia que este trabalho veio corrigir.
 */
export function CabecalhoPagina({
  titulo,
  subtitulo,
  periodo,
  extensao,
  acoes,
}: {
  titulo: string;
  subtitulo: string;
  periodo?: Periodo;
  extensao?: Extensao;
  acoes?: ReactNode;
}) {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="flex flex-col gap-3 px-4 py-3 sm:px-6">
        <div className="flex flex-wrap items-start gap-x-3 gap-y-2">
          <SidebarTrigger className="sem-impressao -ml-1 mt-0.5 shrink-0" />
          <div className="min-w-0 flex-1">
            <h1 className="text-lg leading-tight font-semibold tracking-tight text-foreground">
              {titulo}
            </h1>
            <p className="mt-0.5 max-w-[80ch] text-sm leading-relaxed text-muted-foreground">
              {subtitulo}
            </p>
          </div>
          {acoes ? (
            <div className="sem-impressao flex shrink-0 gap-2">{acoes}</div>
          ) : null}
        </div>

        {periodo ? (
          <>
            {/* A regua fraca do sistema (--compasso), nao o separador cheio:
                titulo e filtro sao o MESMO bloco de contexto, e a divisoria
                forte os apresentava como secoes independentes. */}
            <div aria-hidden className="h-px bg-compasso" />
            <div className="sem-impressao flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
              <FiltroPeriodo periodo={periodo} extensao={extensao ?? null} />
              <p className="text-xs text-muted-foreground">
                Tudo nesta tela — indicadores, série, tabela e export — fala de{" "}
                <strong className="font-medium text-foreground">
                  {rotuloPeriodo(periodo, extensao ?? null)}
                </strong>
                .
              </p>
            </div>
          </>
        ) : null}
      </div>
    </header>
  );
}
