import type { ReactNode } from "react";
import type { DetalheConversa } from "@/lib/api";
import {
  EXPLICACAO_SEM_SINAL,
  ROTULO_SEM_SINAL,
  formatarDataHora,
  formatarSegundos,
  formatarSegundosLED,
} from "@/lib/formato";
import { Badge } from "@/components/ui/badge";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { EtiquetaCategoria } from "@/components/EtiquetaCategoria";
import { MarcaContestacao } from "@/components/MarcaContestacao";
import { NotaLED } from "@/components/NotaLED";

/**
 * O RESUMO DE UM ATENDIMENTO: quatro leituras lidas de uma vez.
 *
 * E a armadura da tela do atendimento -- o mesmo desenho da Visao geral (uma
 * fileira de quatro celulas separadas por filete, rotulo mais numero em LED), e
 * por isso ele mora ao lado da `FaixaIndicadores` em idioma, mas NAO a reusa:
 * `CartaoIndicador` carrega o easter egg dos cinco cliques (`useMentira`), que
 * falsifica os quatro indicadores da Visao geral e nada mais. Uma nota de UM
 * atendimento mentindo enquanto o painel esta aberto seria o defeito que as
 * quatro travas existem para impedir; esta peca nunca soube mentir.
 *
 * As regras que ela nao quebra:
 *   - nota nula e "sem sinal": display APAGADO + a palavra + o motivo, nunca 0
 *     (invariante 2);
 *   - a nota, a categoria e a evidencia sao do SERVIDOR (invariante 3) -- aqui so
 *     se desenha;
 *   - `estimativa` colada a nota, `observado` colado a latencia: o que e
 *     inferido e o que e medido nunca se misturam (PRODUCT.md, principio 2);
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
  const latenciaLED = mediana === null ? null : formatarSegundosLED(mediana);

  return (
    <section
      aria-label="Resumo do atendimento"
      // O filete entre celulas e o `gap-px` sobre fundo de regua: cada celula
      // pinta o proprio fundo opaco. Uma tecnica so serve a 1, 2 ou 4 colunas.
      className="grid grid-cols-1 gap-px border border-linha bg-linha sm:grid-cols-2 xl:grid-cols-4 [&>*]:bg-background"
    >
      <Celula rotulo="Nota inferida" qualificacao="estimativa">
        {semNota ? (
          <>
            <div className="flex items-end gap-3">
              <NotaLED nota={null} altura={56} />
              <span className="pb-1 text-sm text-muted-foreground">
                {ROTULO_SEM_SINAL}
              </span>
            </div>
            <p className="text-xs leading-relaxed text-muted-foreground">
              {EXPLICACAO_SEM_SINAL[conversa.motivo_sem_sinal ?? "sem_fala_do_cliente"]}{" "}
              Sem sinal, não há nota — e ausência de dado não é insatisfação.
            </p>
          </>
        ) : (
          <>
            <div className="flex items-end gap-2">
              <NotaLED nota={conversa.nota} altura={56} />
              <span className="pb-1 text-sm text-muted-foreground">/ 10</span>
            </div>
            {/* Colada no numero, e nao no aparato da tela: uma ressalva sobre
                ESTE numero que morasse no rodape perderia a que numero se
                refere (DESIGN.md §4.1). */}
            <MarcaContestacao
              contestacao={conversa.contestacao}
              detalhado
              className="leading-relaxed"
            />
          </>
        )}
      </Celula>

      <Celula rotulo="Categoria">
        {/* O slot unico da cabeca: cheia, tracejada ou vazada, com o motivo da
            evidencia fraca impresso quando houver. */}
        <EtiquetaCategoria
          categoria={conversa.categoria}
          evidenciaFraca={conversa.evidencia_fraca}
          motivosEvidencia={conversa.motivos_evidencia_fraca}
          className="text-base whitespace-normal"
        />
        <p className="text-xs leading-relaxed text-muted-foreground">
          {conversa.categoria === null
            ? "Sem nota, sem categoria: ela é derivada da nota no servidor."
            : "Derivada da nota pelo servidor, com as faixas vigentes."}
        </p>
      </Celula>

      <Celula rotulo="Latência mediana" qualificacao="observado">
        <div className="flex items-end gap-1.5">
          <SegmentoLED
            valor={latenciaLED === null ? null : latenciaLED.valor}
            rotulo="latência mediana do atendimento"
            altura={40}
          />
          {latenciaLED ? (
            <span className="pb-0.5 text-xs leading-none text-muted-foreground">
              {latenciaLED.unidade}
            </span>
          ) : null}
        </div>
        <p className="text-xs text-muted-foreground">
          {mediana === null
            ? "Nenhuma resposta a medir: sem duas mensagens seguidas não há espera."
            : `sobre ${respostas} ${respostas === 1 ? "resposta" : "respostas"} · ${formatarSegundos(mediana)}`}
        </p>
      </Celula>

      <Celula rotulo="Atendimento" qualificacao="observado">
        <span className="num text-base text-foreground">{conversa.canal}</span>
        <span className="num block text-xs text-muted-foreground">
          {formatarDataHora(conversa.iniciada_em)}
        </span>
        <span className="num block text-xs text-muted-foreground">
          {duracao !== null
            ? `duração ${formatarSegundos(duracao)}`
            : "sem horário de encerramento"}
        </span>
        <span className="block text-xs text-muted-foreground">
          {conversa.escalou_para_humano ? "escalou para humano" : "contido no bot"}
        </span>
      </Celula>
    </section>
  );
}

function Celula({
  rotulo,
  qualificacao,
  children,
}: {
  rotulo: string;
  qualificacao?: string;
  children: ReactNode;
}) {
  return (
    <div className="quebra-evitar flex min-w-0 flex-col gap-2.5 px-4 py-3.5">
      <div className="flex items-start justify-between gap-2">
        <h2 className="rotulo-instrumento">{rotulo}</h2>
        {qualificacao ? (
          <Badge
            variant="outline"
            className="shrink-0 rounded-sm text-[0.6875rem] text-muted-foreground"
          >
            {qualificacao}
          </Badge>
        ) : null}
      </div>
      {children}
    </div>
  );
}
