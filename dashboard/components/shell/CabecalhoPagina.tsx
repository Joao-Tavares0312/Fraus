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
  escopo = "indicadores, série, tabela e export",
}: {
  titulo: string;
  /** Opcional: tela cuja tarefa e obvia pelo titulo nao paga um paragrafo. */
  subtitulo?: string;
  periodo?: Periodo;
  extensao?: Extensao;
  acoes?: ReactNode;
  /**
   * O QUE nesta tela obedece ao periodo, em uma frase curta. O padrao descreve
   * a Visao geral; toda tela cujo conteudo e outro (o Grafo tem nos e arestas,
   * nao serie nem export) passa o seu -- dizer "serie" onde nao ha serie e o
   * tipo de promessa vazia que este cabecalho veio evitar.
   */
  escopo?: string;
}) {
  return (
    // `top-[34px]`: cola logo abaixo da faixa de telemetria (34px, sticky no
    // topo em `TelemetriaDaRota`), e nao sobre ela.
    <header className="vidro-fino vidro-faixa sticky top-[34px] z-20">
      <div className="flex flex-col gap-3 px-4 py-3 sm:px-6">
        <div className="flex flex-wrap items-start gap-x-3 gap-y-2">
          <SidebarTrigger className="sem-impressao -ml-1 mt-0.5 shrink-0" />
          {/* `basis-64`: sem base, o titulo encolhia sem limite e as acoes
              nunca desciam de linha -- a 390px o subtitulo virava uma coluna
              de uma ou duas palavras ao lado de "Todos os atendimentos". Com
              base, quando os dois nao cabem, as acoes quebram para baixo. */}
          <div className="min-w-0 flex-1 basis-64">
            <h1 className="titulo-instrumento text-lg leading-tight text-foreground">
              {titulo}
            </h1>
            {subtitulo ? (
              <p className="mt-0.5 max-w-[80ch] text-sm leading-relaxed text-muted-foreground">
                {subtitulo}
              </p>
            ) : null}
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
                Tudo nesta tela — {escopo} — fala de{" "}
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
