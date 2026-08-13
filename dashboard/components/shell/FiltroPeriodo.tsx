"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition } from "react";
import { CalendarRange, X } from "lucide-react";
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
 * Cada atalho mostra o intervalo real que aplica -- nada de rotulo relativo
 * escondendo qual recorte foi feito.
 *
 * A API nao aceita filtro de data em rota nenhuma, entao o corte acontece no
 * cliente sobre `iniciada_em`; um `GET /conversas?de=&ate=` resolveria.
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

  const atalhos = extensao
    ? [
        {
          rotulo: "7 dias",
          de: somarDias(extensao.ultimo, -6),
          ate: extensao.ultimo,
        },
        {
          rotulo: "14 dias",
          de: somarDias(extensao.ultimo, -13),
          ate: extensao.ultimo,
        },
        {
          rotulo: "30 dias",
          de: somarDias(extensao.ultimo, -29),
          ate: extensao.ultimo,
        },
      ]
    : [];

  const ativo = periodo.de !== null || periodo.ate !== null;

  return (
    <div
      className="flex flex-wrap items-end gap-x-3 gap-y-2"
      data-pendente={pendente || undefined}
    >
      <fieldset className="flex flex-wrap items-end gap-3">
        <legend className="sr-only">Período dos atendimentos</legend>

        <div className="flex flex-col gap-1">
          <Label
            htmlFor="periodo-de"
            className="text-xs font-normal text-muted-foreground"
          >
            De
          </Label>
          <input
            id="periodo-de"
            type="date"
            value={periodo.de ?? ""}
            min={extensao?.primeiro}
            max={extensao?.ultimo}
            onChange={(evento) =>
              aplicar({ ...periodo, de: evento.target.value || null })
            }
            className="num h-9 min-h-11 rounded-md border border-input bg-card px-2.5 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring sm:min-h-9"
          />
        </div>

        <div className="flex flex-col gap-1">
          <Label
            htmlFor="periodo-ate"
            className="text-xs font-normal text-muted-foreground"
          >
            Até
          </Label>
          <input
            id="periodo-ate"
            type="date"
            value={periodo.ate ?? ""}
            min={extensao?.primeiro}
            max={extensao?.ultimo}
            onChange={(evento) =>
              aplicar({ ...periodo, ate: evento.target.value || null })
            }
            className="num h-9 min-h-11 rounded-md border border-input bg-card px-2.5 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring sm:min-h-9"
          />
        </div>
      </fieldset>

      <div className="flex flex-wrap items-center gap-1.5">
        {atalhos.map((atalho) => {
          const selecionado =
            periodo.de === atalho.de && periodo.ate === atalho.ate;
          return (
            <Button
              key={atalho.rotulo}
              type="button"
              size="sm"
              variant={selecionado ? "default" : "outline"}
              aria-pressed={selecionado}
              title={`${formatarDia(atalho.de)} – ${formatarDia(atalho.ate)}`}
              onClick={() => aplicar({ de: atalho.de, ate: atalho.ate })}
            >
              <CalendarRange aria-hidden />
              {atalho.rotulo}
            </Button>
          );
        })}

        {ativo ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => aplicar({ de: null, ate: null })}
          >
            <X aria-hidden />
            Limpar
          </Button>
        ) : null}
      </div>
    </div>
  );
}
