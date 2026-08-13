import type { DetalheConversa } from "@/lib/api";
import {
  latenciasAnotadas,
  ROTULO_LATENCIA,
  severidadeLatencia,
  type MarcaAtribuicao,
  type SentidoAtribuicao,
  type SeveridadeLatencia,
} from "@/lib/derivacoes";
import { formatarHora, formatarSegundos, ROTULO_AUTOR } from "@/lib/formato";

const COR_SEVERIDADE: Record<SeveridadeLatencia, string> = {
  pico: "var(--promotor)",
  saudavel: "var(--muted-foreground)",
  degradando: "var(--neutro)",
  abandono: "var(--detrator)",
};

const COR_SENTIDO: Record<SentidoAtribuicao, string> = {
  puxou_para_baixo: "var(--detrator)",
  puxou_para_cima: "var(--promotor)",
  sem_inclinacao: "var(--muted-foreground)",
};

const ROTULO_SENTIDO: Record<SentidoAtribuicao, string> = {
  puxou_para_baixo: "puxou a nota para baixo",
  puxou_para_cima: "puxou a nota para cima",
  sem_inclinacao: "sem inclinação clara",
};

function porcentagem(valor: number): string {
  return `${Math.round(valor * 100)}%`;
}

/**
 * Intensidade do realce de um trecho, PROPORCIONAL a probabilidade real.
 *
 * O saldo (P(satisfeito) - P(insatisfeito)) vive em [-1, 1]; o realce usa o
 * modulo dele, com teto de 26% de opacidade -- acima disso o texto perde
 * contraste, e nenhuma marcacao vale um paragrafo ilegivel.
 *
 * A intensidade e o TERCEIRO canal, nunca o primeiro: a direcao ja esta na
 * borda colorida E no rotulo textual embaixo. Quem nao distingue as cores
 * continua lendo "puxou a nota para baixo · 82% de insatisfeito".
 */
function realce(marca: MarcaAtribuicao): string | undefined {
  if (marca.sentido === "sem_inclinacao") return undefined;
  const intensidade = Math.min(1, Math.abs(marca.saldo)) * 26;
  return `color-mix(in oklch, ${COR_SENTIDO[marca.sentido]} ${intensidade.toFixed(1)}%, transparent)`;
}

/**
 * Transcricao com as tres coisas que transformam "nota ruim" em "oportunidade
 * de melhoria":
 *
 *   1. cliente e bot visualmente distintos -- a fala do cliente e o que foi
 *      DITO, entao ela veste ambar (`--dito`) e a superficie elevada; a
 *      resposta da maquina fica recuada, em superficie de painel;
 *   2. a latencia anotada em CADA resposta, com a faixa de severidade da
 *      literatura de live chat -- ela sai dos timestamps, nao do modelo;
 *   3. a marcacao das falas do cliente pela probabilidade POR MENSAGEM do
 *      classificador, vinda de `GET /conversas/{id}/atribuicao`, com
 *      intensidade proporcional a essa probabilidade.
 *
 * A marcacao do item 3 e do SERVIDOR. Quando `marcas` vem vazio (a chamada da
 * atribuicao falhou), a transcricao aparece SEM marcacao nenhuma em vez de
 * cair de volta numa heuristica de emoji: uma fonte so para "o que puxou a
 * nota".
 */
