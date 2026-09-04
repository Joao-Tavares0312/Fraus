import { cn } from "@/lib/utils";

/**
 * A CABECA VAZADA: "sem sinal" como NOTACAO, nao como string.
 *
 * A §1.1 do DESIGN.md promete esta peca desde o comeco e a chama de a mais
 * importante da lista: "o marcador existe, ocupa a posicao temporal, e e oco".
 * O principio de produto 3 -- ausencia de dado nao e insatisfacao -- deixa de
 * ser nota de rodape e vira forma.
 *
 * POR QUE OCO E NAO CINZA: cinza dentro da escala leria como um valor baixo.
 * Oco nao esta na escala; ele ocupa o tempo e nao soa.
 *
 * O ROTULO E OBRIGATORIO. O PRODUCT.md exige que categoria nunca seja
 * comunicada so por cor, e forma tem a mesma fraqueza: um anel sozinho obriga
 * o leitor a conhecer a convencao. Quem quiser esconder o rotulo do desenho
 * (numa celula estreita, por exemplo) usa `rotuloVisivel={false}` -- que o
 * mantem para o leitor de tela, e nunca o remove.
 */
export function CabecaVazada({
  rotulo = "sem sinal",
  rotuloVisivel = true,
  className,
}: {
  rotulo?: string;
  rotuloVisivel?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span
        aria-hidden
        className="inline-block size-2.5 shrink-0 rounded-full border border-muted-foreground bg-transparent"
      />
      <span className={cn("text-xs", rotuloVisivel ? "text-muted-foreground" : "sr-only")}>
        {rotulo}
      </span>
    </span>
  );
}
