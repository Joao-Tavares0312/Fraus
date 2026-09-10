import { cn } from "@/lib/utils";

/**
 * FALSO CONTAINMENT: o unico lugar da interface onde DITO e MEDIDO se
 * contradizem, desenhado como contradicao.
 *
 * A regra mestra do DESIGN.md (§1) divide a composicao: acima da linha o que
 * foi DITO, abaixo o que foi MEDIDO. Em toda outra peca as duas metades
 * concordam ou falam de coisas diferentes. Aqui elas discordam sobre o MESMO
 * atendimento: o log diz "nao escalou, o bot deu conta" e a fala do cliente
 * diz "detrator". Por isso esta peca nao e mais um `CartaoIndicador` na
 * armadura -- um cartao empilha o numero ao lado de outros quatro e apaga
 * exatamente o que ele tem de diferente.
 *
 * A LINHA no meio nao e enfeite: e a regua que afirma qual metade e qual.
 *
 * `percentual` vem `null` quando nenhum atendimento contido tem sinal, e ai a
 * peca NAO mostra numero -- mostra o motivo. Zero se leria como "nenhum
 * contido saiu insatisfeito", afirmacao que ninguem mediu.
 *
 * O denominador e impresso junto (`contidos`) de proposito: 33% sobre tres
 * atendimentos e 33% sobre trezentos sao a mesma tinta e leituras diferentes.
 */
export function DiscordanciaContida({
  percentual,
  contidos,
  className,
}: {
  percentual: number | null;
  contidos: number;
  className?: string;
}) {
  const insatisfeitos =
    percentual === null ? null : Math.round((percentual / 100) * contidos);

  return (
    <section
      className={cn("flex flex-col gap-2", className)}
      aria-labelledby="falso-containment-rotulo"
    >
      <h3
        id="falso-containment-rotulo"
        className="text-xs font-medium tracking-wide text-muted-foreground uppercase"
      >
        Contenção que não convenceu
      </h3>

      {percentual === null ? (
        <p className="text-sm text-muted-foreground">
          Nenhum atendimento contido tem fala do cliente no período — sem sinal
          não há como saber se a contenção foi boa notícia.
        </p>
      ) : (
        <>
          {/* ACIMA DA LINHA -- o que o cliente DISSE (ambar). */}
          <p className="text-sm text-dito-texto">
            {insatisfeitos} saiu(ram) <strong>detrator(es)</strong>
          </p>

          <div className="h-px w-full bg-linha" aria-hidden />

          {/* ABAIXO DA LINHA -- o que o log MEDIU (azul). */}
          <p className="text-sm text-medido-texto">
            e mesmo assim <strong>não escalou</strong> para humano
          </p>

          <p className="font-mono text-3xl tabular-nums">
            {percentual.toLocaleString("pt-BR", {
              maximumFractionDigits: 1,
            })}
            <span className="text-lg text-muted-foreground">%</span>
          </p>
          <p className="text-xs text-muted-foreground">
            {insatisfeitos} de {contidos} atendimento(s) contido(s) com sinal.
            Contenção alta com esta taxa alta é sucesso falso: a métrica sobe
            enquanto a experiência piora.
          </p>
        </>
      )}
    </section>
  );
}
