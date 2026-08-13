import { polaridadeDoEmoji, type LexicoDaClasse } from "@/lib/derivacoes";
import { ROTULO_CATEGORIA } from "@/lib/formato";
import { EstadoVazio } from "./EstadoVazio";

const COR: Record<string, string> = {
  detrator: "var(--detrator)",
  neutro: "var(--neutro)",
  promotor: "var(--promotor)",
};

/**
 * Palavras e emojis mais caracteristicos de cada classe.
 *
 * Isto e contado na dashboard a partir das transcricoes: a API nao expoe
 * lexico por classe. O criterio de ordenacao NAO e frequencia bruta -- e
 * distincao: quanto o termo aparece mais nesta classe do que nas outras.
 * "obrigado" aparece em todo lugar e nao explica nada; e o termo que so
 * aparece entre detratores que vira oportunidade de melhoria.
 *
 * A polaridade dos emojis vem do mesmo Emoji Sentiment Ranking que o sinal de
 * emoji do backend usa (exportado por `scripts/gerar_lexico_emoji.py`), e nao
 * de um criterio inventado aqui.
 */
export function PainelLexico({ classes }: { classes: LexicoDaClasse[] }) {
  const temAlgo = classes.some(
    (classe) => classe.palavras.length > 0 || classe.emojis.length > 0,
  );

  if (!temAlgo) {
    return (
      <EstadoVazio
        titulo="Sem vocabulário suficiente para comparar as classes"
        explicacao="Nenhum atendimento pontuado trouxe fala do cliente com palavras fora da lista de parada. O ranking é por distinção entre classes, então precisa de pelo menos duas classes povoadas."
        endpoint="GET /palavras-chave"
      />
    );
  }

  return (
    <div className="grid grid-cols-1 divide-y divide-[var(--filete)] md:grid-cols-3 md:divide-x md:divide-y-0">
      {classes.map((classe) => (
        <div key={classe.categoria} className="flex flex-col gap-4 px-5 py-4">
          <div className="flex items-baseline gap-2">
            <span
              aria-hidden
              className="h-[7px] w-[7px] shrink-0 translate-y-[-1px] rounded-full"
              style={{ background: COR[classe.categoria] }}
            />
            <h3 className="text-[0.875rem] font-semibold text-[var(--tinta)]">
              {ROTULO_CATEGORIA[classe.categoria]}
            </h3>
            <span className="text-[0.75rem] tabular-nums text-[var(--tinta-3)]">
              {classe.atendimentos}{" "}
              {classe.atendimentos === 1 ? "atendimento" : "atendimentos"}
            </span>
          </div>

          <Bloco titulo="Palavras" vazio="nenhuma palavra distintiva">
            {classe.palavras.map((termo) => (
              <li
                key={termo.termo}
                className="flex items-baseline justify-between gap-3 py-1"
              >
                <span className="truncate text-[0.8125rem] text-[var(--tinta)]">
                  {termo.termo}
                </span>
                <span className="shrink-0 text-[0.75rem] tabular-nums text-[var(--tinta-3)]">
                  {termo.ocorrencias}×
                </span>
              </li>
            ))}
          </Bloco>

          <Bloco titulo="Emojis" vazio="nenhum emoji nesta classe">
            {classe.emojis.length > 0 ? (
              <li className="flex flex-wrap gap-2 pt-1">
                {classe.emojis.map((termo) => {
                  const polaridade = polaridadeDoEmoji(termo.termo);
                  return (
                    <span
                      key={termo.termo}
                      title={`polaridade ${polaridade > 0 ? "+" : ""}${polaridade.toFixed(2)} no Emoji Sentiment Ranking`}
                      className="inline-flex items-center gap-1.5 border border-[var(--filete)] px-2 py-1 text-[0.8125rem] text-[var(--tinta-2)]"
                    >
                      <span aria-hidden className="text-[1rem] leading-none">
                        {termo.termo}
                      </span>
                      <span className="tabular-nums text-[0.75rem]">
                        {termo.ocorrencias}×
                      </span>
                      <span className="tabular-nums text-[0.6875rem] text-[var(--tinta-3)]">
                        {polaridade > 0 ? "+" : ""}
                        {polaridade.toFixed(2)}
                      </span>
                    </span>
                  );
                })}
              </li>
            ) : null}
          </Bloco>
        </div>
      ))}
    </div>
  );
}

function Bloco({
  titulo,
  vazio,
  children,
}: {
  titulo: string;
  vazio: string;
  children: React.ReactNode;
}) {
  const vazioDeFato =
    !children || (Array.isArray(children) && children.length === 0);

  return (
    <div>
      <h4 className="mb-1 text-[0.6875rem] font-medium text-[var(--tinta-3)]">
        {titulo}
      </h4>
      {vazioDeFato ? (
        <p className="text-[0.8125rem] text-[var(--tinta-3)]">{vazio}</p>
      ) : (
        <ul className="divide-y divide-[var(--filete)]">{children}</ul>
      )}
    </div>
  );
}
