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
 * Contado na dashboard a partir das transcricoes do periodo: a API nao expoe
 * lexico por classe. O criterio de ordenacao NAO e frequencia bruta -- e
 * distincao: quanto o termo aparece mais nesta classe do que nas outras.
 * "obrigado" aparece em todo lugar e nao explica nada; e o termo que so
 * aparece entre detratores que vira oportunidade de melhoria.
 *
 * O termo do cliente e FALA, entao ele veste ambar (`--dito`). A polaridade
 * dos emojis vem do mesmo Emoji Sentiment Ranking do sinal de emoji do
 * backend, nao de um criterio inventado aqui.
 */
export function PainelLexico({ classes }: { classes: LexicoDaClasse[] }) {
  const temAlgo = classes.some(
    (classe) => classe.palavras.length > 0 || classe.emojis.length > 0,
  );

  if (!temAlgo) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="Sem vocabulário suficiente para comparar as classes"
        explicacao="Nenhum atendimento pontuado do período trouxe fala do cliente com palavras fora da lista de parada. O ranking é por distinção entre classes, então precisa de pelo menos duas classes povoadas."
        endpoint="GET /palavras-chave?de=&ate="
      />
    );
  }

  return (
    <div className="grid grid-cols-1 divide-y divide-border md:grid-cols-3 md:divide-x md:divide-y-0">
      {classes.map((classe) => (
        <div key={classe.categoria} className="flex flex-col gap-4 px-5 py-4">
          <div className="flex flex-wrap items-baseline gap-2">
            <span
              aria-hidden
              className="size-2 shrink-0 -translate-y-px rounded-full"
              style={{ background: COR[classe.categoria] }}
            />
            <h3 className="titulo-instrumento text-sm text-foreground">
              {ROTULO_CATEGORIA[classe.categoria]}
            </h3>
            <span className="num text-xs text-muted-foreground">
              {classe.atendimentos}{" "}
              {classe.atendimentos === 1 ? "atendimento" : "atendimentos"}
            </span>
          </div>

          <div>
            <h4 className="rotulo-instrumento mb-1">Palavras</h4>
            {classe.palavras.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                nenhuma palavra distintiva
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {classe.palavras.map((termo) => (
                  <li
                    key={termo.termo}
                    className="flex items-baseline justify-between gap-3 py-1"
                  >
                    <span className="truncate text-sm text-dito-texto">
                      {termo.termo}
                    </span>
                    <span className="num shrink-0 text-xs text-muted-foreground">
                      {termo.ocorrencias}×
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h4 className="rotulo-instrumento mb-1">Emojis</h4>
            {classe.emojis.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                nenhum emoji nesta classe
              </p>
            ) : (
              <ul className="flex flex-wrap gap-2 pt-1">
                {classe.emojis.map((termo) => {
                  const polaridade = polaridadeDoEmoji(termo.termo);
                  return (
                    <li
                      key={termo.termo}
                      title={`polaridade ${polaridade > 0 ? "+" : ""}${polaridade.toFixed(2)} no Emoji Sentiment Ranking`}
                      className="inline-flex items-center gap-1.5 rounded-sm border border-border px-2 py-1 text-xs text-muted-foreground"
                    >
                      <span aria-hidden className="text-base leading-none">
                        {termo.termo}
                      </span>
                      <span className="num">{termo.ocorrencias}×</span>
                      <span className="num text-[0.6875rem]">
                        {polaridade > 0 ? "+" : ""}
                        {polaridade.toFixed(2)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
