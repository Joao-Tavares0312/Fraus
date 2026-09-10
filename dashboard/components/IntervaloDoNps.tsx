import { cn } from "@/lib/utils";
import { formatarNps } from "@/lib/formato";

/**
 * O NPS INFERIDO COM A INCERTEZA AMOSTRAL -- a extensao vertical do valor.
 *
 * O problema que resolve: "NPS -12" aparecia igual com 8 atendimentos e com
 * 8.000, e a primeira pergunta de quem avalia e quantas conversas sustentam o
 * numero. Um sistema que ja recusa transformar ausencia em zero nao pode
 * mostrar ponto estimado como se ele fosse exato.
 *
 * POR QUE NAO E UMA BARRA DE ERRO. Barra de erro e vocabulario de grafico
 * estatistico generico e nao pertence a este design system. Na gramatica da
 * pauta, o valor OCUPA UMA ALTURA na linha em vez de tocar um ponto: a
 * incerteza e extensao, nao ornamento pendurado no numero.
 *
 * A PAUSA. Com `n` abaixo do minimo, esta peca nao mostra numero -- mostra
 * pausa, que o DESIGN.md ja define como "silencio com duracao notada". E
 * ausencia que ocupa o tempo, e e exatamente "nao tenho amostra para
 * afirmar". O `n` continua impresso: a tela diz QUANTO falta.
 *
 * O ponto e a decisao do SERVIDOR: `nps_intervalo.nps` vem `null` abaixo do
 * minimo, e esta peca nao reimplementa o corte (invariante 3). Ela desenha.
 */
export type IntervaloNps = {
  nps: number | null;
  ic_inferior: number;
  ic_superior: number;
  n: number;
};

/** Posicao de um valor de NPS na escala -100..100, em porcentagem. */
function posicao(valor: number): number {
  return ((Math.min(100, Math.max(-100, valor)) + 100) / 200) * 100;
}

/**
 * Recebe um intervalo REAL, nunca nulo. Ausencia de intervalo tem duas causas
 * distintas -- "nenhum atendimento tem score" e "o agregado do servidor caiu,
 * e o plano B nao calcula intervalo" -- e esta peca nao sabe qual das duas
 * aconteceu. Escrever "nenhum atendimento" na segunda seria afirmar ausencia
 * sem ter como saber, com a confianca de quem sabe. Quem chama decide: sem
 * intervalo, nao renderiza, e o cartao do NPS ao lado ja nomeia o vazio.
 */
export function IntervaloDoNps({
  intervalo,
  className,
}: {
  intervalo: IntervaloNps;
  className?: string;
}) {
  const { nps, ic_inferior, ic_superior, n } = intervalo;
  const inicio = posicao(ic_inferior);
  const fim = posicao(ic_superior);

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div
        className="relative h-6 w-full"
        role="img"
        aria-label={
          nps === null
            ? `Amostra insuficiente: ${n} atendimento(s) com sinal. O intervalo de 95% vai de ${formatarNps(ic_inferior)} a ${formatarNps(ic_superior)}.`
            : `NPS inferido ${formatarNps(nps)}, intervalo de 95% de ${formatarNps(ic_inferior)} a ${formatarNps(ic_superior)}, sobre ${n} atendimento(s).`
        }
      >
        {/* A LINHA da escala -100..100. */}
        <span className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-linha" />

        {/* A EXTENSAO: o valor ocupa altura em vez de tocar um ponto. */}
        <span
          className="absolute top-1/2 h-4 -translate-y-1/2 rounded-xs bg-medido-fraco"
          style={{ left: `${inicio}%`, width: `${Math.max(fim - inicio, 0.5)}%` }}
        />

        {/* O ponto estimado so existe quando o servidor o afirma. */}
        {nps === null ? null : (
          <span
            className="absolute top-1/2 h-5 w-0.5 -translate-x-1/2 -translate-y-1/2 bg-medido"
            style={{ left: `${posicao(nps)}%` }}
          />
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        {nps === null ? (
          <>
            <strong className="font-medium text-foreground">
              Amostra insuficiente (n={n}).
            </strong>{" "}
            O intervalo de 95% vai de{" "}
            <span className="num">{formatarNps(ic_inferior)}</span> a{" "}
            <span className="num">{formatarNps(ic_superior)}</span> — largo
            demais para um ponto estimado significar alguma coisa.
          </>
        ) : (
          <>
            Intervalo de 95%:{" "}
            <span className="num">{formatarNps(ic_inferior)}</span> a{" "}
            <span className="num">{formatarNps(ic_superior)}</span>, sobre {n}{" "}
            atendimento(s) com sinal.
          </>
        )}{" "}
        Ele cobre a incerteza <strong>amostral</strong> — não a incerteza do
        modelo, que exigiria calibração.
      </p>
    </div>
  );
}
