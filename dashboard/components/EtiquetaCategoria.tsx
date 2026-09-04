import type { Categoria } from "@/lib/api";
import { ROTULO_CATEGORIA, ROTULO_SEM_SINAL } from "@/lib/formato";
import { cn } from "@/lib/utils";
import { CabecaVazada } from "./CabecaVazada";

/**
 * Categoria de NPS como etiqueta.
 *
 * Cor NUNCA e o unico canal: o rotulo textual esta sempre escrito, e o ponto
 * colorido apenas reforca. A cor de TEXTO usa a variante `-texto` do token --
 * cor de marcacao e cor de tipo nao sao a mesma coisa, e so a variante cruza
 * 4.5:1 contra `--card`.
 *
 * `categoria: null` NAO cai numa quarta cor da escala de satisfacao: vira
 * `CabecaVazada` -- anel oco, nunca um quarto ponto cheio. Um ponto CHEIO
 * cinza, no mesmo slot dos tres pontos cheios coloridos, seria "cinza dentro
 * da escala" (DESIGN.md §5) -- exatamente o que a §1.1 probe.
 *
 * `comRotulo={false}`: esta etiqueta ja escreve `ROTULO_SEM_SINAL` por
 * extenso logo depois do anel (linha de baixo), entao a `CabecaVazada` NAO
 * imprime o proprio rotulo -- se imprimisse, o leitor de tela leria "sem
 * sinal, sem sinal". O rotulo textual continua existindo e continua na
 * arvore de acessibilidade; so quem o escreve mudou.
 */
const APARENCIA: Record<Categoria, { ponto: string; texto: string }> = {
  detrator: { ponto: "bg-detrator", texto: "text-detrator-texto" },
  neutro: { ponto: "bg-neutro", texto: "text-neutro-texto" },
  promotor: { ponto: "bg-promotor", texto: "text-promotor-texto" },
};

export function EtiquetaCategoria({
  categoria,
  className,
}: {
  categoria: Categoria | null;
  className?: string;
}) {
  const aparencia = categoria ? APARENCIA[categoria] : null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-sm whitespace-nowrap",
        aparencia ? aparencia.texto : "text-muted-foreground",
        className,
      )}
    >
      {aparencia ? (
        <span
          aria-hidden
          className={cn("size-2 shrink-0 rounded-full", aparencia.ponto)}
        />
      ) : (
        <CabecaVazada comRotulo={false} />
      )}
      {categoria ? ROTULO_CATEGORIA[categoria] : ROTULO_SEM_SINAL}
    </span>
  );
}
