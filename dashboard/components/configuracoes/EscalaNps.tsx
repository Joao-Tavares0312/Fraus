import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { cn } from "@/lib/utils";

export type Faixas = Record<string, [number, number]>;

export const CATEGORIAS = ["detrator", "neutro", "promotor"] as const;
export type CategoriaNps = (typeof CATEGORIAS)[number];

export const COR_DA_CATEGORIA: Record<string, string> = {
  detrator: "var(--detrator)",
  neutro: "var(--neutro)",
  promotor: "var(--promotor)",
};

export const CLASSE_TEXTO_DA_CATEGORIA: Record<string, string> = {
  detrator: "text-detrator-texto",
  neutro: "text-neutro-texto",
  promotor: "text-promotor-texto",
};

export const ROTULO_DA_CATEGORIA: Record<string, string> = {
  detrator: "Detrator",
  neutro: "Neutro",
  promotor: "Promotor",
};

export const NOTAS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

/** Quais categorias reivindicam a nota. Zero = buraco, duas ou mais = choque. */
export function categoriasDaNota(faixas: Faixas, nota: number): string[] {
  return Object.entries(faixas)
    .filter(([, [minima, maxima]]) => nota >= minima && nota <= maxima)
    .map(([categoria]) => categoria);
}

/**
 * A escala 0-10 INTEIRA, com a categoria em que cada nota cai.
 *
 * Este e o controle mais delicado da aplicacao, e a razao de a escala aparecer
 * por extenso e uma so: seis campos numericos nao deixam ninguem ver que a nota
 * 6 ficou orfa. Aqui a nota descoberta aparece hachurada e dita por escrito, e
 * a nota reivindicada por duas faixas aparece em conflito -- ANTES do salvar,
 * na mesma tela em que o servidor vai recusar.
 *
 * Cor nunca e o unico canal: cada celula carrega o nome da categoria embaixo do
 * numero, e as celulas problematicas carregam a palavra ("sem faixa",
 * "conflito").
 */
export function EscalaNps({
  faixas,
  className,
}: {
  faixas: Faixas;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0 overflow-x-auto", className)}>
      {/* `min-w` para o celular: onze celulas com o nome da categoria embaixo
          nao cabem em 390px sem cortar a palavra, e cortar a palavra deixaria
          a categoria so na cor. A escala rola dentro do proprio container. */}
      <ol
        className="grid min-w-[34rem] grid-cols-11 gap-px overflow-hidden border border-border bg-border"
        aria-label="Escala de notas de 0 a 10 e a categoria de cada nota"
      >
        {NOTAS.map((nota) => {
          const donas = categoriasDaNota(faixas, nota);
          const orfa = donas.length === 0;
          const conflito = donas.length > 1;
          const categoria = donas[0];

          return (
            <li
              key={nota}
              className={cn(
                "flex min-w-0 flex-col items-center gap-1 bg-card px-0.5 py-2 text-center",
                conflito && "outline outline-1 -outline-offset-1 outline-destructive",
              )}
              style={
                orfa || conflito
                  ? {
                      backgroundImage:
                        "repeating-linear-gradient(135deg, var(--muted) 0 4px, transparent 4px 8px)",
                    }
                  : undefined
              }
            >
              {/* A nota da escala em LED: e o indice 0-10, nao um valor
                  medido, entao a cor e `tinta` e nao o azul do medido. A nota
                  sem faixa ou em conflito apaga o brilho -- ela nao tem dona. */}
              <SegmentoLED
                valor={String(nota)}
                altura={18}
                cor="tinta"
                rotulo={`nota ${nota}`}
                className={orfa || conflito ? "opacity-50" : undefined}
              />
              <span
                aria-hidden
                className="h-1 w-full rounded-xs"
                style={{
                  background:
                    orfa || conflito
                      ? "transparent"
                      : (COR_DA_CATEGORIA[categoria] ?? "var(--sem-sinal)"),
                }}
              />
              <span
                className={cn(
                  "text-[0.6875rem] leading-tight",
                  conflito
                    ? "text-destructive"
                    : orfa
                      ? "text-muted-foreground"
                      : (CLASSE_TEXTO_DA_CATEGORIA[categoria] ??
                        "text-muted-foreground"),
                )}
              >
                {conflito
                  ? "conflito"
                  : orfa
                    ? "sem faixa"
                    : (ROTULO_DA_CATEGORIA[categoria] ?? categoria)}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
