import type { Categoria } from "@/lib/api";
import { ROTULO_CATEGORIA, ROTULO_SEM_SINAL } from "@/lib/formato";
import { cn } from "@/lib/utils";
import { CabecaVazada } from "./CabecaVazada";

/**
 * Categoria de NPS como etiqueta.
 *
 * Cor NUNCA e o unico canal: o rotulo textual esta sempre escrito, e o ponto
 * colorido apenas reforca. A cor de TEXTO usa a variante `-texto` do token --
 * cor de marcacao e cor de tipo nao sao a mesma coisa, e so a variante cruza
 * 4.5:1 contra `--card`.
 *
 * `categoria: null` NAO cai numa quarta cor da escala de satisfacao: vira
 * `CabecaVazada` -- anel oco, nunca um quarto ponto cheio. Um ponto CHEIO
 * cinza, no mesmo slot dos tres pontos cheios coloridos, seria "cinza dentro
 * da escala" (DESIGN.md §5) -- exatamente o que a §1.1 probe.
 *
 * `comRotulo={false}`: esta etiqueta ja escreve `ROTULO_SEM_SINAL` por
 * extenso logo depois do anel (linha de baixo), entao a `CabecaVazada` NAO
 * imprime o proprio rotulo -- se imprimisse, o leitor de tela leria "sem
 * sinal, sem sinal". O rotulo textual continua existindo e continua na
 * arvore de acessibilidade; so quem o escreve mudou.
 */
const APARENCIA: Record<
  Categoria,
  { ponto: string; borda: string; texto: string }
> = {
  detrator: {
    ponto: "bg-detrator",
    borda: "border-detrator",
    texto: "text-detrator-texto",
  },
  neutro: { ponto: "bg-neutro", borda: "border-neutro", texto: "text-neutro-texto" },
  promotor: {
    ponto: "bg-promotor",
    borda: "border-promotor",
    texto: "text-promotor-texto",
  },
};

/**
 * A TERCEIRA FORMA entra aqui, e nao num componente irmao, porque este e o
 * slot UNICO da cabeca: tabela, piores atendimentos, ficha do grafo e tela do
 * atendimento passam todos por ele. Um componente separado que quem chama
 * escolhesse daria tres formas em quatro lugares -- e a que ninguem lembrasse
 * de trocar seria a que continuaria mentindo confianca.
 *
 *   cheia      medido, com evidencia          -> ponto colorido cheio
 *   tracejada  medido, evidencia FRACA        -> anel tracejado na cor da classe
 *   vazada     nao medido                     -> anel oco, cinza
 *
 * `evidenciaFraca` vem do SERVIDOR (`fraus/evidencia.py`), derivada de fala
 * observavel -- quantas mensagens, quantas palavras -- e NUNCA da
 * probabilidade do modelo: probabilidade nao calibrada nao e confianca, e
 * chamar de confianca prometeria uma calibracao que este projeto nao tem.
 *
 * A tracejada mantem a COR DA CLASSE: a categoria continua valendo, e o que
 * esta em duvida e o quanto de fala a sustenta. Trocar por cinza a jogaria
 * para fora da escala, que e o significado reservado a ausencia.
 */
export function EtiquetaCategoria({
  categoria,
  evidenciaFraca = false,
  motivosEvidencia = [],
  className,
}: {
  categoria: Categoria | null;
  /** Derivado no servidor. Ignorado quando não há categoria: "sem sinal" tem forma própria. */
  evidenciaFraca?: boolean | null;
  motivosEvidencia?: string[];
  className?: string;
}) {
  const aparencia = categoria ? APARENCIA[categoria] : null;
  const tracejada = Boolean(aparencia && evidenciaFraca);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-sm whitespace-nowrap",
        aparencia ? aparencia.texto : "text-muted-foreground",
        className,
      )}
    >
      {aparencia ? (
        <span
          aria-hidden
          className={cn(
            "size-2 shrink-0 rounded-full",
            tracejada
              ? cn("border border-dashed bg-transparent", aparencia.borda)
              : aparencia.ponto,
          )}
        />
      ) : (
        <CabecaVazada comRotulo={false} />
      )}
      {categoria ? ROTULO_CATEGORIA[categoria] : ROTULO_SEM_SINAL}
      {/* O motivo por extenso: forma sozinha obriga o leitor a conhecer a
          convencao, e "evidência fraca" solto nao aciona ninguem. Mesma regra
          que faz a `CabecaVazada` exigir rotulo. */}
      {tracejada ? (
        <span className="text-xs text-muted-foreground">
          {motivosEvidencia.length > 0
            ? `· evidência fraca: ${motivosEvidencia[0]}`
            : "· evidência fraca"}
        </span>
      ) : null}
    </span>
  );
}
