import type { FichaModelo } from "@/lib/api";
import { formatarNumero } from "@/lib/formato";
import { Painel } from "@/components/Painel";
import { EstadoVazio } from "@/components/EstadoVazio";
import { LIMIAR_SUSPEITO } from "./MetricasTreino";

/**
 * O VEREDITO: as tres ressalvas estruturais que o avaliador precisa ler ANTES
 * de qualquer numero desta tela, num sistema `dominante` -- o unico da tela
 * Modelo, e por isso o primeiro do arquivo, antes do simulador.
 *
 * Ate 04/09/2026 estes tres fatos estavam espalhados: os dois de ironia
 * enterrados em `MetricasTreino.tsx` num paragrafo do mesmo peso visual que a
 * contagem do lexicon de emoji, e o de tempo em lugar nenhum desta tela (so
 * na visao geral, em `NotaMetodologica.tsx`). Nenhum dos tres foi inventado
 * aqui -- os dois de ironia leem os MESMOS campos de `GET /modelo` que
 * `MetricasTreino` ja lia (`cabecas` e `metricas`), e o de tempo e uma
 * limitacao declarada de arquitetura (nao ha cabeca de tempo a treinar; o
 * sinal vem de `fraus/sinais/tempo.py` sobre timestamps, nunca de fine-tuning),
 * por isso nao depende de nenhum campo numerico da API.
 */
export function EstadoDoModelo({ modelo }: { modelo: FichaModelo }) {
  const ironia = modelo.cabecas.find((cabeca) => cabeca.nome === "ironia") ?? null;
  const metricasIronia = ironia?.metricas ?? null;

  const f1Bruto =
    metricasIronia && typeof metricasIronia.f1_ironico === "number"
      ? metricasIronia.f1_ironico
      : null;
  const f1Percentual =
    f1Bruto !== null
      ? formatarNumero(f1Bruto <= 1 ? f1Bruto * 100 : f1Bruto)
      : null;
  const f1Suspeito = f1Bruto !== null && f1Bruto >= LIMIAR_SUSPEITO;

  return (
    <Painel
      titulo="O veredito, antes do número"
      nivel="dominante"
      legenda={
        <>
          A ironia foi a primeira familia a entrar no vetor do fusor, em
          21/08/2026, e a primeira a sair dele, em 04/09/2026 -- a cabeca (IDPT
          2021, treinada em tweet e noticia) mede sentimento positivo no corpus
          de treino deste projeto, nao ironia, porque frase educada com queixa
          real (&ldquo;que atendimento maravilhoso, so esperei 3 horas&rdquo;) e exatamente
          o padrao que ela aprendeu a reconhecer como ironica em outro dominio.
          Ela continua carregada, obrigatoria e lida por mensagem -- aparece em
          `mensagens[].prob_ironia` e no simulador abaixo -- so nao pesa mais em
          `contribuicoes` nem em `importancias`. O F1 de 100% mede acerto no
          MESMO corpus sintetico que gerou o treino: metrica perfeita em tarefa
          de linguagem quase nunca significa modelo bom, significa que o teste
          se parece demais com o treino. O sinal de tempo tem a mesma limitacao
          por um motivo diferente: nenhum corpus publico de review em
          portugues tem timestamps de dialogo, entao ele e treinado em
          conversas sinteticas calibradas por literatura de live chat, nao em
          atendimento real.
        </>
      }
    >
      <ul className="flex flex-col gap-4">
        <li className="flex flex-col gap-1">
          <span className="flex flex-wrap items-baseline gap-2">
            <span className="rounded-full bg-warning-rich-text/10 px-2 py-0.5 text-xs font-medium text-warning-rich-text">
              fora do vetor
            </span>
            <span className="text-sm font-medium text-foreground">
              A ironia não pontua
            </span>
          </span>
          {ironia ? (
            <p className="text-xs leading-relaxed text-muted-foreground">
              {ironia.pontua
                ? "A API ainda reporta esta cabeca como parte do fusor -- verifique se este texto ficou desatualizado."
                : "Carregada, obrigatória e lida por mensagem, mas fora de `importancias` e `contribuicoes` desde 04/09/2026: medida no corpus de treino, ela funciona como detector de sentimento positivo, não de ironia."}
            </p>
          ) : (
            <EstadoVazio
              className="mt-1"
              titulo="A cabeça de ironia não subiu"
              explicacao="GET /modelo não trouxe uma cabeça chamada `ironia` em `cabecas`. Sem ela não há como confirmar se continua fora do fusor."
              etapa="notebook 04 (ironia), descrito em docs/treinamento.md"
            />
          )}
        </li>

        <li className="flex flex-col gap-1">
          <span className="flex flex-wrap items-baseline gap-2">
            <span className="rounded-full bg-warning-rich-text/10 px-2 py-0.5 text-xs font-medium text-warning-rich-text">
              suspeito
            </span>
            <span className="text-sm font-medium text-foreground">
              O F1 da ironia é medida em corpus sintético
            </span>
          </span>
          {f1Percentual !== null ? (
            <p className="text-xs leading-relaxed text-muted-foreground">
              <span className="num text-foreground">{f1Percentual}%</span> de
              F1 na classe irônica, {f1Suspeito ? "acima" : "abaixo"} do limiar
              que este projeto trata como suspeito.{" "}
              {f1Suspeito
                ? "Metrica perfeita em tarefa de linguagem quase nunca significa modelo bom."
                : ""}
            </p>
          ) : (
            <EstadoVazio
              className="mt-1"
              titulo="O F1 da ironia ainda não foi exportado"
              explicacao="`metricas.f1_ironico` não veio de GET /modelo — nem para a cabeça de ironia, nem com valor 0, que seria dizer que ela erra tudo."
              etapa="notebook 04 (ironia), que exporta metricas.json"
            />
          )}
        </li>

        <li className="flex flex-col gap-1">
          <span className="flex flex-wrap items-baseline gap-2">
            <span className="rounded-full bg-warning-rich-text/10 px-2 py-0.5 text-xs font-medium text-warning-rich-text">
              sintético
            </span>
            <span className="text-sm font-medium text-foreground">
              O sinal de tempo é treinado em dados sintéticos
            </span>
          </span>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Latência, escalação e abandono aprendem de conversas sintéticas
            calibradas por literatura de live chat — nenhum corpus público de
            review em português tem timestamps de diálogo. Limitação
            declarada, não escondida.
          </p>
        </li>
      </ul>
    </Painel>
  );
}
