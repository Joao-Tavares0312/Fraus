import type { CSSProperties, ReactNode } from "react";
import {
  ORDEM_CLASSES,
  disputaDasClasses,
  emocoesPorValor,
  formatarProbabilidade as formatar,
  type Classe,
  type ProbabilidadesDeClasse,
} from "@/lib/partitura";

/**
 * A LEITURA DA FALA: tres graficos, um por pergunta.
 *
 * Substitui a pauta unica (`PartituraDaFala`, 15/09/2026) em 13/11/2026. A
 * pauta punha classe, emocao e ironia em dez linhas iguais na mesma regua, e
 * o defeito que o Joao apontou era exatamente esse: tres perguntas de natureza
 * diferente disputando a mesma forma. Agora cada uma tem a sua:
 *
 *   satisfacao -> tres classes EM ORDEM que somam 1: uma faixa dividida
 *   emocao     -> sete categorias sem ordem: linha com a nota na regua 0-1,
 *                 da maior para a menor
 *   ironia     -> um numero so: um medidor, com a marca do meio
 *
 * Cada grafico abre com o veredito em texto; o desenho so confirma.
 *
 * O QUE NAO MUDOU, porque nasceu de defeito medido:
 * - a FORMA diz de onde vem a leitura, nunca a opacidade (opacidade derrubou
 *   o contraste abaixo de AA em 14/09/2026): cheia = cabeca treinada, vazada =
 *   o desprezo derivado, tracejada = a ironia, cabeca pouco confiavel;
 * - a disputa e DISTANCIA entre duas probabilidades, nunca "confianca";
 * - ausencia nao vira zero (invariante 2): leitura que nao veio nao desenha
 *   grafico nenhum, e zero observado continua escrito como zero;
 * - nada e recalculado aqui alem de ordem e formato.
 *
 * Esta leitura continua SEPARADA da nota da conversa: e a leitura desta
 * frase, e quem pesa na nota e a media da conversa (ver `CabecasDeLeitura`).
 */

const COR_CLASSE: Record<Classe, string> = {
  insatisfeito: "var(--detrator)",
  neutro: "var(--neutro)",
  satisfeito: "var(--promotor)",
};
const TEXTO_CLASSE: Record<Classe, string> = {
  insatisfeito: "text-detrator-texto",
  neutro: "text-neutro-texto",
  satisfeito: "text-promotor-texto",
};

/**
 * Cor de cada emocao: so a MARCA (linha e nota), nunca o nome nem o numero.
 * Emocao que a API trouxer e nao estiver aqui cai no azul do medido, sem
 * inventar tom.
 */
const COR_EMOCAO: Record<string, string> = {
  medo: "var(--emo-medo)",
  nojo: "var(--emo-nojo)",
  tristeza: "var(--emo-tristeza)",
  raiva: "var(--emo-raiva)",
  surpresa: "var(--emo-surpresa)",
  alegria: "var(--emo-alegria)",
  neutro: "var(--emo-neutro)",
};
const corDaEmocao = (nome: string) => COR_EMOCAO[nome] ?? "var(--medido)";

const largura = (valor: number) => `${Math.min(Math.max(valor, 0), 1) * 100}%`;

/** A moldura comum: nome da pergunta, veredito em texto, e o grafico. */
function Grafico({
  rotulo,
  nome,
  veredito,
  apoio,
  children,
}: {
  rotulo: string;
  nome: string;
  veredito: ReactNode;
  apoio: ReactNode;
  children: ReactNode;
}) {
  return (
    <section role="group" aria-label={rotulo} className="flex min-w-0 flex-col gap-2">
      <div className="flex flex-col gap-0.5">
        <h4 className="text-xs font-normal text-muted-foreground">{nome}</h4>
        <p className="text-sm font-medium text-foreground">{veredito}</p>
        <p className="text-xs text-muted-foreground">{apoio}</p>
      </div>
      {children}
    </section>
  );
}

