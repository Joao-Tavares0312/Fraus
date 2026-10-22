"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  formatarDia,
  somarDias,
  type Extensao,
  type Periodo,
} from "@/lib/periodo";

/**
 * Filtro de periodo GLOBAL.
 *
 * O recorte vai para a URL (`?de=&ate=`) e todas as telas leem dali, entao
 * indicador, serie, tabela e export nunca discordam entre si.
 *
 * Os ATALHOS sao ancorados no ULTIMO DIA COM DADO, nao em `hoje`. Ancorar em
 * hoje pareceria mais natural e seria pior: o conjunto pode terminar antes ou
 * depois de hoje, e "ultimos 7 dias" devolveria vazio sem explicar por que.
 * Os atalhos mantem o intervalo aplicado na URL; o cabecalho mostra suas
 * datas com o rotulo canonico. A extensao sempre vem do conjunto completo,
 * mesmo quando o recorte atual esta vazio.
 */
export function FiltroPeriodo({
  periodo,
  extensao,
}: {
  periodo: Periodo;
  extensao: Extensao;
}) {
  const router = useRouter();
  const parametros = useSearchParams();
  const [pendente, iniciar] = useTransition();

  const aplicar = (proximo: Periodo) => {
    if (pendente) return;

    const consulta = new URLSearchParams(parametros.toString());
    for (const [chave, valor] of [
      ["de", proximo.de],
      ["ate", proximo.ate],
    ] as const) {
      if (valor) consulta.set(chave, valor);
      else consulta.delete(chave);
    }
    const texto = consulta.toString();
    iniciar(() => router.replace(texto ? `?${texto}` : "?", { scroll: false }));
  };

  const atalhos = [7, 30].map((dias) => ({
    dias,
    de: extensao ? somarDias(extensao.ultimo, -(dias - 1)) : null,
    ate: extensao?.ultimo ?? null,
  }));

  const ativo = periodo.de !== null || periodo.ate !== null;

  return (
    <div
      className="flex min-w-0 max-w-full flex-col gap-2"
      data-pendente={pendente || undefined}
      aria-busy={pendente}
    >
      <div className="flex min-w-0 max-w-full flex-wrap items-center gap-x-3 gap-y-2">
      {/* Campos flexiveis mantem as duas datas na mesma linha no celular. */}
      <fieldset
        disabled={pendente}
        className="flex w-full min-w-0 flex-nowrap items-center gap-x-2 sm:w-auto sm:flex-wrap sm:gap-y-2"
      >
        <legend className="sr-only">Período dos atendimentos</legend>

        <Label
          htmlFor="periodo-de"
          className="text-sm font-normal text-muted-foreground"
        >
          De
        </Label>
        <input
          id="periodo-de"
          type="date"
          value={periodo.de ?? ""}
          data-vazio={periodo.de ? undefined : ""}
          min={extensao?.primeiro}
          max={extensao?.ultimo}
          onChange={(evento) =>
            aplicar({ ...periodo, de: evento.target.value || null })
          }
          className="campo-data min-w-0 flex-1 sm:flex-none"
        />

        <Label
          htmlFor="periodo-ate"
          className="ml-1 text-sm font-normal text-muted-foreground"
        >
          até
        </Label>
        <input
          id="periodo-ate"
          type="date"
          value={periodo.ate ?? ""}
          data-vazio={periodo.ate ? undefined : ""}
          min={extensao?.primeiro}
          max={extensao?.ultimo}
          onChange={(evento) =>
            aplicar({ ...periodo, ate: evento.target.value || null })
          }
          className="campo-data min-w-0 flex-1 sm:flex-none"
        />
      </fieldset>

      <div
        className="flex min-w-0 max-w-full flex-wrap items-center gap-1.5"
        role="group"
        aria-label="Atalhos de período"
      >
        {atalhos.map((atalho) => {
          const selecionado =
            atalho.de !== null &&
            periodo.de === atalho.de &&
            periodo.ate === atalho.ate;
          return (
            <Button
              key={atalho.dias}
              type="button"
              size="sm"
              className="min-h-9 px-2 text-xs"
              variant={selecionado ? "default" : "outline"}
              aria-pressed={selecionado}
              disabled={pendente || !extensao}
              title={
                atalho.de && atalho.ate
                  ? `${formatarDia(atalho.de)} – ${formatarDia(atalho.ate)}`
                  : "Disponível quando houver datas dos atendimentos."
              }
              onClick={() => {
                if (!atalho.de || !atalho.ate) return;
                aplicar({ de: atalho.de, ate: atalho.ate });
              }}
            >
              Últimos {atalho.dias} dias
            </Button>
          );
        })}

        <Button
          type="button"
          size="sm"
          className="min-h-9 px-2 text-xs"
          variant={!ativo ? "default" : "outline"}
          aria-pressed={!ativo}
          disabled={pendente}
          onClick={() => aplicar({ de: null, ate: null })}
        >
          Todo o período
        </Button>
      </div>
      </div>
      <p className="text-sm leading-snug text-muted-foreground">
        {extensao
          ? `Atalhos até ${formatarDia(extensao.ultimo)}, último dia com dados — não até hoje.`
          : "Atalhos indisponíveis sem datas dos atendimentos. Você pode retirar o filtro."}
      </p>
    </div>
  );
}
