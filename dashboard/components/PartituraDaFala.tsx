import type { CSSProperties, ReactNode } from "react";
import {
  ORDEM_CLASSES,
  disputaDasClasses,
  formatarProbabilidade as formatar,
  separarEmocoes,
  type Classe,
  type ProbabilidadesDeClasse,
} from "@/lib/partitura";

/**
 * A PARTITURA DA FALA: classe, emocao e ironia de uma frase numa pauta so.
 *
 * Desenho aprovado em 15/09/2026 (direcao "C1 + C2" da comparacao). A tese e
 * a mesma da interface inteira: UMA regua. As tres leituras ficam no mesmo
 * eixo 0-1, uma linha cada, entao a ironia de 0,97 se compara com a alegria
 * de 0,58 sem trocar de escala -- a escala relativa a maior emocao, que era a
 * de antes, fazia 0,58 e 0,97 parecerem do mesmo tamanho.
 *
 * A FORMA DA NOTA DIZ DE ONDE VEM A LEITURA, nunca a opacidade (opacidade
 * derrubou o contraste abaixo de AA sobre o vidro, medido em 14/09/2026):
 *   cheia     -> cabeca treinada, ou a classe vencedora
 *   vazada    -> classe que perdeu, ou o desprezo derivado
 *   tracejada -> a ironia, cabeca pouco confiavel
 *
 * A DISPUTA: quando a 1a e a 2a classe ficam a menos de `LIMIAR_DISPUTA`, um
 * colchete mede a distancia entre as duas notas. E distancia, nao confianca.
 *
 * Esta pauta continua SEPARADA da nota da conversa: ela e a leitura desta
 * frase, e quem pesa na nota e a media da conversa (ver `CabecasDeLeitura`).
 */

const COR_CLASSE: Record<Classe, string> = {
  insatisfeito: "var(--detrator)",
  neutro: "var(--neutro)",
  satisfeito: "var(--promotor)",
};

type Forma = "cheia" | "vazada" | "tracejada";

/** O trilho 0-1 de uma linha. Decorativo: o valor sai em texto ao lado. */
function Trilho({
  valor,
  forma,
  cor,
  corte = false,
  colchete,
}: {
  valor: number;
  forma: Forma;
  cor: string;
  corte?: boolean;
  colchete?: { de: number; ate: number };
}) {
  const posicao = `${Math.min(Math.max(valor, 0), 1) * 100}%`;
  const nota: CSSProperties =
    forma === "cheia"
      ? { left: posicao, background: cor }
      : { left: posicao, borderColor: cor, borderStyle: forma === "tracejada" ? "dashed" : "solid" };
  return (
    <span aria-hidden className="relative block h-5 min-w-0">
      <span className="absolute inset-0 flex justify-between">
        {[0, 1, 2, 3, 4].map((grade) => (
          <i key={grade} className="w-px bg-compasso" />
        ))}
      </span>
      <span className="absolute inset-x-0 top-1/2 h-px bg-compasso" />
      {corte ? (
        <span className="absolute top-0.5 bottom-0.5 left-1/2 w-px border-l border-dashed border-muted-foreground" />
      ) : null}
      {colchete ? (
        <span
          className="absolute top-1/2 h-3 min-w-1 -translate-y-1/2 border-x-2 border-warning-rich-text after:absolute after:inset-x-0 after:top-1/2 after:h-px after:bg-warning-rich-text"
          style={{ left: `${colchete.de * 100}%`, width: `${(colchete.ate - colchete.de) * 100}%` }}
        />
      ) : null}
      <span className="absolute top-1/2 left-0 h-px" style={{ width: posicao, background: cor }} />
      <span
        className={
          forma === "cheia"
            ? "absolute top-1/2 size-[9px] -translate-x-1/2 -translate-y-1/2 rounded-full"
            : `absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border-[1.5px] bg-card ${
                forma === "tracejada" ? "size-[11px]" : "size-[9px]"
              }`
        }
        style={nota}
      />
    </span>
  );
}

function Linha({
  nome,
  valor,
  forma,
  cor = "var(--medido)",
  forte = false,
  fraco = false,
  corte,
  colchete,
  titulo,
  italico = false,
}: {
  nome: string;
  valor: number;
  forma: Forma;
  cor?: string;
  forte?: boolean;
  fraco?: boolean;
  corte?: boolean;
  colchete?: { de: number; ate: number };
  titulo?: string;
  italico?: boolean;
}) {
  return (
    <>
      <span
        title={titulo}
        className={`truncate text-right text-xs ${forte ? "font-medium text-foreground" : "text-muted-foreground"} ${italico ? "italic" : ""}`}
      >
        {nome}
      </span>
      <Trilho valor={valor} forma={forma} cor={cor} corte={corte} colchete={colchete} />
      <span className={`num text-right text-xs ${fraco ? "text-muted-foreground" : "text-foreground"}`}>
        {formatar(valor)}
      </span>
    </>
  );
}

