import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { ordenarPorMagnitude } from "@/lib/derivacoes";
import { EXPLICACAO_SEM_SINAL, formatarComSinal } from "@/lib/formato";
import type { MotivoSemSinal } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { BarrasDeFeature } from "./BarrasDeFeature";
import { EstadoVazio } from "./EstadoVazio";
import { RessalvaDaTela } from "./AparatoDaTela";

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
 *
 * Recebe os tres campos soltos, nao o objeto inteiro de uma rota -- `Atribuicao`
 * (tela de atendimento) e `ConversaAnalisada` (tela `/analisar`) tem formatos
 * diferentes por fora, mas os tres campos que este painel usa sao identicos nos
 * dois. Acoplar ao tipo de uma rota so far duplicaria o componente na outra tela,
 * que e exatamente o erro que o `sinais_fora_do_score` de `/analisar` sofreu ate
 * aqui (existe no tipo desde a mudanca de 04/09/2026, nunca foi renderizado).
 */
export function PainelContribuicoes({
  contribuicoes,
  sinaisForaDoScore,
  totalDeFeatures,
  motivoSemSinal = null,
}: {
  contribuicoes: Record<string, number> | null;
  sinaisForaDoScore: string[];
  totalDeFeatures: number;
  /** Do servidor. Sem ele, o texto generico cobre os dois motivos. */
  motivoSemSinal?: MotivoSemSinal | null;
}) {
  if (contribuicoes === null) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="Sem contribuições para este atendimento"
        explicacao={`${motivoSemSinal ? EXPLICACAO_SEM_SINAL[motivoSemSinal] : "Não há sinal do cliente neste atendimento."} Sem nota não há contribuições para mostrar. Ausência de contribuição não significa que cada sinal vale zero.`}
      />
    );
  }

  const features = ordenarPorMagnitude(contribuicoes);
  const paraCima = features.filter((f) => f.valor > 0).length;
  const paraBaixo = features.filter((f) => f.valor < 0).length;
  const foraDoScore = sinaisForaDoScore;

  return (
    <>
    <div className="flex flex-col gap-4 px-5 py-4">
      <Alert className="rounded-md">
        <AlertTitle className="text-sm">
          O que influenciou esta leitura
        </AlertTitle>
        <AlertDescription className="text-sm leading-relaxed">
          As barras mostram a contribuição dos {totalDeFeatures} sinais{" "}
          <strong className="font-medium text-foreground">
            neste atendimento
          </strong>
          . Valores positivos favorecem a leitura de satisfação; negativos,
          a de insatisfação. Não são pontos da nota nem efeitos causais.
          O peso global dos sinais está na tela{" "}
          <Link
            href="/dashboard/modelo"
            className="inline-flex items-center gap-0.5 text-primary underline underline-offset-4"
          >
            Modelo
            <ArrowUpRight aria-hidden className="size-3" />
          </Link>
          .
        </AlertDescription>
      </Alert>

      {foraDoScore.length > 0 && (
        <Alert className="rounded-md">
          <AlertTitle className="text-sm">
            {foraDoScore.length === 1
              ? "Um sinal foi lido, mas não pontua."
              : `${foraDoScore.length} sinais foram lidos, mas não pontuam.`}
          </AlertTitle>
          <AlertDescription className="text-sm leading-relaxed">
            <code className="break-words rounded bg-muted px-1 py-0.5 text-sm">
              {foraDoScore.join(", ")}
            </code>{" "}
            aparece por mensagem nesta tela, mas não entra na lista de
            contribuições abaixo nem move a nota. É leitura, não decisão.
          </AlertDescription>
        </Alert>
      )}

      <p className="text-sm text-muted-foreground">
        <span className="num text-promotor-texto">{paraCima}</span>{" "}
        {paraCima === 1 ? "sinal com contribuição positiva" : "sinais com contribuição positiva"} ·{" "}
        <span className="num text-detrator-texto">{paraBaixo}</span> com
        contribuição negativa. Ordenados pelo tamanho da contribuição,
        independentemente do sentido.
      </p>

      <BarrasDeFeature
        features={features}
        modo="divergente"
        formatarValor={(valor) => formatarComSinal(valor, 2)}
      />
    </div>
      <RessalvaDaTela titulo="Contribuições dos sinais">
        As contribuições são termos na diferença entre os logits de
        satisfeito e insatisfeito, não pontos da nota. A transformação em
        score é não linear; uma contribuição positiva favorece satisfeito
        em relação a insatisfeito, mas não mede o efeito isolado sobre a
        nota nem estabelece causalidade. Estes valores descrevem este
        atendimento, não a importância global dos sinais no modelo.
      </RessalvaDaTela>
    </>
  );
}