function Satisfacao({ classes }: { classes: ProbabilidadesDeClasse }) {
  const d = disputaDasClasses(classes);
  return (
    <Grafico
      rotulo="satisfação desta fala"
      nome="Satisfação"
      veredito={
        <>
          <span className={TEXTO_CLASSE[d.vencedora]}>{d.vencedora}</span>{" "}
          <span className="num font-normal">{formatar(classes[d.vencedora])}</span>
        </>
      }
      apoio={
        d.disputa ? (
          <>
            <span className="text-warning-rich-text">em disputa com {d.segunda}</span>{" "}
            <span className="num">Δ {formatar(d.margem)}</span>
          </>
        ) : (
          <>
            folga de <span className="num">{formatar(d.margem)}</span> sobre {d.segunda}
          </>
        )
      }
    >
      {/* A faixa e decorativa: os tres numeros saem escritos logo abaixo, na
          mesma ordem fixa (invariante 8). Fatia de zero observado nao ganha
          largura minima -- um fio ali se leria como "um pouco". */}
      <span aria-hidden className="flex h-6 gap-0.5">
        {ORDEM_CLASSES.map((nome) => (
          <span
            key={nome}
            className={`rounded-sm ${classes[nome] > 0 ? "min-w-0.5" : ""}`}
            style={{ flexGrow: classes[nome], flexBasis: 0, background: COR_CLASSE[nome] }}
          />
        ))}
      </span>
      <dl className="grid grid-cols-3 gap-x-2 text-xs">
        {ORDEM_CLASSES.map((nome, indice) => (
          <div
            key={nome}
            className={`flex min-w-0 flex-col ${indice === 1 ? "items-center" : indice === 2 ? "items-end" : ""}`}
          >
            <dt className={`truncate ${nome === d.vencedora ? "text-foreground" : "text-muted-foreground"}`}>{nome}</dt>
            <dd className={`num ${nome === d.vencedora ? "text-foreground" : "text-muted-foreground"}`}>
              {formatar(classes[nome])}
            </dd>
          </div>
        ))}
      </dl>
    </Grafico>
  );
}

/** A linha da regua 0-1 com a nota no valor. Decorativa: o numero sai ao lado. */
function Trilho({ valor, cor, vazada = false }: { valor: number; cor: string; vazada?: boolean }) {
  const posicao = largura(valor);
  const nota: CSSProperties = vazada ? { left: posicao, borderColor: cor } : { left: posicao, background: cor };
  return (
    <span aria-hidden className="relative block h-5 min-w-0">
      <span className="absolute inset-0 flex justify-between">
        {[0, 1, 2, 3, 4].map((grade) => (
          <i key={grade} className="w-px bg-compasso" />
        ))}
      </span>
      <span className="absolute inset-x-0 top-1/2 h-px bg-compasso" />
      <span className="absolute top-1/2 left-0 h-0.5 -translate-y-1/2" style={{ width: posicao, background: cor }} />
      <span
        className={`absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ${
          vazada ? "border-[1.5px] bg-card" : ""
        }`}
        style={nota}
      />
    </span>
  );
}

function LinhaDeEmocao({
  nome,
  valor,
  forte = false,
  derivado = false,
}: {
  nome: string;
  valor: number;
  forte?: boolean;
  derivado?: boolean;
}) {
  return (
    <>
      <span
        data-emocao={nome}
        title={derivado ? "derivado de raiva + nojo; não é classe treinada" : undefined}
        className={`truncate text-xs ${forte ? "font-medium text-foreground" : "text-muted-foreground"} ${
          derivado ? "italic" : ""
        }`}
      >
        {nome}
      </span>
      <Trilho valor={valor} cor={derivado ? "var(--emo-raiva)" : corDaEmocao(nome)} vazada={derivado} />
      <span className={`num text-right text-xs ${forte ? "text-foreground" : "text-muted-foreground"}`}>
        {formatar(valor)}
      </span>
    </>
  );
}

const GRADE_EMOCAO = "grid grid-cols-[8.5ch_minmax(0,1fr)_4ch] items-center gap-x-2.5";

