import type { CabecaDeModelo, MetricasTreino as Metricas } from "@/lib/api";
import { formatarNumero } from "@/lib/formato";
import { EstadoVazio } from "@/components/EstadoVazio";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";

/**
 * Campos numericos que a tela sabe nomear.
 *
 * `f1_macro_xed_pt` e o mais importante da lista e o motivo de ela existir: e
 * o F1 da emocao num corpus que NAO passou por traducao automatica, e ele e
 * menos da metade do F1 no corpus de treino. Deixar esse numero cair na lista
 * generica de "outros campos" esconderia a unica medida honesta de quanto o
 * modelo de emocao generaliza.
 */
const NUMERICAS: Record<string, { rotulo: string; explicacao: string }> = {
  acuracia: {
    rotulo: "Acurácia",
    explicacao: "proporção de predições corretas no conjunto de teste",
  },
  f1_macro: {
    rotulo: "F1-macro",
    explicacao: "média não ponderada do F1 das classes — a classe rara pesa igual",
  },
  f1_macro_xed_pt: {
    rotulo: "F1-macro no XED-pt",
    explicacao:
      "corpus independente, em português europeu, SEM tradução automática — é o quanto o modelo generaliza fora do corpus que o treinou",
  },
  f1_ironico: {
    rotulo: "F1 da classe irônica",
    explicacao: "no mesmo corpus sintético que gerou o treino",
  },
  exemplos_treino: {
    rotulo: "Exemplos de treino",
    explicacao: "tamanho do corpus usado",
  },
};

/** Campos em prosa: procedência e ressalva. Vão inteiros, nunca resumidos. */
const TEXTUAIS: Record<string, string> = {
  corpus: "Corpus",
  corpus_treino: "Corpus de treino",
  corpus_teste_independente: "Corpus de teste independente",
  limitacao: "Limitação declarada",
  desprezo: "Sobre o desprezo",
  limiar_anotadores: "Limiar de anotadores",
  rotulo: "Rótulo",
};

const ROTULO_CABECA: Record<string, string> = {
  satisfacao: "Satisfação",
  emocao: "Emoção",
  ironia: "Ironia",
};

/**
 * Acima disto, uma metrica deixa de ser boa noticia e vira suspeita.
 *
 * Acuracia perfeita em tarefa de linguagem quase nunca significa modelo bom:
 * significa que o conjunto de teste parece demais com o de treino. E o caso da
 * cabeca de ironia, treinada em corpus GERADO -- ela reporta 1.0 e erra 6 em
 * 10 falas sinceras de atendimento. Exibir "100%" sem a ressalva colada seria
 * a mentira mais eficaz desta tela inteira.
 */
// Exportado: o veredito no topo da tela (`EstadoDoModelo.tsx`) precisa do
// mesmo corte para decidir se cola o rotulo "suspeito" no F1 da ironia --
// duplicar o numero literal ali criaria dois limiares que podem divergir.
export const LIMIAR_SUSPEITO = 0.999;

function comoFracao(valor: unknown): number | null {
  if (typeof valor !== "number" || !Number.isFinite(valor)) return null;
  return valor;
}

/** Metrica pode vir em [0,1] ou ja em pontos percentuais. */
function percentual(valor: number): string {
  return `${formatarNumero(valor <= 1 ? valor * 100 : valor)}%`;
}

export function MetricasTreino({
  metricas,
  cabecas,
}: {
  metricas: Metricas | null;
  cabecas?: CabecaDeModelo[];
}) {
  // A ficha antiga so conhecia a satisfacao. Se a API for de uma versao sem
  // `cabecas`, a tela continua mostrando o que sempre mostrou em vez de sumir.
  const lista: CabecaDeModelo[] =
    cabecas && cabecas.length > 0
      ? cabecas
      : [{ nome: "satisfacao", classes: [], metricas, pontua: true }];

  if (lista.every((cabeca) => cabeca.metricas === null)) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="Nenhuma cabeça foi treinada ainda"
        explicacao="GET /modelo respondeu metricas: null para todas, que é o valor correto antes do treino — o servidor não inventa número. Assim que os notebooks rodarem no Colab e exportarem os arquivos de métricas, acurácia e F1 aparecem aqui. Zero não é resposta: seria dizer que o modelo erra tudo, quando ele nem existe."
        etapa="notebooks/01 (satisfação), 03 (emoção) e 04 (ironia), descritos em docs/treinamento.md"
      />
    );
  }

  return (
    <div className="flex flex-col gap-5 px-5 py-4">
      {lista.map((cabeca) => (
        <Cabeca key={cabeca.nome} cabeca={cabeca} />
      ))}
    </div>
  );
}

