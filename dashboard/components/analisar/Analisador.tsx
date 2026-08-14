"use client";

import { useRef, useState } from "react";
import { FileText, Upload } from "lucide-react";
import {
  analisarArquivo,
  type ConversaAnalisada,
  type ResultadoAnalise,
} from "@/lib/api";
import {
  EXPLICACAO_DESFECHO,
  ROTULO_AUTOR,
  ROTULO_DESFECHO,
  formatarEsperaOuTraco,
  formatarHora,
  formatarSegundos,
} from "@/lib/formato";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Painel } from "@/components/Painel";
import { EtiquetaCategoria } from "@/components/EtiquetaCategoria";
import { EstadoVazio } from "@/components/EstadoVazio";
import { TextoComPesos } from "./TextoComPesos";

/** Teto do lado do cliente, espelhando o do servidor -- recusa antes de subir. */
const TETO_CARACTERES = 200_000;

export function Analisador() {
  const entrada = useRef<HTMLInputElement>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [arquivo, setArquivo] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ResultadoAnalise | null>(null);

  async function aoEscolher(evento: React.ChangeEvent<HTMLInputElement>) {
    const escolhido = evento.target.files?.[0];
    if (!escolhido) return;

    setErro(null);
    setResultado(null);
    setArquivo(escolhido.name);

    const conteudo = await escolhido.text();
    if (conteudo.length > TETO_CARACTERES) {
      setErro(
        `O arquivo tem ${conteudo.length.toLocaleString("pt-BR")} caracteres, acima do limite de ${TETO_CARACTERES.toLocaleString("pt-BR")}. Esta tela examina um atendimento por vez; para um lote inteiro, use a importação em Integrações.`,
      );
      return;
    }

    setOcupado(true);
    const resposta = await analisarArquivo(conteudo);
    setOcupado(false);
    if (resposta.ok) setResultado(resposta.dado);
    else setErro(resposta.erro);
  }

  return (
    <div className="flex flex-col gap-4">
      <Painel
        titulo="Arquivo do atendimento"
        legenda="Nada aqui entra no banco: nem a conversa, nem a nota, nem o arquivo. Analisar não muda o NPS de ninguém — é a diferença entre esta tela e a importação. O conteúdo é lido no seu navegador e interpretado em memória pelo servidor; nenhum byte é gravado em disco."
      >
        <div className="flex flex-col gap-3 px-5 py-4">
          <p className="text-sm text-muted-foreground">
            Um CSV com as colunas{" "}
            <code className="num rounded-sm bg-muted px-1 py-0.5 text-foreground">
              conversa_id, canal, autor, texto, enviada_em, escalou_para_humano
            </code>{" "}
            — o mesmo formato da importação, uma linha por mensagem.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <input
              ref={entrada}
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              onChange={aoEscolher}
            />
            <Button
              type="button"
              size="sm"
              onClick={() => entrada.current?.click()}
              disabled={ocupado}
            >
              <Upload aria-hidden />
              {ocupado ? "Analisando…" : "Escolher arquivo"}
            </Button>
            {arquivo ? (
              <span className="num flex items-center gap-1.5 text-xs text-muted-foreground">
                <FileText aria-hidden className="size-3.5" />
                {arquivo}
              </span>
            ) : null}
          </div>

          {ocupado ? (
            <p className="text-xs text-muted-foreground">
              O peso de cada palavra sai apagando a palavra e perguntando de
              novo ao modelo — uma passada por palavra, em CPU. Uma conversa
              longa leva alguns segundos.
            </p>
          ) : null}
        </div>
      </Painel>

      {erro ? (
        <Alert variant="destructive">
          <AlertTitle>Não foi possível analisar</AlertTitle>
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      ) : null}

      {resultado ? <Resultado resultado={resultado} /> : null}
    </div>
  );
}

