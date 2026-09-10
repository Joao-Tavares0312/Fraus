import { cn } from "@/lib/utils";

/**
 * A CABECA TRACEJADA: medido, com evidencia fraca.
 *
 * Fecha o trio que a §1.1 do DESIGN.md abriu:
 *
 *   cheia      medido, com evidencia
 *   tracejada  medido, evidencia fraca   <- esta
 *   vazada     nao medido
 *
 * O buraco que ela tapa era visivel na tela: uma conversa cujo cliente
 * escreveu so "ok" saia CHEIA, com a mesma confianca visual de uma conversa de
 * 40 turnos. As duas tinham nota; so uma tinha material para sustenta-la.
 *
 * POR QUE TRACEJADA E NAO MEIO-CHEIA, nem cinza: o contorno continua inteiro
 * -- o valor existe e esta na escala --, mas a linha e interrompida. Cinza
 * seria "valor baixo" (a §5 proibe cinza dentro da escala) e preenchimento
 * parcial seria uma segunda leitura quantitativa competindo com a nota.
 *
 * A EVIDENCIA VEM DO SERVIDOR, sempre. `evidencia_fraca` e derivada em
 * `fraus/evidencia.py` a partir de fala observavel -- quantas mensagens,
 * quantas palavras --, NUNCA da probabilidade do modelo: probabilidade nao
 * calibrada nao e confianca. Esta peca desenha; ela nao decide.
 *
 * O ROTULO E OBRIGATORIO, mesma regra da `CabecaVazada`: forma sozinha obriga
 * o leitor a conhecer a convencao. Aqui ele vai alem de nomear o estado e
 * imprime o MOTIVO, porque "evidencia fraca" nao aciona ninguem e "menos de 5
 * palavras do cliente" aciona.
 */
export function CabecaTracejada({
  motivos = [],
  comRotulo = true,
  className,
}: {
  /** Por que a evidência é fraca — vem pronto do servidor. */
  motivos?: string[];
  comRotulo?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn("inline-flex items-center gap-1.5", className)}
      title={motivos.length > 0 ? motivos.join("; ") : undefined}
    >
      <span
        aria-hidden
        className="inline-block size-2 shrink-0 rounded-full border border-dashed border-medido bg-transparent"
      />
      {comRotulo ? (
        <span className="text-xs text-muted-foreground">
          {motivos.length > 0 ? `evidência fraca: ${motivos[0]}` : "evidência fraca"}
        </span>
      ) : null}
    </span>
  );
}