function Cabeca({ cabeca }: { cabeca: CabecaDeModelo }) {
  const metricas = cabeca.metricas;
  const nome = ROTULO_CABECA[cabeca.nome] ?? cabeca.nome;

  const numericas = metricas
    ? Object.keys(NUMERICAS)
        .filter((chave) => comoFracao(metricas[chave]) !== null)
        .map((chave) => ({ chave, valor: comoFracao(metricas[chave])! }))
    : [];

  const textuais = metricas
    ? Object.keys(TEXTUAIS).filter(
        (chave) => typeof metricas[chave] === "string" || typeof metricas[chave] === "number",
      )
    : [];

  // Mesma normalizacao que `percentual` aplica para EXIBIR: o campo pode vir
  // em fracao [0,1] ou ja em pontos percentuais, e comparar o valor cru
  // contra LIMIAR_SUSPEITO (fracao) rotulava um resultado em pontos
  // percentuais baixo (ex.: 5.0 = 5%) como "suspeito" -- o mesmo bug corrigido
  // em EstadoDoModelo.tsx.
  const ehSuspeita = (chave: string, valor: number) => {
    if (chave === "exemplos_treino") return false;
    const fracao = valor <= 1 ? valor : valor / 100;
    return fracao >= LIMIAR_SUSPEITO;
  };

  const porClasse =
    metricas && metricas.f1_por_classe && typeof metricas.f1_por_classe === "object"
      ? Object.entries(metricas.f1_por_classe as Record<string, number>)
      : [];

  // Dispara para QUALQUER cabeca cuja metrica cruze LIMIAR_SUSPEITO -- nao so
  // ironia. Ate 04/09/2026 esta explicacao so existia cravada no veredito do
  // topo da tela (EstadoDoModelo.tsx), escrita em cima da ironia; se o
  // retreino exportar, por exemplo, acuracia 1.0 para a cabeca de TEXTO, o
  // rotulo "suspeito" aparece aqui sem nenhum lugar dizendo por que isso e
  // ma noticia. Recolher e permitido, remover nao -- por isso o paragrafo
  // volta a existir onde a suspeita de fato acontece: por metrica, por
  // cabeca.
  const temSuspeita = numericas.some(({ chave, valor }) => ehSuspeita(chave, valor));

  return (
    <section className="flex flex-col gap-3 border-t border-linha pt-4 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h3 className="titulo-instrumento text-sm text-foreground">{nome}</h3>
        {/* `pontua` NAO e unanime desde 04/09/2026: satisfacao e emocao valem
            `true`, ironia vale `false` -- ela continua carregada e lida por
            mensagem, mas saiu do vetor do fusor porque, medida no corpus de
            treino, funcionava como detector de sentimento positivo. Este campo
            existe exatamente para este caso: sem ele, tres cartoes iguais
            esconderiam a diferenca entre a cabeca que move a nota e a que so
            descreve. Ver `fraus/api/rotas/modelo.py` e `docs/treinamento.md`. */}
        <span className="text-xs text-muted-foreground">
          {cabeca.pontua
            ? "entra no fusor — é esta cabeça que move a nota"
            : "não entra no fusor — cabeça treinada, mas ainda não pontua"}
        </span>
        {cabeca.classes.length > 0 ? (
          <span className="num text-xs text-muted-foreground">
            {cabeca.classes.join(" · ")}
          </span>
        ) : null}
      </div>

      {metricas === null ? (
        <p className="text-xs text-muted-foreground">
          Ainda não treinada — <code className="num">metricas: null</code>, que é
          o valor correto antes do treino. Zero seria dizer que ela erra tudo.
        </p>
      ) : (
        <>
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {numericas.map(({ chave, valor }) => {
              const suspeita = ehSuspeita(chave, valor);
              return (
                <div
                  key={chave}
                  className="flex flex-col gap-1 border border-compasso px-4 py-3"
                >
                  <dt className="rotulo-instrumento">
                    {NUMERICAS[chave].rotulo}
                  </dt>
                  <dd className="flex items-end gap-2 leading-none text-foreground">
                    <SegmentoLED
                      valor={
                        chave === "exemplos_treino"
                          ? formatarNumero(valor, 0)
                          : formatarNumero(valor <= 1 ? valor * 100 : valor)
                      }
                      altura={30}
                      rotulo={
                        chave === "exemplos_treino"
                          ? NUMERICAS[chave].rotulo
                          : `${NUMERICAS[chave].rotulo}, em porcento`
                      }
                    />
                    {chave === "exemplos_treino" ? null : (
                      <span className="num text-sm text-muted-foreground">%</span>
                    )}
                    {suspeita ? (
                      <span className="text-xs font-normal text-warning-rich-text">
                        suspeito
                      </span>
                    ) : null}
                  </dd>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {NUMERICAS[chave].explicacao} · campo{" "}
                    <code className="num">{chave}</code>
                  </p>
                </div>
              );
            })}
          </dl>

          {temSuspeita ? (
            <p className="text-xs leading-relaxed text-warning-rich-text">
              Métrica perfeita em tarefa de linguagem quase nunca significa
              modelo bom — significa que o conjunto de teste se parece demais
              com o de treino.
              {/* "Leia a limitacao abaixo" so aparece quando `limitacao` de
                  fato vem em `metricas` -- ela nao e campo garantido pelo
                  contrato da API, e sem ela o texto apontaria para um trecho
                  que nao existe nesta tela. A frase de honestidade acima
                  continua incondicional: e ela, nao a remissao, que carrega
                  o alerta central. */}
              {textuais.includes("limitacao")
                ? " Leia a limitação abaixo antes de citar estes números."
                : ""}
            </p>
          ) : null}

          {porClasse.length > 0 ? (
            <div>
              <h4 className="rotulo-instrumento">
                F1 por classe
              </h4>
              <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                {porClasse.map(([classe, valor]) => (
                  <li key={classe}>
                    {classe}{" "}
                    <span className="num text-foreground">
                      {percentual(valor)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {/* A prosa da procedencia e da limitacao vai INTEIRA. Ela e o que
              impede o numero de cima de ser lido como promessa. */}
          {textuais.map((chave) => (
            <p
              key={chave}
              className="text-xs leading-relaxed text-muted-foreground"
            >
              <strong className="font-medium">{TEXTUAIS[chave]}:</strong>{" "}
              {String(metricas[chave])}
            </p>
          ))}
        </>
      )}
    </section>
  );
}
