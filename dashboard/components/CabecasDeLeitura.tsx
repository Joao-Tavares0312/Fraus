import { PartituraDaFala } from "@/components/PartituraDaFala";
import type { ProbabilidadesDeClasse } from "@/lib/partitura";

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
  classes = null,
  emocao,
  ironia,
  compacto = false,
  ressalvas = true,
  recolher = true,
}: {
  /** Ver `PartituraDaFala`: falso numa tela que examina uma frase só. */
  recolher?: boolean;
  /**
   * As três probabilidades de classe DESTA frase, quando a tela as tem. Entram
   * na mesma pauta de emoção e ironia (`PartituraDaFala`) — a escala comum é o
   * ponto do desenho. O Simulador não passa: ele mostra a classificação na
   * barra grande dele, acima.
   */
  classes?: ProbabilidadesDeClasse | null;
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
  if (!classes && !emocao && ironia === null) return null;

  return (
    <div className="flex flex-col gap-3">
      {!compacto ? (
        <p className="text-xs text-muted-foreground">
          <span className="uppercase tracking-wide">
            leitura por frase
          </span>{" "}
          — a média da emoção por conversa entra nas features do fusor desde
          21/08/2026, mas o número aqui é desta frase, não a média que pesa na
          nota. A ironia é só leitura: desde 04/09/2026 ela não entra mais no
          fusor.
        </p>
      ) : null}

      <PartituraDaFala classes={classes} emocao={emocao} ironia={ironia} recolher={recolher} />

      {/* A ETIQUETA DE EXPOSICAO -- Art. 50(3) do EU AI Act, em vigor desde
          02/08/2026. Classificar sete emocoes torna o Fraus, pela letra do
          regulamento, um sistema de RECONHECIMENTO DE EMOCAO, e o deployer
          precisa informar as pessoas naturais expostas a ele. Nao importa que
          rode local, em CPU e sem LLM: o que classifica o sistema e o que ele
          infere sobre pessoas.

          Mora aqui, e nao numa faixa de aviso propria, pelo mesmo motivo que a
          etiqueta de estimativa mora colada ao NPS: ressalva longe do numero
          nao e lida. E segue a regra de ressalva unica -- `ressalvas` e falso
          quando o painel se repete por mensagem, e ai a etiqueta vale uma vez
          no cabecalho de quem repete.

          Linguagem de gente, nao citacao de artigo. Escopo e base legal
          inteiros em docs/conformidade.md. */}
      {ressalvas && emocao ? (
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          <strong>Isto é leitura automática de emoção.</strong> As classes
          acima são inferidas do texto por um modelo — nunca declaradas por
          quem escreveu, e nunca conferidas por uma pessoa antes de aparecerem
          aqui. Elas descrevem <strong>o cliente</strong>: o Fraus não pontua
          atendentes, e isso é uma regra do produto, não uma pendência.
        </p>
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

      {/* O numero e a marca de "cabeça pouco confiável" moram na pauta (nota
          tracejada, com o título no rótulo). Aqui fica só a prosa, que vale
          uma vez por tela. */}
      {ressalvas && ironia !== null ? (
        <p className="text-[11px] leading-relaxed text-muted-foreground">
          <strong>ironia é cabeça pouco confiável</strong> — por isso a nota
          tracejada. Ela acerta o caso de manual — “que atendimento
          maravilhoso, só esperei 3 horas” — e erra feio no resto:{" "}
          <strong>6 em 10</strong> falas sinceras de atendimento saem marcadas
          como irônicas, com 0,999 de confiança. Ela foi treinada num corpus
          gerado e aprendeu o registro conversacional em vez da pragmática.
          Leia como indício, nunca como veredito.
        </p>
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
