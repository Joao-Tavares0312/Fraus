import type { PesoDaFeature } from "@/lib/derivacoes";
import { ROTULO_SINAL } from "@/lib/derivacoes";
import { cn } from "@/lib/utils";

/**
 * Cor por TIPO DE SINAL, para os pesos globais.
 *
 * A metafora do produto encaixa direto: o sinal de texto e de emoji sao o que
 * foi DITO (ambar, dois pesos da mesma familia), e o de tempo e o `--tempo`.
 * Emocao, lexico e estilo entraram no vetor em 21/08/2026 e ganharam cor
 * propria (nenhuma reciclada) para nao se misturarem visualmente com as tres
 * famílias antigas. "outros" e o balde explicito de prefixo desconhecido --
 * nunca deve aparecer com fusor treinado sobre `NOMES_FEATURES`, mas existe
 * para nao herdar a cor de uma familia real se o contrato do backend mudar de
 * novo. Nenhum deles e lime -- a marca nao entra em dado.
 *
 * A ironia SAIU do vetor em 04/09/2026 (medida no corpus de treino, a cabeca
 * funciona como detector de sentimento positivo, nao de ironia -- ver
 * docs/handoff.md). A entrada abaixo fica morta para dado real: nenhuma
 * feature `ironia_*` sai mais de `NOMES_FEATURES`, entao `feature.sinal`
 * nunca chega como "ironia" vindo do backend. Mantida porque `SinalDaFeature`,
 * em `lib/derivacoes.ts`, ainda declara "ironia" como valor valido do tipo
 * (o mapa de prefixo->familia e compartilhado com outras leituras que
 * precisam da cabeca por mensagem) -- apagar so aqui trocaria um lookup
 * tipado por um `undefined` silencioso se algum caller passar esse sinal.
 */
const COR_DO_SINAL: Record<string, string> = {
  texto: "var(--dito)",
  emoji: "var(--medido)",
  tempo: "var(--tempo)",
  emocao: "var(--emocao)",
  lexico: "var(--lexico)",
  ironia: "var(--ironia)", // morta para dado real -- ver nota acima
  estilo: "var(--estilo)",
  outros: "var(--outros-sinal)",
};

const TEXTO_DO_SINAL: Record<string, string> = {
  texto: "text-dito-texto",
  emoji: "text-medido-texto",
  tempo: "text-tempo-texto",
  emocao: "text-emocao-texto",
  lexico: "text-lexico-texto",
  ironia: "text-ironia-texto", // morta para dado real -- ver nota em COR_DO_SINAL
  estilo: "text-estilo-texto",
  outros: "text-outros-sinal-texto",
};

/**
 * Barras de peso de feature em DOIS modos, e a diferenca entre eles e a
 * distincao que o produto nao pode errar:
 *
 *   `modo="global"`      -> `importancias`: peso do MODELO, sempre positivo,
 *                           colorido pela familia de sinal (as sete do vetor:
 *                           texto, emoji, tempo, emocao, lexico, estilo,
 *                           incongruencia -- a ironia NAO esta entre elas
 *                           desde 04/09/2026, ver nota em COR_DO_SINAL).
 *   `modo="divergente"`  -> `contribuicoes`: o que pesou NAQUELE atendimento,
 *                           COM SINAL, saindo de um eixo central — positivo
 *                           para a direita (empurrou a nota para cima),
 *                           negativo para a esquerda.
 *
 * As duas geometrias sao deliberadamente diferentes: barra que cresce da
 * esquerda nunca e confundida com barra que cresce de um centro, mesmo de
 * relance. O rotulo textual de cada barra reforca, porque cor e forma tambem
 * nao podem ser o unico canal.
 */
export function BarrasDeFeature({
  features,
  modo,
  formatarValor,
}: {
  features: PesoDaFeature[];
  modo: "global" | "divergente";
  formatarValor: (valor: number) => string;
}) {
  return (
    <ul className="flex flex-col gap-2">
      {features.map((feature) => (
        <li
          key={feature.nome}
          className="grid grid-cols-[minmax(0,11rem)_1fr_auto] items-center gap-3"
        >
          <span
            className="truncate text-xs text-foreground"
            title={feature.nome}
          >
            {feature.rotulo}
          </span>

          {modo === "global" ? (
            <span className="h-2 w-full overflow-hidden rounded-sm bg-muted">
              <span
                className="block h-full rounded-sm"
                style={{
                  width: `${Math.max(2, feature.fracao * 100)}%`,
                  background: COR_DO_SINAL[feature.sinal],
                }}
              />
            </span>
          ) : (
            <span className="relative flex h-2 w-full items-center rounded-sm bg-muted">
              {/* eixo zero, sempre visivel: e ele que da sentido ao sinal */}
              <span
                aria-hidden
                className="absolute inset-y-[-3px] left-1/2 w-px -translate-x-1/2 bg-border"
              />
              <span
                className="absolute inset-y-0 rounded-sm"
                style={
                  feature.valor >= 0
                    ? {
                        left: "50%",
                        width: `${Math.max(1, (feature.fracao * 100) / 2)}%`,
                        background: "var(--promotor)",
                      }
                    : {
                        right: "50%",
                        width: `${Math.max(1, (feature.fracao * 100) / 2)}%`,
                        background: "var(--detrator)",
                      }
                }
              />
            </span>
          )}

          <span
            className={cn(
              "num w-16 shrink-0 text-right text-xs",
              modo === "global"
                ? TEXTO_DO_SINAL[feature.sinal]
                : feature.valor >= 0
                  ? "text-promotor-texto"
                  : "text-detrator-texto",
            )}
          >
            {formatarValor(feature.valor)}
          </span>

          <span className="sr-only">
            {modo === "global"
              ? `sinal de ${ROTULO_SINAL[feature.sinal].toLowerCase()}`
              : feature.valor >= 0
                ? "empurrou a nota para cima"
                : "puxou a nota para baixo"}
          </span>
        </li>
      ))}
    </ul>
  );
}
