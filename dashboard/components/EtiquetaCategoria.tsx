import type { Categoria } from "@/lib/api";
import { ROTULO_CATEGORIA, ROTULO_SEM_SINAL } from "@/lib/formato";

const COR: Record<Categoria, string> = {
  detrator: "var(--detrator)",
  neutro: "var(--neutro)",
  promotor: "var(--promotor)",
};

/**
 * Categoria sempre com PONTO + PALAVRA: a cor nunca carrega o significado
 * sozinha (daltonismo, impressao em preto e branco, projetor de banca).
 *
 * `categoria: null` vira "sem sinal", jamais nota 0 -- ausencia de dado nao e
 * insatisfacao.
 */
export function EtiquetaCategoria({
  categoria,
  className = "",
}: {
  categoria: Categoria | null;
  className?: string;
}) {
  const semSinal = categoria === null;
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap text-[0.8125rem] ${
        semSinal ? "text-[var(--tinta-3)]" : "text-[var(--tinta)]"
      } ${className}`}
    >
      {semSinal ? (
        <span
          aria-hidden
          className="h-[7px] w-[7px] rounded-full border border-dashed"
          style={{ borderColor: "var(--sem-sinal)" }}
        />
      ) : (
        <span
          aria-hidden
          className="h-[7px] w-[7px] rounded-full"
          style={{ background: COR[categoria] }}
        />
      )}
      {semSinal ? ROTULO_SEM_SINAL : ROTULO_CATEGORIA[categoria]}
    </span>
  );
}
