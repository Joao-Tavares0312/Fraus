import { formatarNumero } from "@/lib/formato";

/**
 * Emocao e ironia de uma fala -- as duas cabecas de LEITURA POR FRASE.
 *
 * COMPARTILHADO entre o simulador ao vivo e a analise de arquivo de proposito.
 * As duas telas leem os MESMOS campos da mesma API, e cada uma tinha a sua
 * versao: o simulador mostrava as oito emocoes com barra e as ressalvas
 * inteiras, e a analise mostrava so a emocao vencedora numa linha. A API
 * mandava as oito nas duas, e uma delas jogava sete fora.
 *
 * Duas copias de um painel que explica um modelo envelhecem separadas -- e a
 * que envelhece e sempre a que ninguem olha, ate alguem citar dela um numero
 * sem a ressalva que a outra tela ja tinha.
 *
 * Desde 21/08/2026 emocao TAMBEM pontua: `emocao_*` entrou nas features do
 * fusor (agregada por conversa, nao por frase). A ironia chegou a pontuar do
 * mesmo jeito, mas SAIU do vetor em 04/09/2026 -- medida no corpus de treino,
 * a cabeca (treinada em tweet e noticia) vira detector de sentimento positivo
 * em resenha de atendimento, nao detector de ironia. Ela continua carregada e
 * exibida aqui, como leitura por frase, so que sem pesar na nota.
 * O numero exibido AQUI e a leitura desta frase, nao a media que alimenta o
 * modelo -- por isso a separacao visual continua existindo: encostar
 * "ironia 99%" na barra de satisfacao convidaria a ler uma frase como causa
 * direta da nota, quando quem pesa (so no caso da emocao) e a media da
 * conversa inteira.
 */
