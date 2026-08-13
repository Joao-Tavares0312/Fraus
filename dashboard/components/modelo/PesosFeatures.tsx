import { agruparPorSinal, ROTULO_SINAL, pesoPorSinal } from "@/lib/derivacoes";
import { formatarNumero } from "@/lib/formato";
import { BarrasDeFeature } from "@/components/BarrasDeFeature";
import { EstadoVazio } from "@/components/EstadoVazio";

const COR_DO_SINAL: Record<string, string> = {
  texto: "var(--dito)",
  emoji: "var(--medido)",
  tempo: "var(--tempo)",
};

const EXPLICACAO_DO_SINAL: Record<string, string> = {
  texto: "BERTimbau, probabilidade por mensagem do cliente",
  emoji: "lexicon do Emoji Sentiment Ranking + posição relativa no texto",
  tempo: "latência, escalação e abandono, derivados dos timestamps",
};

/**
 * As 16 features do fusor com o peso GLOBAL de cada uma, agrupadas pelos tres
 * sinais do trabalho.
 *
 * Este e o peso do MODELO: ele vale para todos os atendimentos e nao explica
 * nenhum em particular. Quem quer saber por que UM atendimento tirou aquela
 * nota abre o atendimento e le `contribuicoes`, que sai com sinal. A tela diz
 * isso em voz alta -- confundir os dois e o erro que derruba numa banca.
 *
 * Os pesos sao coeficientes absolutos da regressao logistica; e por isso que o
 * fusor e linear -- a pergunta "qual sinal pesou mais" so tem resposta em
 * modelo cujos coeficientes significam alguma coisa.
 */
export function PesosFeatures({
  importancias,
}: {
  importancias: Record<string, number>;
}) {
  const grupos = agruparPorSinal(importancias);
  const total = Object.keys(importancias).length;

  if (total === 0) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="O modelo não devolveu pesos"
        explicacao="GET /modelo respondeu com o mapa de importâncias vazio. Sem fusor treinado não há coeficiente a exibir, e desenhar 16 barras iguais seria inventar um modelo."
        etapa="notebook 02 (treino do fusor)"
      />
    );
  }

  const porSinal = pesoPorSinal(importancias);

  return (
    <div className="flex flex-col gap-5 px-5 py-4">
      <ul className="flex flex-wrap gap-x-6 gap-y-2">
        {porSinal.map((peso) => (
          <li key={peso.sinal} className="flex items-baseline gap-2 text-xs">
            <span
              aria-hidden
              className="size-2 shrink-0 translate-y-px rounded-full"
              style={{ background: COR_DO_SINAL[peso.sinal] }}
            />
            <span className="font-medium text-foreground">
              {ROTULO_SINAL[peso.sinal]}
            </span>
            <span className="num text-muted-foreground">
              {Math.round(peso.fracao * 100)}% do peso total
            </span>
          </li>
        ))}
      </ul>

      {grupos.map((grupo) =>
        grupo.features.length === 0 ? null : (
          <section key={grupo.sinal} className="flex flex-col gap-2">
            <h3 className="flex flex-wrap items-baseline gap-2 text-xs font-semibold text-foreground">
              <span
                aria-hidden
                className="size-2 shrink-0 translate-y-px rounded-full"
                style={{ background: COR_DO_SINAL[grupo.sinal] }}
              />
              Sinal de {ROTULO_SINAL[grupo.sinal].toLowerCase()}
              <span className="font-normal text-muted-foreground">
                {EXPLICACAO_DO_SINAL[grupo.sinal]}
              </span>
            </h3>
            <BarrasDeFeature
              features={grupo.features}
              modo="global"
              formatarValor={(valor) => formatarNumero(Math.abs(valor), 3)}
            />
          </section>
        ),
      )}
    </div>
  );
}
