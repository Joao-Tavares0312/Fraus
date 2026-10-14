import type { Confianca, Resultado } from "@/lib/api";
import { EstadoVazio } from "./EstadoVazio";

/** Frase simples por criterio; o servidor decide QUAIS valem, aqui so se traduz. */
function frase(criterio: string, fora: string[] | null): string {
  switch (criterio) {
    case "conjunto_multiplo":
      return "a nota é compatível com mais de uma classe de satisfação";
    case "conjunto_vazio":
      return "a nota não se parece com nenhuma classe de satisfação calibrada";
    case "deriva":
      return `fora da faixa de treino em: ${(fora ?? []).join(", ")}`;
    default:
      return criterio;
  }
}

/**
 * Selo de confianca conformal do score gravado.
 *
 * Conjunto e abstencao chegam prontos do servidor (invariante 3); aqui so se
 * desenha. Abstencao informa, nao exclui: a conversa continua no NPS. Score
 * nulo nao desenha nada -- a tela ja diz "sem sinal" (invariante 2). Falha da
 * rota nunca afirma confianca.
 */
export function SeloConfianca({ resultado }: { resultado: Resultado<Confianca> }) {
  if (!resultado.ok) {
    if (resultado.status === 503) {
      return (
        <EstadoVazio
          titulo="Calibração conformal ainda não gerada para este modelo"
          explicacao={resultado.erro}
          endpoint="GET /conversas/{id}/confianca"
        />
      );
    }
    if (resultado.status === 409) {
      return (
        <EstadoVazio
          titulo="Confiança indisponível"
          explicacao="Esta conversa foi pontuada com outra régua; repontue para ver a confiança."
        />
      );
    }
    return (
      <EstadoVazio
        titulo="Confiança indisponível"
        explicacao={`A leitura de confiança falhou: ${resultado.erro}`}
        endpoint="GET /conversas/{id}/confianca"
      />
    );
  }

  const c = resultado.dado;
  if (c.score === null) return null;

  const percentual = Math.round(c.alvo * 100);

  return (
    <section
      aria-label="Confiança da leitura"
      className="flex flex-col gap-1.5 border border-border px-4 py-3"
    >
      {c.abstencao ? (
        <>
          <p className="text-sm font-medium text-foreground">
            Leitura sem confiança suficiente
          </p>
          <ul className="flex flex-col gap-0.5">
            {c.criterios.map((criterio) => (
              <li key={criterio} className="text-xs text-foreground">
                {frase(criterio, c.features_fora_da_faixa)}
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">Continua contando no NPS.</p>
        </>
      ) : (
        <>
          <p className="num text-xs text-foreground">
            Classe de satisfação compatível com esta nota (calibração de {percentual}%):{" "}
            {(c.rotulos_conjunto ?? []).join(", ")}
          </p>
          <p className="text-xs text-muted-foreground">
            É a classe do rótulo de treino (insatisfeito/neutro/satisfeito), não a categoria NPS.
          </p>
        </>
      )}
      {c.deriva_nao_avaliada ? (
        <p className="text-xs text-muted-foreground">
          deriva não avaliada nesta leitura (conversa longa)
        </p>
      ) : null}
      <p className="max-w-[70ch] text-xs text-muted-foreground">{c.garantia}</p>
    </section>
  );
}