function Emocao({ emocao, recolher }: { emocao: Record<string, number>; recolher: boolean }) {
  const { dominante, visiveis, recolhidas, desprezo } = emocoesPorValor(emocao, recolher ? undefined : Infinity);
  if (!dominante) return null;
  const desprezoAVista = !recolher && desprezo !== null;
  const temRecolhido = recolhidas.length > 0 || (recolher && desprezo !== null);
  const treinadas = visiveis.length + recolhidas.length;
  return (
    <Grafico
      rotulo="emoção desta fala"
      nome="Emoção"
      veredito={
        <>
          <span
            aria-hidden
            className="mr-1.5 inline-block size-2 rounded-full align-middle"
            style={{ background: corDaEmocao(dominante[0]) }}
          />
          {dominante[0]} <span className="num font-normal">{formatar(dominante[1])}</span>
        </>
      }
      apoio={
        <>
          a maior de {treinadas} {treinadas === 1 ? "classe" : "classes"}
        </>
      }
    >
      <div className={GRADE_EMOCAO}>
        {visiveis.map(([nome, valor], indice) => (
          <LinhaDeEmocao key={nome} nome={nome} valor={valor} forte={indice === 0} />
        ))}
        {desprezoAVista ? <LinhaDeEmocao nome="desprezo" valor={desprezo} derivado /> : null}
        <span />
        <span aria-hidden className="num flex justify-between pt-0.5 text-[0.6875rem] text-muted-foreground">
          <span>0</span>
          <span>,25</span>
          <span>,50</span>
          <span>,75</span>
          <span>1</span>
        </span>
        <span />
      </div>
      {desprezoAVista ? (
        <p className="text-[0.6875rem] text-muted-foreground">
          <span className="italic">desprezo</span>: derivado de raiva + nojo, não é classe treinada.
        </p>
      ) : null}
      {recolher && temRecolhido ? (
        <details className="group/resto">
          <summary className="cursor-pointer list-none text-xs text-muted-foreground marker:content-none hover:text-foreground [&::-webkit-details-marker]:hidden">
            <span className="num group-open/resto:hidden">+ </span>
            <span className="num hidden group-open/resto:inline">− </span>
            mais {recolhidas.length} {recolhidas.length === 1 ? "emoção" : "emoções"}
            {desprezo !== null ? " e o desprezo" : ""}
          </summary>
          <div className={`mt-1 ${GRADE_EMOCAO}`}>
            {recolhidas.map(([nome, valor]) => (
              <LinhaDeEmocao key={nome} nome={nome} valor={valor} />
            ))}
            {desprezo !== null ? <LinhaDeEmocao nome="desprezo" valor={desprezo} derivado /> : null}
          </div>
          {desprezo !== null ? (
            <p className="mt-1 text-[0.6875rem] text-muted-foreground">
              <span className="italic">desprezo</span>: derivado de raiva + nojo, não é classe treinada.
            </p>
          ) : null}
        </details>
      ) : null}
    </Grafico>
  );
}

/**
 * O meio da regua. NUMERO DE INTERFACE, nao limiar calibrado: e a marca que o
 * medidor desenha, e o texto so diz de que lado dela o numero caiu. "Sem
 * indicio" nao afirma que a fala e sincera -- a cabeca e pouco confiavel nos
 * dois sentidos, e a legenda diz isso sempre.
 */
const MEIO_DA_IRONIA = 0.5;

function Ironia({ ironia }: { ironia: number }) {
  return (
    <Grafico
      rotulo="ironia desta fala"
      nome="Ironia"
      veredito={
        <>
          {ironia >= MEIO_DA_IRONIA ? "indício de ironia" : "sem indício de ironia"}{" "}
          <span className="num font-normal">{formatar(ironia)}</span>
        </>
      }
      apoio="cabeça pouco confiável; leia como indício"
    >
      {/* Tracejado e hachura: a forma da cabeca pouco confiavel, a mesma da
          nota tracejada da pauta. Nunca opacidade. */}
      <span aria-hidden className="relative block h-6 overflow-hidden rounded-sm border-[1.5px] border-dashed border-medido">
        <span
          className="block h-full"
          style={{
            width: largura(ironia),
            background:
              "repeating-linear-gradient(115deg, color-mix(in oklab, var(--medido) 55%, var(--card)) 0 6px, color-mix(in oklab, var(--medido) 22%, var(--card)) 6px 12px)",
          }}
        />
        <span className="absolute inset-y-0 left-1/2 border-l-[1.5px] border-foreground" />
      </span>
      <span aria-hidden className="num flex justify-between text-[0.6875rem] text-muted-foreground">
        <span>0</span>
        <span>,50</span>
        <span>1</span>
      </span>
    </Grafico>
  );
}

export function LeituraDaFala({
  classes,
  emocao,
  ironia,
  recolher = true,
}: {
  /**
   * Recolher as emoções além das duas maiores. Verdadeiro onde a leitura se
   * repete por fala (Analisador); falso onde se examina UMA frase (Simulador),
   * e aí esconder emoção esconderia justamente o que se veio olhar.
   */
  recolher?: boolean;
  /** As três probabilidades juntas, ou nenhuma — nunca `?? 0` (invariante 2). */
  classes: ProbabilidadesDeClasse | null;
  emocao: Record<string, number> | null;
  ironia: number | null;
}) {
  if (!classes && !emocao && ironia === null) return null;
  return (
    <div className="grid gap-x-8 gap-y-5 [grid-template-columns:repeat(auto-fit,minmax(min(100%,14rem),1fr))]">
      {classes ? <Satisfacao classes={classes} /> : null}
      {emocao ? <Emocao emocao={emocao} recolher={recolher} /> : null}
      {ironia !== null ? <Ironia ironia={ironia} /> : null}
    </div>
  );
}
