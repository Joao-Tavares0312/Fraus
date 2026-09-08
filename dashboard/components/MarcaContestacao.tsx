import type { Contestacao } from "@/lib/api";
import { formatarSegundos } from "@/lib/formato";
import { cn } from "@/lib/utils";

/**
 * A marca de quando o tempo contesta o elogio.
 *
 * Score saturado convivendo com espera longa: a leitura mais provavel e ironia
 * ("que atendimento maravilhoso, so esperei 3 horas"), e o modelo nao alcanca
 * isso sozinho -- nenhuma feature agregada de conversa reverte uma
 * probabilidade saturada por mensagem. A marca acompanha o numero em vez de
 * corrigi-lo: score, nota e categoria seguem exibidos como sempre, e o
 * atendimento continua contando no NPS.
 *
 * ROTULO CURTO, NAO APARATO (DESIGN.md §4.1). `estimativa`, `observado` e
 * `sem sinal` ficam colados ao numero, sempre visiveis; so a prosa
 * metodologica migra para o rodape. Uma ressalva sobre ESTE numero que morasse
 * no aparato da tela perderia a que numero se refere.
 *
 * `--warning` PORQUE ELE E COR DE TEXTO E NUNCA PREENCHIMENTO (DESIGN.md
 * §3.3): o precedente exato e o rotulo "suspeito" de `MetricasTreino`, que
 * marca metrica boa demais pelo mesmo motivo -- numero que merece desconfianca
 * sem deixar de ser o numero. Ele compartilha o matiz do dourado da marca e
 * sobrevive por ser tipo, nao superficie.
 *
 * SEM ESTADO, SEM EFEITO, SEM ANIMACAO DE ENTRADA. Ela vem dos campos que a
 * API mandou e sai do markup renderizado no servidor. E a mesma regra que
 * tirou a etiqueta de honestidade do `Revelar` na vitrine: numa ferramenta
 * cujo nome e o daimon do engano, a ressalva nao pode ser a parte que some
 * quando o JavaScript falha.
 *
 * NAO usa `CabecaVazada`: aquilo e a notacao de AUSENCIA de sinal (§1.1), e
 * aqui ha sinal de sobra -- ha dois, e eles discordam. Emprestar o simbolo do
 * vazio para o conflito apagaria a distincao que a cabeca vazada existe para
 * fazer.
 */
export function MarcaContestacao({
  contestacao,
  className,
  detalhado = false,
}: {
  contestacao: Contestacao | null;
  className?: string;
  /** Na transcricao ha espaco para a frase inteira; na tabela, nao. */
  detalhado?: boolean;
}) {
  if (contestacao === null) return null;

  const espera = formatarSegundos(contestacao.latencia_mediana_s);

  return (
    <span
      className={cn(
        "inline-flex items-baseline gap-1.5 text-xs font-normal text-warning-rich-text",
        className,
      )}
    >
      {/* `aria-hidden` no simbolo, texto por extenso ao lado: cor e glifo
          nunca sao o unico canal -- a mesma regra de `EtiquetaCategoria`. */}
      <span aria-hidden>⚠</span>
      {detalhado ? (
        <span>
          Leitura contestada — elogio saturado ({contestacao.score.toFixed(2)})
          contra espera mediana de {espera}. O modelo leu como satisfacao; o
          relógio discorda. A nota ao lado não foi alterada, e este atendimento
          continua contando nos indicadores.
        </span>
      ) : (
        <span>
          contestada — elogio contra espera de {espera}
        </span>
      )}
    </span>
  );
}