export function Transcricao({
  conversa,
  marcas,
}: {
  conversa: DetalheConversa;
  marcas: Map<number, MarcaAtribuicao>;
}) {
  const latencias = new Map(
    latenciasAnotadas(conversa.mensagens).map((l) => [l.indice, l.segundos]),
  );

  return (
    <ol className="divide-y divide-border">
      {conversa.mensagens.map((mensagem, indice) => {
        const doCliente = mensagem.autor === "cliente";
        const latencia = latencias.get(indice);
        const marca = marcas.get(indice);
        const severidade =
          latencia === undefined ? null : severidadeLatencia(latencia);

        return (
          <li
            key={`${indice}-${mensagem.enviada_em}`}
            className={`quebra-evitar grid grid-cols-[5.5rem_1fr] gap-x-4 px-5 py-3.5 sm:grid-cols-[7rem_1fr] ${
              doCliente ? "bg-muted/50" : ""
            }`}
          >
            <div className="flex flex-col gap-0.5 pt-0.5">
              <span
                className={`text-xs font-medium ${
                  doCliente ? "text-dito-texto" : "text-muted-foreground"
                }`}
              >
                {ROTULO_AUTOR[mensagem.autor] ?? mensagem.autor}
              </span>
              <span className="num text-[0.6875rem] text-muted-foreground">
                {formatarHora(mensagem.enviada_em)}
              </span>
            </div>

            <div className="min-w-0">
              <p
                className={`max-w-[70ch] rounded-md text-sm leading-relaxed text-foreground ${
                  doCliente
                    ? marca && marca.sentido !== "sem_inclinacao"
                      ? "border-l-2 px-3 py-1.5"
                      : "px-0"
                    : "border-l border-border pl-3"
                }`}
                style={
                  doCliente && marca && marca.sentido !== "sem_inclinacao"
                    ? {
                        borderColor: COR_SENTIDO[marca.sentido],
                        backgroundColor: realce(marca),
                      }
                    : undefined
                }
              >
                {mensagem.texto}
              </p>

              {latencia !== undefined && severidade ? (
                <p className="mt-1.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
                  <span
                    aria-hidden
                    className="inline-block size-1.5 rounded-full"
                    style={{ background: COR_SEVERIDADE[severidade] }}
                  />
                  <span className="num text-[0.6875rem] text-tempo-texto">
                    {formatarSegundos(latencia)}
                  </span>
                  <span className="text-[0.6875rem] text-muted-foreground">
                    de espera do cliente até esta resposta ·{" "}
                    {ROTULO_LATENCIA[severidade].titulo.toLowerCase()} (
                    {ROTULO_LATENCIA[severidade].detalhe})
                  </span>
                </p>
              ) : null}

              {marca ? (
                <div className="mt-2 flex flex-col gap-1">
                  <p className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span className="inline-flex items-baseline gap-1.5 text-xs font-medium text-foreground">
                      <span
                        aria-hidden
                        className="inline-block size-2 -translate-y-px rounded-full"
                        style={{ background: COR_SENTIDO[marca.sentido] }}
                      />
                      {ROTULO_SENTIDO[marca.sentido]}
                    </span>
                    <span className="num text-xs text-muted-foreground">
                      {porcentagem(marca.probabilidade)} de {marca.classe} no
                      classificador de texto
                    </span>
                  </p>
                  <BarraProbabilidade marca={marca} />
                </div>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/**
 * Barra das tres probabilidades da mensagem, na ordem fixa das classes
 * (0 insatisfeito, 1 neutro, 2 satisfeito -- invariante 8). E a leitura mais
 * rapida possivel de "o quanto o modelo esta convencido": a largura E a
 * probabilidade.
 */
function BarraProbabilidade({ marca }: { marca: MarcaAtribuicao }) {
  const faixas = [
    { chave: "insatisfeito", valor: marca.probInsatisfeito, cor: "var(--detrator)" },
    { chave: "neutro", valor: marca.probNeutro, cor: "var(--neutro)" },
    { chave: "satisfeito", valor: marca.probSatisfeito, cor: "var(--promotor)" },
  ];

  return (
    <span
      className="flex h-1 w-full max-w-[22rem] gap-px overflow-hidden rounded-sm bg-muted"
      role="img"
      aria-label={faixas
        .map((faixa) => `${faixa.chave} ${porcentagem(faixa.valor)}`)
        .join(", ")}
      title={faixas
        .map((faixa) => `${faixa.chave}: ${porcentagem(faixa.valor)}`)
        .join(" · ")}
    >
      {faixas.map((faixa) => (
        <span
          key={faixa.chave}
          style={{ width: `${faixa.valor * 100}%`, background: faixa.cor }}
        />
      ))}
    </span>
  );
}
