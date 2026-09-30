"use client";

import { usePathname } from "next/navigation";
import { rotuloNumerado, telaDoCaminho } from "../../lib/navegacao";
import { TelemetriaTopo, TelemetriaValor } from "./TelemetriaTopo";

/**
 * A telemetria da ferramenta: "FRAUS / 01_VISAO GERAL" a esquerda, o regime do
 * produto a direita. Montada UMA vez no shell (`app/dashboard/layout.tsx`).
 *
 * A direita diz duas coisas que sao verdade do produto inteiro, e por isso
 * cabem numa faixa que nao muda de tela: o NPS e ESTIMATIVA (inferido do texto,
 * nunca perguntado ao cliente) e nao ha LLM em runtime (invariante 1).
 *
 * Sticky no topo: o cabecalho de pagina (`CabecalhoPagina`) cola logo abaixo
 * dela, em `top-[34px]`.
 */
export function TelemetriaDaRota() {
  const tela = telaDoCaminho(usePathname());

  return (
    <TelemetriaTopo
      className="sticky top-0 z-30"
      esquerda={
        <>
          FRAUS / <TelemetriaValor>{tela ? rotuloNumerado(tela) : "—"}</TelemetriaValor>
        </>
      }
      direita={
        <>
          NPS <TelemetriaValor>ESTIMATIVA</TelemetriaValor> · LLM{" "}
          <TelemetriaValor>00</TelemetriaValor>
        </>
      }
    />
  );
}
