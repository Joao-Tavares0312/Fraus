"use client";

import type { TipoDeNo } from "@/lib/api";
import { ROTULO_TIPO } from "./FichaDoNo";
import { TIPOS_NA_LEGENDA, eDito } from "./desenho";

/**
 * A LEGENDA: o que cada cor do canvas quer dizer.
 *
 * Ela existe porque a cor passou a codificar TIPO, e cor sem legenda e
 * adivinhacao: antes eram duas vozes que o resto da dashboard ja ensina
 * (ambar/azul aparecem em toda tela), agora sao nove matizes que so existem
 * aqui. Pintar nove cores e nao dizer o que sao seria o grafo afirmando uma
 * distincao que o leitor nao tem como ler -- o mesmo silencio que a regra do
 * projeto proibe.
 *
 * Ela mostra SO os tipos presentes no grafo em tela. Uma legenda fixa de nove
 * itens anunciaria `importacao` e `desfecho` num banco que nao tem nenhum dos
 * dois, mandando procurar no canvas uma cor que nao foi pintada.
 *
 * O agrupamento em duas colunas nao e diagramacao: ele e a familia. Quente e o
 * que foi DITO, frio e o que foi MEDIDO -- a regra antiga do DESIGN.md, agora
 * legivel na propria legenda em vez de so no codigo.
 */
export function LegendaDeCores({ tipos }: { tipos: Set<TipoDeNo> }) {
  const presentes = TIPOS_NA_LEGENDA.filter((tipo) => tipos.has(tipo));
  if (presentes.length === 0) return null;

  const ditos = presentes.filter(eDito);
  const medidos = presentes.filter((tipo) => !eDito(tipo));

  return (
    <div className="flex flex-wrap items-start gap-x-6 gap-y-2 text-[11px] text-muted-foreground">
      {ditos.length > 0 ? <Familia titulo="dito" tipos={ditos} /> : null}
      {medidos.length > 0 ? <Familia titulo="medido" tipos={medidos} /> : null}
    </div>
  );
}

function Familia({ titulo, tipos }: { titulo: string; tipos: TipoDeNo[] }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <span
        className={`font-mono tracking-[0.14em] uppercase ${titulo === "dito" ? "text-dito-texto" : "text-medido-texto"}`}
      >
        {titulo}
      </span>
      {tipos.map((tipo) => (
        <span key={tipo} className="flex items-center gap-1.5">
          {/*
            `aria-hidden` no ponto e o nome ao lado em texto: quem nao enxerga
            a cor le a palavra, e quem enxerga usa os dois. Cor nunca e o unico
            canal (DESIGN.md).

            O estilo e inline, e nao classe utilitaria, porque o nome do token
            vem de um `Record` em tempo de execucao -- uma classe montada por
            template string (`bg-no-${tipo}`) nao existe no CSS gerado: o
            Tailwind so inclui o que consegue ler estaticamente no fonte, e a
            legenda sairia com nove pontos invisiveis.
          */}
          <span
            aria-hidden
            className="size-2 shrink-0 rounded-full"
            style={{ backgroundColor: `var(--no-${tipo})` }}
          />
          {ROTULO_TIPO[tipo]}
        </span>
      ))}
    </div>
  );
}
