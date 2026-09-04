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
 * O ROTULO E OBRIGATORIO -- mas nao precisa ser ESTE componente a imprimi-lo.
 * O PRODUCT.md exige que categoria nunca seja comunicada so por cor, e forma
 * tem a mesma fraqueza: um anel sozinho obriga o leitor a conhecer a
 * convencao. `comRotulo` (default `true`) manda a `CabecaVazada` escrever o
 * proprio rotulo. Quem passa `comRotulo={false}` esta dizendo "eu, quem
 * chamou, ja escrevo um rotulo textual equivalente ao lado" -- e assume a
 * obrigacao de cumprir isso de verdade.
 *
 * Por que nao veio um `rotuloVisivel={false}` que so escondia com `sr-only`:
 * `sr-only` tira o texto da tela mas MANTEM na arvore de acessibilidade --
 * quem usasse `CabecaVazada` ao lado do proprio rotulo (como
 * `EtiquetaCategoria`) fazia o leitor de tela ler o rotulo DUAS VEZES ("sem
 * sinal, sem sinal"). `comRotulo={false}` nao esconde o rotulo desta peca:
 * ele nao existe. A regra de nunca comunicar so por forma continua valendo
 * -- so muda QUEM imprime o texto, nunca SE ele existe.
 */
export function CabecaVazada({
  rotulo = "sem sinal",
  comRotulo = true,
  className,
}: {
  rotulo?: string;
  comRotulo?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span
        aria-hidden
        className="inline-block size-2 shrink-0 rounded-full border border-muted-foreground bg-transparent"
      />
      {comRotulo ? (
        <span className="text-xs text-muted-foreground">{rotulo}</span>
      ) : null}
    </span>
  );
}