export function CabecasDeLeitura({
  emocao,
  ironia,
  compacto = false,
  ressalvas = true,
}: {
  emocao: Record<string, number> | null;
  ironia: number | null;
  /** Sem o cabeçalho de contexto — para quem já o escreveu por fora. */
  compacto?: boolean;
  /**
   * Mostrar a prosa da díade do desprezo e da limitação da ironia.
   *
   * Verdadeiro numa tela que analisa UMA frase. Falso quando o painel se
   * repete por mensagem: a mesma ressalva vinte vezes na mesma página vira
   * ruído e para de ser lida, que é o oposto do que ela existe para fazer. Aí
   * ela vale uma vez, no cabeçalho de quem repete.
   */
  ressalvas?: boolean;
}) {
  if (!emocao && ironia === null) return null;

  // Ordena por probabilidade: a emocao que o modelo viu vem primeiro, e a
  // cauda de valores baixos nao rouba a leitura.
  const emocoes = emocao ? Object.entries(emocao).sort((a, b) => b[1] - a[1]) : [];
  const maior = emocoes[0]?.[1] ?? 1;

  return (
    <div className="flex flex-col gap-3">
      {!compacto ? (
        <p className="text-xs text-muted-foreground">
          <span className="uppercase tracking-wide opacity-70">
            leitura por frase
          </span>{" "}
          — a média da emoção por conversa entra nas features do fusor desde
          21/08/2026, mas o número aqui é desta frase, não a média que pesa na
          nota. A ironia é só leitura: desde 04/09/2026 ela não entra mais no
          fusor.
        </p>
      ) : null}

      {emocoes.length > 0 ? (
        <ul className="flex flex-col gap-1">
          {emocoes.map(([nome, valor]) => (
            <li key={nome} className="flex items-center gap-2">
              <span className="w-20 shrink-0 text-xs text-muted-foreground">
                {nome}
              </span>
              {/* A largura é relativa à MAIOR emoção, não a 100%: as sete
                  classes somam 1, então a barra em escala absoluta deixaria
                  tudo abaixo da vencedora invisível. O número ao lado é o
                  valor real, para a escala relativa não enganar. */}
              <span className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-sm bg-muted">
                <span
                  className="block h-full bg-medido"
                  style={{ width: `${maior > 0 ? (valor / maior) * 100 : 0}%` }}
                />
              </span>
              <span className="num w-12 shrink-0 text-right text-xs text-muted-foreground">
                {formatarNumero(valor * 100)}%
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      {ressalvas && emocao && "desprezo" in emocao ? (
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          <strong>desprezo</strong> não é uma classe treinada: nenhum corpus em
          português a anota. Ela é derivada da díade raiva + nojo (Plutchik,
          1980) pela média geométrica — que exige as <em>duas</em> emoções
          juntas, enquanto a média aritmética daria meio ponto para raiva pura
          sem nojo nenhum, o que é raiva, não desprezo.
        </p>
      ) : null}

      {ironia !== null ? (
        <div className="flex flex-col gap-1">
          <div className="flex items-baseline gap-2">
            <span className="text-xs text-muted-foreground">ironia</span>
            <span className="num text-sm text-foreground">
              {formatarNumero(ironia * 100)}%
            </span>
            <span className="text-[11px] text-muted-foreground opacity-70">
              pouco confiável
            </span>
          </div>
          {ressalvas ? (
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              Esta cabeça acerta o caso de manual — “que atendimento
              maravilhoso, só esperei 3 horas” — e erra feio no resto:{" "}
              <strong>6 em 10</strong> falas sinceras de atendimento saem
              marcadas como irônicas, com 0,999 de confiança. Ela foi treinada
              num corpus gerado e aprendeu o registro conversacional em vez da
              pragmática. Leia como indício, nunca como veredito.
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

/**
 * A FORMA da escrita de uma fala -- caixa alta, alongamento, ênfase, palavrão.
 *
 * Irmão de `CabecasDeLeitura` e mora no mesmo arquivo pelo mesmo motivo que
 * ela: painel que explica um modelo, duplicado, envelhece separado.
 *
 * Diferente das duas cabeças de leitura, estilo não é modelo -- é
 * determinístico, calculado por regra em `fraus/sinais/estilo.py`. Por isso
 * não leva ressalva de confiabilidade: não há probabilidade para calibrar,
 * a marca ou está no texto ou não está. O que ele NÃO diz é o quanto isso
 * pesou na nota: quem pesa é a média da conversa inteira, nas features
 * `estilo_*` do fusor.
 */
export function LeituraDeEstilo({
  estilo,
}: {
  estilo: {
    caixa_alta: boolean;
    alongamento: boolean;
    pontuacao_enfatica: number;
    palavrao: number | null;
    palavrao_dirigido: boolean;
    censura: boolean;
  } | null;
}) {
  if (!estilo) return null;

  const marcas: string[] = [];
  if (estilo.caixa_alta) marcas.push("caixa alta");
  if (estilo.alongamento) marcas.push("alongamento");
  if (estilo.pontuacao_enfatica > 0) {
    marcas.push(`ênfase ×${estilo.pontuacao_enfatica}`);
  }
  if (estilo.palavrao !== null) {
    const grau =
      estilo.palavrao >= 1 ? "pesado" : estilo.palavrao >= 0.66 ? "médio" : "leve";
    marcas.push(
      estilo.palavrao_dirigido ? `palavrão ${grau}, dirigido` : `palavrão ${grau}`,
    );
  }
  if (estilo.censura) marcas.push("autocensura");

  // Nenhuma marca é resultado legítimo, não estado vazio: a fala foi medida e
  // não tem ênfase nenhuma. Some da tela em vez de anunciar "nada" vinte
  // vezes numa página que repete o painel por mensagem.
  if (marcas.length === 0) return null;

  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="marcas de estilo da fala">
      {marcas.map((marca) => (
        <li
          key={marca}
          className="rounded-sm bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground"
        >
          {marca}
        </li>
      ))}
    </ul>
  );
}

/**
 * As tres probabilidades de satisfacao como barra empilhada.
 *
 * A largura E a probabilidade -- nao ha eixo escondido. Ordem fixa das classes
 * (0 insatisfeito, 1 neutro, 2 satisfeito), a mesma do servidor.
 */
export function BarraDeClasses({
  insatisfeito,
  neutro,
  satisfeito,
}: {
  insatisfeito: number;
  neutro: number;
  satisfeito: number;
}) {
  const classes = [
    { rotulo: "Insatisfeito", valor: insatisfeito, cor: "var(--detrator)" },
    { rotulo: "Neutro", valor: neutro, cor: "var(--neutro)" },
    { rotulo: "Satisfeito", valor: satisfeito, cor: "var(--promotor)" },
  ];

  return (
    <div className="flex flex-col gap-1.5">
      <div
        className="flex h-2 w-full gap-px overflow-hidden rounded-sm bg-muted"
        role="img"
        aria-label={classes
          .map((c) => `${c.rotulo} ${formatarNumero(c.valor * 100)}%`)
          .join(", ")}
      >
        {classes.map((classe) => (
          <span
            key={classe.rotulo}
            style={{ width: `${classe.valor * 100}%`, background: classe.cor }}
          />
        ))}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1">
        {classes.map((classe) => (
          <li key={classe.rotulo} className="flex items-baseline gap-1.5">
            <span
              aria-hidden
              className="size-2 shrink-0 translate-y-px rounded-full"
              style={{ background: classe.cor }}
            />
            <span className="text-xs text-muted-foreground">{classe.rotulo}</span>
            <span className="num text-xs text-foreground">
              {formatarNumero(classe.valor * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
