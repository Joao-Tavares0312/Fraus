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
  saudavel: "var(--tinta-3)",
  degradando: "var(--neutro)",
  abandono: "var(--detrator)",
};

const COR_SENTIDO: Record<SentidoAtribuicao, string> = {
  puxou_para_baixo: "var(--detrator)",
  puxou_para_cima: "var(--promotor)",
  sem_inclinacao: "var(--tinta-3)",
};

const ROTULO_SENTIDO: Record<SentidoAtribuicao, string> = {
  puxou_para_baixo: "puxou a nota para baixo",
  puxou_para_cima: "puxou a nota para cima",
  sem_inclinacao: "sem inclinação clara",
};

const ROTULO_CLASSE: Record<MarcaAtribuicao["classe"], string> = {
  insatisfeito: "insatisfeito",
  neutro: "neutro",
  satisfeito: "satisfeito",
};

function porcentagem(valor: number): string {
  return `${Math.round(valor * 100)}%`;
}

/**
 * Transcricao com as tres coisas que transformam "nota ruim" em "oportunidade
 * de melhoria":
 *
 *   1. cliente e bot visualmente distintos (superficie e alinhamento, nao cor
 *      decorativa) -- quem le precisa saber de quem e a fala sem procurar;
 *   2. a latencia anotada ao lado de CADA resposta, com a faixa de severidade
 *      da literatura de live chat -- ela sai dos timestamps, nao do modelo;
 *   3. a marcacao das falas do cliente pela probabilidade POR MENSAGEM do
 *      classificador, vinda de `GET /conversas/{id}/atribuicao`.
 *
 * A marcacao do item 3 e do SERVIDOR. Quando `marcas` vem vazio (a chamada da
 * atribuicao falhou), a transcricao aparece sem marcacao nenhuma em vez de
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
    <ol className="divide-y divide-[var(--filete)]">
      {conversa.mensagens.map((mensagem, indice) => {
        const doCliente = mensagem.autor === "cliente";
        const latencia = latencias.get(indice);
        const marca = marcas.get(indice);
        const puxouParaBaixo = marca?.sentido === "puxou_para_baixo";

        return (
          <li
            key={`${indice}-${mensagem.enviada_em}`}
            className={`quebra-evitar grid grid-cols-[6.5rem_1fr] gap-x-4 px-5 py-3.5 ${
              doCliente ? "bg-[var(--superficie-2)]" : ""
            }`}
          >
            <div className="flex flex-col gap-0.5 pt-0.5">
              <span
                className={`text-[0.75rem] font-medium ${
                  doCliente ? "text-[var(--tinta)]" : "text-[var(--tinta-2)]"
                }`}
              >
                {ROTULO_AUTOR[mensagem.autor] ?? mensagem.autor}
              </span>
              <span className="font-mono text-[0.6875rem] tabular-nums text-[var(--tinta-3)]">
                {formatarHora(mensagem.enviada_em)}
              </span>
            </div>

            <div className="min-w-0">
              <p
                className={`max-w-[70ch] text-[0.875rem] leading-[1.6] text-[var(--tinta)] ${
                  doCliente
                    ? marca && marca.sentido !== "sem_inclinacao"
                      ? "border-l-2 pl-3"
                      : ""
                    : "border-l border-[var(--filete)] pl-3"
                } ${puxouParaBaixo ? "font-medium" : ""}`}
                style={
                  doCliente && marca && marca.sentido !== "sem_inclinacao"
                    ? { borderColor: COR_SENTIDO[marca.sentido] }
                    : undefined
                }
              >
                {mensagem.texto}
              </p>

              {latencia !== undefined ? (
                <p className="mt-1.5 flex items-center gap-1.5">
                  <span
                    aria-hidden
                    className="inline-block h-[6px] w-[6px] rounded-full"
                    style={{
                      background: COR_SEVERIDADE[severidadeLatencia(latencia)],
                    }}
                    title={ROTULO_LATENCIA[severidadeLatencia(latencia)].detalhe}
                  />
                  <span className="font-mono text-[0.6875rem] tabular-nums text-[var(--tinta-2)]">
                    {formatarSegundos(latencia)}
                  </span>
                  <span className="text-[0.6875rem] text-[var(--tinta-3)]">
                    de espera do cliente até esta resposta
                  </span>
                </p>
              ) : null}

              {marca ? (
                <div className="mt-2 flex flex-col gap-1">
                  <p className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span className="inline-flex items-baseline gap-1.5 text-[0.75rem] font-medium text-[var(--tinta)]">
                      <span
                        aria-hidden
                        className="inline-block h-[7px] w-[7px] translate-y-[-1px] rounded-full"
                        style={{ background: COR_SENTIDO[marca.sentido] }}
                      />
                      {ROTULO_SENTIDO[marca.sentido]}
                    </span>
                    <span className="text-[0.75rem] text-[var(--tinta-2)]">
                      {porcentagem(marca.probabilidade)} de{" "}
                      {ROTULO_CLASSE[marca.classe]} no classificador de texto
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
 * (0 insatisfeito, 1 neutro, 2 satisfeito). E a leitura mais rapida possivel
 * de "o quanto o modelo esta convencido": a largura E a probabilidade.
 */
function BarraProbabilidade({ marca }: { marca: MarcaAtribuicao }) {
  const faixas = [
    {
      chave: "insatisfeito",
      valor: marca.probInsatisfeito,
      cor: "var(--detrator)",
    },
    { chave: "neutro", valor: marca.probNeutro, cor: "var(--neutro)" },
    {
      chave: "satisfeito",
      valor: marca.probSatisfeito,
      cor: "var(--promotor)",
    },
  ];

  return (
    <span
      className="flex h-[4px] w-full max-w-[22rem] overflow-hidden rounded-[2px] bg-[var(--filete)]"
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
          style={{
            width: `${faixa.valor * 100}%`,
            background: faixa.cor,
          }}
        />
      ))}
    </span>
  );
}
