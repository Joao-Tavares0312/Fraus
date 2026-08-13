import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { Atribuicao } from "@/lib/api";
import { ordenarPorMagnitude } from "@/lib/derivacoes";
import { formatarNumero } from "@/lib/formato";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { BarrasDeFeature } from "./BarrasDeFeature";
import { EstadoVazio } from "./EstadoVazio";

/**
 * As `contribuicoes` DESTE atendimento.
 *
 * Este painel existe para nao repetir o erro que derruba numa banca:
 * `importancias` e o peso GLOBAL do modelo -- vale para todos os atendimentos,
 * e sempre positivo, e nao explica nenhum caso; `contribuicoes` e quanto cada
 * feature pesou NESTE atendimento, COM SINAL.
 *
 * A distincao aparece em tres lugares ao mesmo tempo:
 *   - na copy: o titulo, o subtitulo e o aviso dizem qual e qual;
 *   - na geometria: contribuicao sai de um eixo central para os dois lados;
 *     importancia cresce da esquerda (e mora em outra TELA, a de Modelo);
 *   - na cor: aqui a escala e a divergente (promotor/detrator), la e a dos
 *     tres tipos de sinal.
 */
export function PainelContribuicoes({
  atribuicao,
  totalDeFeatures,
}: {
  atribuicao: Atribuicao;
  totalDeFeatures: number;
}) {
  if (atribuicao.contribuicoes === null) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="Sem contribuições para este atendimento"
        explicacao="O cliente não falou, então não há score — e sem score não há o que decompor. As contribuições vêm null do servidor exatamente neste caso; preencher com zeros diria que cada sinal pesou nada, quando na verdade nenhum sinal foi medido."
      />
    );
  }

  const features = ordenarPorMagnitude(atribuicao.contribuicoes);
  const paraCima = features.filter((f) => f.valor > 0).length;
  const paraBaixo = features.filter((f) => f.valor < 0).length;

  return (
    <div className="flex flex-col gap-4 px-5 py-4">
      <Alert className="rounded-md">
        <AlertTitle className="text-xs">
          Isto não é a importância do modelo.
        </AlertTitle>
        <AlertDescription className="text-xs leading-relaxed">
          O que está abaixo é a contribuição das {totalDeFeatures} features{" "}
          <strong className="font-medium text-foreground">
            neste atendimento
          </strong>
          , com sinal: positivo empurrou a nota para cima, negativo puxou para
          baixo. O peso <em>global</em> do modelo — o mesmo para todos os
          atendimentos — vive na tela{" "}
          <Link
            href="/modelo"
            className="inline-flex items-center gap-0.5 text-primary underline underline-offset-4"
          >
            Modelo
            <ArrowUpRight aria-hidden className="size-3" />
          </Link>
          .
        </AlertDescription>
      </Alert>

      <p className="text-xs text-muted-foreground">
        <span className="num text-promotor-texto">{paraCima}</span> feature(s)
        empurraram para cima ·{" "}
        <span className="num text-detrator-texto">{paraBaixo}</span> puxaram
        para baixo. Ordenadas por magnitude — a de cima é a que mais mexeu na
        nota.
      </p>

      <BarrasDeFeature
        features={features}
        modo="divergente"
        formatarValor={(valor) =>
          `${valor > 0 ? "+" : valor < 0 ? "−" : ""}${formatarNumero(Math.abs(valor), 2)}`
        }
      />
    </div>
  );
}
