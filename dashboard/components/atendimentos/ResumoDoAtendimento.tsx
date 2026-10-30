import type { DetalheConversa } from "@/lib/api";
import {
  EXPLICACAO_SEM_SINAL,
  ROTULO_SEM_SINAL,
  formatarDataHora,
  formatarSegundos,
} from "@/lib/formato";
import { CabecaVazada } from "@/components/CabecaVazada";
import { Explicacao } from "@/components/Explicacao";
import { EtiquetaCategoria } from "@/components/EtiquetaCategoria";
import { MarcaContestacao } from "@/components/MarcaContestacao";
import { NotaInferida } from "@/components/NotaInferida"

/**
 * O RESUMO DE UM ATENDIMENTO, numa linha (KISS, 30/10/2026): nota e
 * categoria primeiro, depois canal, data, duracao, espera e desfecho.
 *
 * As regras que ela nao quebra:
 *   - nota nula e "sem sinal", com a palavra, nunca zero (invariante 2); o
 *     motivo mora no ⓘ;
 *   - a nota, a categoria e a evidencia sao do SERVIDOR (invariante 3) -- aqui so
 *     se desenha;
 *   - `estimativa` colada a nota: o que e inferido e o que e medido nunca se
 *     misturam (PRODUCT.md, principio 2);
 *   - a latencia e derivada dos timestamps na leitura, nunca lida de um campo
 *     gravado (invariante 5).
 */
export function ResumoDoAtendimento({
  conversa,
  mediana,
  respostas,
  duracao,
}: {
  conversa: DetalheConversa;
  /** Mediana das esperas, derivada dos timestamps; `null` se nao houve resposta. */
  mediana: number | null;
  respostas: number;
  duracao: number | null;
}) {
  const semNota = conversa.nota === null;

  const fatos = [
    conversa.canal,
    formatarDataHora(conversa.iniciada_em),
    duracao !== null ? `duração ${formatarSegundos(duracao)}` : null,
    mediana !== null
      ? `espera mediana ${formatarSegundos(mediana)} (${respostas} ${respostas === 1 ? "resposta" : "respostas"})`
      : null,
    conversa.escalou_para_humano ? "escalou para humano" : "contido no bot",
  ].filter((fato): fato is string => fato !== null);

  return (
    <section
      aria-label="Resumo do atendimento"
      className="flex min-w-0 flex-col gap-1.5"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {semNota ? (
          <span className="inline-flex items-center gap-1">
            <CabecaVazada rotulo={ROTULO_SEM_SINAL} className="text-base" />
            <Explicacao rotulo="Por que não há nota">
              {EXPLICACAO_SEM_SINAL[conversa.motivo_sem_sinal ?? "sem_fala_do_cliente"]}{" "}
              Sem sinal, não há nota, e ausência de dado não é insatisfação.
            </Explicacao>
          </span>
        ) : (
          <>
            <span className="flex items-end gap-1.5">
              <NotaInferida nota={conversa.nota} className="text-3xl" />
              <span className="pb-1 text-sm text-muted-foreground">/ 10</span>
            </span>
            <EtiquetaCategoria
              categoria={conversa.categoria}
              evidenciaFraca={conversa.evidencia_fraca}
              motivosEvidencia={conversa.motivos_evidencia_fraca}
              className="text-base whitespace-normal"
            />
            <span className="inline-flex items-center gap-0.5 text-xs text-muted-foreground">
              estimativa
              <Explicacao rotulo="Sobre a nota estimada">
                Nota inferida do texto pelo servidor, não perguntada ao
                cliente. A categoria sai da nota pelas faixas vigentes.
              </Explicacao>
            </span>
          </>
        )}
      </div>
      <p className="num text-sm text-muted-foreground">{fatos.join(" · ")}</p>
      {semNota ? null : (
        <MarcaContestacao
          contestacao={conversa.contestacao}
          detalhado
          className="leading-relaxed"
        />
      )}
    </section>
  );
}
