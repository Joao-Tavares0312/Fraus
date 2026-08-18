"use client";

import { ENDERECO_API } from "@/lib/api";
import { useSaude, type EstadoDeSaude as Estado } from "./SaudeProvider";

const APARENCIA: Record<
  Estado,
  { rotulo: string; cor: string; detalhe: string }
> = {
  verificando: {
    rotulo: "verificando…",
    cor: "bg-muted-foreground",
    detalhe: "consultando GET /saude",
  },
  "no-ar": {
    rotulo: "API no ar",
    cor: "bg-success",
    detalhe: "GET /saude respondeu ok",
  },
  "fora-do-ar": {
    rotulo: "API fora do ar",
    cor: "bg-destructive",
    detalhe: "GET /saude não respondeu",
  },
};

/**
 * Estado de saude da API, sempre visivel no rodape da navegacao.
 *
 * Existe porque a API real do Fraus NAO sobe sem modelo treinado (invariante
 * 7): a tela em branco tem duas causas possiveis -- banco vazio ou servidor
 * fora -- e sem este indicador quem esta na frente do produto nao sabe qual.
 *
 * Cor nao e o unico canal: o rotulo textual diz o estado, e o `title` diz qual
 * endereco foi consultado.
 *
 * O POLLING nao mora mais aqui: ele vive no `SaudeProvider`, porque o aviso de
 * "API fora do ar" mostra o mesmo fato e dois pollings independentes
 * discordariam por ate 20 segundos -- este rodape dizendo "API no ar" com o
 * aviso ainda na tela.
 */
export function EstadoSaude() {
  const { estado } = useSaude();

  const { rotulo, cor, detalhe } = APARENCIA[estado];

  return (
    <div
      className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-muted-foreground"
      title={`${detalhe} — ${ENDERECO_API}`}
    >
      <span
        aria-hidden
        className={`size-2 shrink-0 rounded-full ${cor}`}
      />
      <span
        role="status"
        className="truncate group-data-[collapsible=icon]:hidden"
      >
        {rotulo}
      </span>
      <span className="sr-only">{`${rotulo}. ${detalhe}.`}</span>
    </div>
  );
}
