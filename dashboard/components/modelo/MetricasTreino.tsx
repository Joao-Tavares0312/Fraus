import type { MetricasTreino as Metricas } from "@/lib/api";
import { formatarNumero } from "@/lib/formato";
import { EstadoVazio } from "@/components/EstadoVazio";

/**
 * As duas metricas conhecidas, com o rotulo e o nome tecnico do campo.
 * Qualquer outra chave que o notebook exporte aparece na lista generica -- e
 * melhor mostrar o que veio do que esconder atras de um mapa fechado.
 */
const CONHECIDAS: { chave: string; rotulo: string; explicacao: string }[] = [
  {
    chave: "acuracia",
    rotulo: "Acurácia",
    explicacao: "proporção de predições corretas no conjunto de teste",
  },
  {
    chave: "f1_macro",
    rotulo: "F1-macro",
    explicacao:
      "média não ponderada do F1 das três classes — a classe rara pesa igual",
  },
];

function comoFracao(valor: unknown): number | null {
  if (typeof valor !== "number" || !Number.isFinite(valor)) return null;
  return valor;
}

/**
 * Metricas do treino.
 *
 * Quando `metricas` vem `null` a tela mostra ESTADO VAZIO HONESTO, nunca zero:
 * "acurácia 0%" e um modelo que erra tudo, e "modelo ainda não treinado" e
 * outra coisa completamente diferente. O estado vazio nomeia o que falta -- o
 * notebook que exporta `modelos/metricas.json` -- porque estado vazio que nao
 * diz o proximo passo e so um buraco.
 */
export function MetricasTreino({ metricas }: { metricas: Metricas | null }) {
  if (metricas === null) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="O modelo ainda não foi treinado"
        explicacao="GET /modelo respondeu metricas: null, que é o valor correto antes do treino — o servidor não inventa número. Assim que os notebooks rodarem no Colab e exportarem modelos/metricas.json, acurácia e F1-macro aparecem aqui. Zero não é resposta: seria dizer que o modelo erra tudo, quando ele nem existe."
        etapa="notebooks/01 (BERTimbau) e notebooks/02 (fusor), descritos em docs/treinamento.md"
      />
    );
  }

  const extras = Object.entries(metricas).filter(
    ([chave]) => !CONHECIDAS.some((conhecida) => conhecida.chave === chave),
  );

  return (
    <div className="flex flex-col gap-4 px-5 py-4">
      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {CONHECIDAS.map(({ chave, rotulo, explicacao }) => {
          const valor = comoFracao(metricas[chave]);
          return (
            <div
              key={chave}
              className="flex flex-col gap-1 rounded-lg bg-muted/40 px-4 py-3"
            >
              <dt className="text-xs font-medium text-muted-foreground">
                {rotulo}
              </dt>
              <dd className="num text-[1.75rem] leading-none font-semibold text-foreground">
                {valor === null ? (
                  <span className="text-lg font-medium text-muted-foreground">
                    não exportada
                  </span>
                ) : (
                  // A metrica pode vir em [0,1] ou ja em pontos percentuais;
                  // normalizar aqui evita "0,87%" onde deveria ser "87%".
                  `${formatarNumero(valor <= 1 ? valor * 100 : valor)}%`
                )}
              </dd>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {explicacao} · campo <code className="num">{chave}</code>
              </p>
            </div>
          );
        })}
      </dl>

      {extras.length > 0 ? (
        <div>
          <h3 className="text-xs font-medium text-muted-foreground">
            Outros campos exportados pelo notebook
          </h3>
          <ul className="num mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            {extras.map(([chave, valor]) => (
              <li key={chave}>
                {chave}: <span className="text-foreground">{String(valor)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