function Grupo({ rotulo, extra }: { rotulo: string; extra?: ReactNode }) {
  return (
    <div className="col-span-3 mt-2 grid grid-cols-subgrid items-end first:mt-0">
      <span className="text-right font-mono text-[0.6875rem] uppercase tracking-widest text-muted-foreground">
        {rotulo}
      </span>
      <span className="col-start-2 row-start-1 border-t border-linha" />
      {extra ? (
        <span className="col-span-2 col-start-2 row-start-1 justify-self-end pb-0.5 text-[0.6875rem] whitespace-nowrap">
          {extra}
        </span>
      ) : null}
    </div>
  );
}

export function PartituraDaFala({
  classes,
  emocao,
  ironia,
}: {
  /** As três probabilidades juntas, ou nenhuma — nunca `?? 0` (invariante 2). */
  classes: ProbabilidadesDeClasse | null;
  emocao: Record<string, number> | null;
  ironia: number | null;
}) {
  if (!classes && !emocao && ironia === null) return null;

  const disputa = classes ? disputaDasClasses(classes) : null;
  const emocoes = emocao ? separarEmocoes(emocao) : null;
  const temRecolhido = emocoes !== null && (emocoes.recolhidas.length > 0 || emocoes.desprezo !== null);

  return (
    <div
      role="group"
      aria-label="leitura por frase: classe, emoção e ironia na mesma escala de 0 a 1"
      className="grid grid-cols-[9.5ch_minmax(0,1fr)_4.5ch] items-center gap-x-2.5"
    >
      {classes && disputa ? (
        <>
          <Grupo
            rotulo="classe"
            extra={
              <span className={`num ${disputa.disputa ? "text-warning-rich-text" : "text-muted-foreground"}`}>
                Δ {formatar(disputa.margem)}
                {disputa.disputa ? " · disputa" : ""}
              </span>
            }
          />
          {ORDEM_CLASSES.map((nome) => {
            const venceu = nome === disputa.vencedora;
            return (
              <Linha
                key={nome}
                nome={nome}
                valor={classes[nome]}
                forma={venceu ? "cheia" : "vazada"}
                cor={COR_CLASSE[nome]}
                forte={venceu}
                fraco={!venceu}
                colchete={
                  venceu && disputa.disputa
                    ? { de: classes[disputa.segunda], ate: classes[nome] }
                    : undefined
                }
              />
            );
          })}
        </>
      ) : null}

      {emocoes && emocoes.visiveis.length > 0 ? (
        <>
          <Grupo rotulo="emoção" extra={<span className="text-muted-foreground">2 maiores</span>} />
          {emocoes.visiveis.map(([nome, valor]) => (
            <Linha key={nome} nome={nome} valor={valor} forma="cheia" fraco={valor < 0.1} />
          ))}
        </>
      ) : null}

      {ironia !== null ? (
        <>
          <Grupo rotulo="ironia" />
          <Linha
            nome="ironia"
            valor={ironia}
            forma="tracejada"
            cor="var(--medido-texto)"
            corte
            titulo="cabeça pouco confiável"
          />
        </>
      ) : null}

      <span />
      <span aria-hidden className="num flex justify-between pt-1 text-[0.6875rem] text-muted-foreground">
        <span>0</span>
        <span>,25</span>
        <span>,50</span>
        <span>,75</span>
        <span>1</span>
      </span>
      <span />

      {temRecolhido && emocoes ? (
        <details className="group/resto col-span-3">
          <summary className="cursor-pointer list-none pt-1 pb-0.5 pl-[calc(9.5ch+0.625rem)] text-xs text-muted-foreground marker:content-none hover:text-foreground [&::-webkit-details-marker]:hidden">
            <span className="num group-open/resto:hidden">+ </span>
            <span className="num hidden group-open/resto:inline">− </span>
            mais {emocoes.recolhidas.length} emoções
            {emocoes.desprezo !== null ? " e o desprezo" : ""}
          </summary>
          <div className="mt-0.5 grid grid-cols-[9.5ch_minmax(0,1fr)_4.5ch] items-center gap-x-2.5">
            {emocoes.recolhidas.map(([nome, valor]) => (
              <Linha key={nome} nome={nome} valor={valor} forma="cheia" fraco={valor < 0.1} />
            ))}
            {emocoes.desprezo !== null ? (
              <Linha
                nome="desprezo"
                valor={emocoes.desprezo}
                forma="vazada"
                fraco
                italico
                titulo="derivado de raiva + nojo; não é classe treinada"
              />
            ) : null}
          </div>
        </details>
      ) : null}
    </div>
  );
}