function Resultado({ resultado }: { resultado: ResultadoAnalise }) {
  const cortou = resultado.conversas_no_arquivo > resultado.conversas_analisadas;

  return (
    <div className="flex flex-col gap-4">
      {/* O que ficou de FORA vem antes do resultado, na mesma linha do que a
          importação já faz: silenciar o corte faria o operador achar que
          analisou o arquivo inteiro. */}
      {cortou ? (
        <Alert>
          <AlertTitle>
            <span className="num">{resultado.conversas_analisadas}</span> de{" "}
            <span className="num">{resultado.conversas_no_arquivo}</span>{" "}
            conversas analisadas
          </AlertTitle>
          <AlertDescription>
            Esta tela examina um atendimento por vez e para no limite do
            servidor. Para o arquivo inteiro, use a importação em Integrações.
          </AlertDescription>
        </Alert>
      ) : null}

      {resultado.total_rejeitadas > 0 ? (
        <Alert>
          <AlertTitle>
            <span className="num">{resultado.total_rejeitadas}</span> linha(s)
            rejeitada(s)
          </AlertTitle>
          <AlertDescription>
            <ul className="mt-1 flex flex-col gap-0.5">
              {resultado.rejeitadas.map((linha) => (
                <li key={linha.numero_linha} className="text-xs">
                  <span className="num">linha {linha.numero_linha}</span>:{" "}
                  {linha.motivo}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      ) : null}

      {resultado.analises.map((analise) => (
        <Analise
          key={analise.conversa.id}
          analise={analise}
          referencia={resultado.referencia_conversas}
        />
      ))}
    </div>
  );
}

function Medida({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <dt className="text-xs text-muted-foreground">{rotulo}</dt>
      <dd className="num text-base leading-none text-foreground">{valor}</dd>
    </div>
  );
}

function Analise({
  analise,
  referencia,
}: {
  analise: ConversaAnalisada;
  referencia: number;
}) {
  const semSinal = analise.score === null;

  return (
    <div className="flex flex-col gap-4">
      <Painel
        titulo={`Resultado — ${analise.conversa.id}`}
        legenda="A nota sai do fusor, que aprendeu com dezesseis medidas de texto, emoji e tempo. Emoção e ironia aparecem na transcrição abaixo mas NÃO entram nessa conta: elas descrevem a fala, não pontuam o atendimento."
      >
        <dl className="grid grid-cols-2 gap-x-6 gap-y-4 px-5 py-4 sm:grid-cols-4">
          <div className="flex min-w-0 flex-col gap-1">
            <dt className="text-xs text-muted-foreground">Nota inferida</dt>
            <dd className="flex items-baseline gap-2">
              {semSinal ? (
                <span className="text-sm text-muted-foreground">
                  sem sinal do cliente
                </span>
              ) : (
                <>
                  <span className="num estimado text-2xl leading-none text-foreground">
                    {analise.nota}
                  </span>
                  <EtiquetaCategoria categoria={analise.categoria} />
                </>
              )}
            </dd>
          </div>
          <div className="flex min-w-0 flex-col gap-0.5">
            <dt className="text-xs text-muted-foreground">Desfecho</dt>
            <dd
              className="text-base leading-none text-foreground"
              title={EXPLICACAO_DESFECHO[analise.desfecho]}
            >
              {ROTULO_DESFECHO[analise.desfecho]}
            </dd>
          </div>
          <Medida
            rotulo="Mensagens"
            valor={`${analise.qtd_mensagens} (${analise.qtd_cliente} do cliente)`}
          />
          <Medida
            rotulo="Duração"
            valor={formatarSegundos(analise.duracao_s)}
          />
          <Medida
            rotulo="1ª resposta"
            valor={formatarEsperaOuTraco(analise.latencia_primeira_resposta_s)}
          />
          <Medida
            rotulo="Resposta do bot (mediana)"
            valor={formatarEsperaOuTraco(analise.latencia_mediana_bot_s)}
          />
          <Medida
            rotulo="Resposta humana (mediana)"
            valor={formatarEsperaOuTraco(analise.latencia_mediana_humano_s)}
          />
          <Medida rotulo="Canal" valor={analise.conversa.canal} />
        </dl>
      </Painel>

      <Painel
        titulo="A conversa, palavra a palavra"
        legenda="O grifo é medido por oclusão: apaga-se a palavra e pergunta-se de novo ao modelo. Verde empurrou a leitura para satisfeito, vermelho puxou para insatisfeito, e a força da cor é o tamanho do efeito. Ressalva do método: apagar uma palavra de dentro de uma expressão fixa deixa um fragmento que ninguém escreveria — o peso é verdadeiro sobre o que o modelo faz, e não deve ser lido como “esta palavra significa insatisfação”. Só a fala do cliente recebe peso: o classificador foi treinado em texto de cliente, e pontuar o roteiro do bot seria número sem lastro."
        semPadding
      >
        <ol className="flex flex-col">
          {analise.mensagens.map((mensagem) => {
            const doCliente = mensagem.autor === "cliente";
            return (
              <li
                key={mensagem.indice}
                className="flex flex-col gap-1 border-b border-compasso px-5 py-3 last:border-b-0"
              >
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                  <span
                    className={`text-xs ${doCliente ? "text-dito-texto" : "text-muted-foreground"}`}
                  >
                    {ROTULO_AUTOR[mensagem.autor]}
                  </span>
                  <span className="num text-xs text-muted-foreground">
                    {formatarHora(
                      analise.conversa.mensagens[mensagem.indice].enviada_em,
                    )}
                  </span>
                  {doCliente && mensagem.prob_satisfeito !== null ? (
                    <span className="num text-xs text-muted-foreground">
                      satisfeito {mensagem.prob_satisfeito.toFixed(2)} ·
                      insatisfeito {mensagem.prob_insatisfeito?.toFixed(2)}
                    </span>
                  ) : null}
                </div>

                <p className="text-sm leading-relaxed text-foreground">
                  <TextoComPesos
                    texto={mensagem.texto}
                    palavras={mensagem.palavras}
                  />
                </p>

                {doCliente && mensagem.prob_ironia !== null ? (
                  <SinaisDeLeitura mensagem={mensagem} />
                ) : null}
              </li>
            );
          })}
        </ol>
      </Painel>

      <Painel
        titulo="Palavras desta conversa"
        legenda={
          referencia === 0
            ? "Não há conversas no banco para servir de comparação, então o destaque sai vazio — inventar “igual à média” sem ter medido média nenhuma seria pior que não comparar."
            : `“Destaque” é quantas vezes a palavra aparece mais aqui do que no resto do banco (${referencia} atendimentos). É o que responde o que ESTA conversa tem de diferente: as palavras mais repetidas de qualquer atendimento são as mesmas de todos os outros. Palavras funcionais (“de”, “que”, “não”) ficam de fora da contagem, mas continuam valendo peso na transcrição acima — “não” muda a leitura de uma frase inteira.`
        }
        semPadding
      >
        {analise.vocabulario.length === 0 ? (
          <EstadoVazio
            className="m-5"
            titulo="Sem palavras do cliente"
            explicacao="O cliente não falou nesta conversa, então não há vocabulário a contar."
          />
        ) : (
          <ul className="flex flex-col">
            {analise.vocabulario.map((item) => (
              <li
                key={item.palavra}
                className="flex items-baseline justify-between gap-4 border-b border-compasso px-5 py-2 last:border-b-0"
              >
                <span className="text-sm text-foreground">{item.palavra}</span>
                <span className="flex items-baseline gap-4 text-xs text-muted-foreground">
                  <span className="num">{item.vezes}×</span>
                  {item.destaque === null ? (
                    <span title="Não aparece em nenhuma outra conversa do banco.">
                      inédita
                    </span>
                  ) : (
                    <span
                      className="num"
                      title={`${item.destaque.toFixed(1)} vezes mais frequente aqui do que no resto do banco`}
                    >
                      {item.destaque.toFixed(1)}× o normal
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Painel>
    </div>
  );
}

/**
 * Emocao e ironia da mensagem.
 *
 * Vem visualmente separado da probabilidade de satisfacao de proposito: os
 * dois numeros daqui NAO entram no score. Encostar "ironia 0,99" num painel de
 * nota sem essa separacao convida a conclusao de que a ironia derrubou a nota
 * -- e o fusor nunca viu ironia nenhuma.
 */
function SinaisDeLeitura({
  mensagem,
}: {
  mensagem: { emocao: Record<string, number> | null; prob_ironia: number | null };
}) {
  const emocaoTop = mensagem.emocao
    ? Object.entries(mensagem.emocao).sort((a, b) => b[1] - a[1])[0]
    : null;

  return (
    <p className="flex flex-wrap items-baseline gap-x-3 text-xs text-muted-foreground">
      <span className="text-[11px] uppercase tracking-wide opacity-70">
        fora do score
      </span>
      {emocaoTop ? (
        <span>
          emoção {emocaoTop[0]}{" "}
          <span className="num">{emocaoTop[1].toFixed(2)}</span>
        </span>
      ) : null}
      {mensagem.prob_ironia !== null ? (
        <span title="A cabeça de ironia acerta o caso de manual mas marca 6 em 10 falas sinceras de atendimento como irônicas. Leia como indício, nunca como veredito.">
          ironia <span className="num">{mensagem.prob_ironia.toFixed(2)}</span>{" "}
          <span className="opacity-70">(pouco confiável)</span>
        </span>
      ) : null}
    </p>
  );
}
