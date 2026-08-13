import type { DetalheConversa } from "@/lib/api";
import {
  evidenciasDaConversa,
  latenciasAnotadas,
  severidadeLatencia,
  type Evidencia,
} from "@/lib/derivacoes";
import { formatarHora, formatarSegundos, ROTULO_AUTOR } from "@/lib/formato";

const COR_SEVERIDADE = {
  boa: "var(--tinta-3)",
  atencao: "var(--neutro)",
  critica: "var(--detrator)",
} as const;

/**
 * Transcricao com as tres coisas que transformam "nota ruim" em "oportunidade
 * de melhoria":
 *
 *   1. cliente e bot visualmente distintos (superficie e alinhamento, nao cor
 *      decorativa) -- quem le precisa saber de quem e a fala sem procurar;
 *   2. a latencia anotada ao lado de CADA resposta, com a faixa de severidade
 *      da literatura de live chat;
 *   3. a marcacao dos trechos que puxaram a nota.
 *
 * A marcacao usa so evidencia OBSERVAVEL na transcricao (polaridade de emoji e
 * tempo de espera). A atribuicao por sentenca do classificador de texto nao
 * tem endpoint, entao ela nao e simulada aqui -- o painel de evidencias diz
 * isso explicitamente.
 */
export function Transcricao({ conversa }: { conversa: DetalheConversa }) {
  const latencias = new Map(
    latenciasAnotadas(conversa.mensagens).map((l) => [l.indice, l.segundos]),
  );
  const evidencias = evidenciasDaConversa(conversa);
  const porIndice = new Map<number, Evidencia[]>();
  for (const evidencia of evidencias) {
    porIndice.set(evidencia.indice, [
      ...(porIndice.get(evidencia.indice) ?? []),
      evidencia,
    ]);
  }

  return (
    <ol className="divide-y divide-[var(--filete)]">
      {conversa.mensagens.map((mensagem, indice) => {
        const doCliente = mensagem.autor === "cliente";
        const latencia = latencias.get(indice);
        const marcas = porIndice.get(indice) ?? [];
        const puxouParaBaixo = marcas.some(
          (marca) => marca.sentido === "puxou_para_baixo",
        );

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
                  doCliente ? "" : "border-l border-[var(--filete)] pl-3"
                } ${puxouParaBaixo ? "font-medium" : ""}`}
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
                  />
                  <span className="font-mono text-[0.6875rem] tabular-nums text-[var(--tinta-2)]">
                    {formatarSegundos(latencia)}
                  </span>
                  <span className="text-[0.6875rem] text-[var(--tinta-3)]">
                    de espera do cliente até esta resposta
                  </span>
                </p>
              ) : null}

              {marcas.length > 0 ? (
                <ul className="mt-2 flex flex-col gap-1.5">
                  {marcas.map((marca) => (
                    <li
                      key={`${marca.tipo}-${marca.rotulo}`}
                      className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5"
                    >
                      <span className="inline-flex items-baseline gap-1.5 text-[0.75rem] font-medium text-[var(--tinta)]">
                        <span
                          aria-hidden
                          className="inline-block h-[7px] w-[7px] translate-y-[-1px] rounded-full"
                          style={{
                            background:
                              marca.sentido === "puxou_para_baixo"
                                ? "var(--detrator)"
                                : "var(--promotor)",
                          }}
                        />
                        {marca.rotulo}
                      </span>
                      <span className="text-[0.75rem] text-[var(--tinta-2)]">
                        {marca.detalhe}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
