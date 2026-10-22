"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { anunciarAtualizacao } from "@/lib/atualizacao";
import { FileText, RefreshCw, Upload } from "lucide-react";
import {
  analisarUpload,
  previaUpload,
  type ConversaAnalisada,
  type MapeamentoConfirmado,
  type OrdemData,
  type PreviaLeitura,
  type MensagemAnalisada,
  type ResultadoAnalise,
} from "@/lib/api";
import {
  CabecasDeLeitura,
  LeituraDeEstilo,
} from "@/components/CabecasDeLeitura";
import {
  EXPLICACAO_DESFECHO,
  ROTULO_AUTOR,
  ROTULO_DESFECHO,
  ROTULO_SEM_SINAL,
  formatarEsperaOuTraco,
  formatarHora,
  formatarSegundos,
} from "@/lib/formato";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Painel } from "@/components/Painel";
import { EtiquetaCategoria } from "@/components/EtiquetaCategoria";
import { NotaInferida } from "@/components/NotaInferida"
import { EstadoVazio } from "@/components/EstadoVazio";
import { PainelContribuicoes } from "@/components/PainelContribuicoes";
import { TextoComPesos } from "./TextoComPesos";
import { formatarProbabilidade } from "@/lib/partitura";
import { ConferenciaDeColunas } from "./ConferenciaDeColunas";
import { IconeDeAcao } from "@/components/IconeDeAcao";
import { deveSalvar, proximoPasso } from "@/lib/fluxo-analise";

/** Teto do lado do cliente, espelhando o do servidor -- recusa antes de subir. */
const TETO_BYTES = 200_000;

const ACEITOS = ".csv,.tsv,.xlsx,.xlsm,.json,.jsonl,.txt,.docx,.pdf";

/**
 * "Arrastar e pronto" (19/10/2026): o cliente final solta o arquivo e recebe
 * a análise, já salva nos indicadores. A conferência de colunas só aparece
 * quando o servidor diz que a leitura NÃO é confiável (`previa.confiavel`),
 * ou quando a pessoa pede para ajustar depois do resultado.
 *
 * Sem horário não há nota nem o que somar aos indicadores: o arquivo é lido
 * em modo avulso, e o resultado diz por quê.
 */
export function Analisador() {
  const entrada = useRef<HTMLInputElement>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [arquivo, setArquivo] = useState<string | null>(null);
  /** O último arquivo escolhido, para "tentar de novo" sem reabrir o seletor. */
  const [ultimo, setUltimo] = useState<File | null>(null);
  const [resultado, setResultado] = useState<ResultadoAnalise | null>(null);
  /** A leitura inferida que precisa de conferência antes do modelo rodar. */
  const [previa, setPrevia] = useState<PreviaLeitura | null>(null);
  /** A última prévia com mapeamento, para "ajustar colunas" depois do resultado. */
  const [mapeada, setMapeada] = useState<PreviaLeitura | null>(null);
  /**
   * Contador, não booleano: dragenter/dragleave disparam para CADA filho que
   * o cursor cruza, e um booleano apagaria o realce ao passar sobre o ícone
   * dentro da própria área.
   */
  const [arrastando, setArrastando] = useState(0);

  async function rodar(
    escolhido: File,
    lida: PreviaLeitura,
    opcoes: { mapeamento?: MapeamentoConfirmado; ordemData?: OrdemData | null } = {},
  ) {
    const resposta = await analisarUpload(escolhido, {
      ...opcoes,
      salvar: deveSalvar(lida),
    });
    if (resposta.ok) {
      setPrevia(null);
      setResultado(resposta.dado);
      if (resposta.dado.gravacao) anunciarAtualizacao();
    } else {
      setErro(resposta.erro);
    }
  }

  async function analisar(escolhido: File) {
    setErro(null);
    setResultado(null);
    setPrevia(null);
    setMapeada(null);
    setArquivo(escolhido.name);
    setUltimo(escolhido);

    if (escolhido.size > TETO_BYTES) {
      setErro(
        `O arquivo tem ${Math.round(escolhido.size / 1024).toLocaleString("pt-BR")} kB, acima do limite de ${Math.round(TETO_BYTES / 1024).toLocaleString("pt-BR")} kB. Divida o arquivo em partes menores e envie uma de cada vez.`,
      );
      return;
    }

    // A prévia vem ANTES do modelo: é só leitura e responde rápido. Leitura
    // confiável segue direto; duvidosa para na conferência — coluna errada
    // não dá erro, dá nota errada.
    setOcupado(true);
    const lida = await previaUpload(escolhido);
    if (!lida.ok) {
      setOcupado(false);
      setErro(lida.erro);
      return;
    }
    if (lida.dado.mapeamento) setMapeada(lida.dado);
    if (proximoPasso(lida.dado) === "conferir") {
      setOcupado(false);
      setPrevia(lida.dado);
      return;
    }
    await rodar(escolhido, lida.dado);
    setOcupado(false);
  }

  async function ajustar(mapeamento: MapeamentoConfirmado, ordemData: OrdemData | null) {
    if (!ultimo) return;
    setOcupado(true);
    const lida = await previaUpload(ultimo, { mapeamento, ordemData });
    setOcupado(false);
    if (lida.ok) {
      setErro(null);
      setPrevia(lida.dado);
      setMapeada(lida.dado);
    } else {
      setErro(lida.erro);
    }
  }

  async function confirmar(mapeamento: MapeamentoConfirmado, ordemData: OrdemData | null) {
    if (!ultimo || !previa) return;
    setOcupado(true);
    setErro(null);
    await rodar(ultimo, previa, { mapeamento, ordemData });
    setOcupado(false);
  }

  async function aoEscolher(evento: React.ChangeEvent<HTMLInputElement>) {
    const escolhido = evento.target.files?.[0];

    // Zerar o valor do input É O CONSERTO, não faxina. Um `<input type=file>`
    // só dispara `change` quando o valor MUDA -- escolher o mesmo arquivo de
    // novo não dispara nada, e a tela ficava parada mostrando o erro anterior
    // sem nenhum sinal de que o clique foi ignorado.
    evento.target.value = "";

    if (escolhido) await analisar(escolhido);
  }

  return (
    <div className="flex min-w-0 flex-col gap-4">
      {/* Mantido montado mesmo quando o resultado recolhe a área de envio. */}
      <input
        ref={entrada}
        type="file"
        accept={ACEITOS}
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        disabled={ocupado}
        onChange={aoEscolher}
        data-testid="entrada-arquivo"
      />
      {resultado ? (
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 border-b border-linha pb-3">
          <span className="flex min-w-0 items-center gap-2 text-sm text-foreground">
            <FileText aria-hidden className="size-4 shrink-0" />
            <span className="break-all">{arquivo}</span>
          </span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => entrada.current?.click()}
            disabled={ocupado}
          >
            <IconeDeAcao acao="arquivo" />
            Trocar arquivo
          </Button>
        </div>
      ) : (
      <Painel
        titulo="Arquivo do atendimento"
        legenda="As conversas analisadas entram nos indicadores, nos atendimentos e no grafo. Dados pessoais são censurados antes da análise, e reenviar a mesma conversa não duplica nada."
      >
        <div className="px-5 py-4">
          {/*
            A área inteira recebe o arquivo — arrastar por cima realça com a
            cor de ação, que aqui é legítima: soltar É a ação primária da
            tela. O clique continua passando pelo <input>, então teclado e
            leitor de tela usam o mesmo caminho de sempre (o botão).
          */}
          <div
            data-arrastando={arrastando > 0 || undefined}
            onDragEnter={(evento) => {
              evento.preventDefault();
              if (!ocupado) setArrastando((n) => n + 1);
            }}
            onDragLeave={() => setArrastando((n) => Math.max(0, n - 1))}
            onDragOver={(evento) => evento.preventDefault()}
            onDrop={async (evento) => {
              evento.preventDefault();
              setArrastando(0);
              const solto = evento.dataTransfer.files?.[0];
              if (solto && !ocupado) await analisar(solto);
            }}
            className="group flex flex-col items-center gap-2 rounded-md border border-dashed border-input px-6 py-10 text-center transition-colors duration-200 ease-fluid data-[arrastando]:border-primary data-[arrastando]:bg-primary/5"
          >
            <Upload
              aria-hidden
              className="size-5 text-muted-foreground transition-colors duration-200 group-data-[arrastando]:text-primary"
            />
            <p className="text-sm text-muted-foreground">
              Arraste o arquivo para cá, ou
            </p>
            <Button
              type="button"
              size="sm"
              onClick={() => entrada.current?.click()}
              disabled={ocupado}
            ><IconeDeAcao acao="arquivo" />
              {ocupado ? "Analisando…" : "Escolher arquivo"}
            </Button>
            <p className="text-xs text-muted-foreground">
              Planilha, CSV, JSON ou conversa exportada do WhatsApp
            </p>
            {arquivo ? (
              <span className="num mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                <FileText aria-hidden className="size-3.5" />
                {arquivo}
              </span>
            ) : null}
          </div>

          {ocupado ? (
            <p className="mt-3 text-xs text-muted-foreground" role="status">
              Lendo cada mensagem com os modelos, em CPU. Uma conversa longa
              leva alguns segundos.
            </p>
          ) : null}
        </div>
      </Painel>
      )}

      {resultado?.gravacao ? (
        <Alert role="status">
          <AlertTitle>{resultado.gravacao.salvas} atendimento(s) salvo(s) nos indicadores</AlertTitle>
          <AlertDescription>
            <p>Os indicadores e o grafo já consideram os atendimentos analisados.</p>
            <div className="mt-3 flex flex-wrap gap-3">
              {[["/dashboard", "Ver indicadores"], ["/dashboard/atendimentos", "Ver atendimentos"], ["/dashboard/grafo", "Ver grafo"]].map(([rota, rotulo]) => <Link key={rota} className="text-sm underline underline-offset-4" href={`${rota}?de=${resultado.gravacao!.de}&ate=${resultado.gravacao!.ate}`}>{rotulo}</Link>)}
            </div>
          </AlertDescription>
        </Alert>
      ) : resultado ? (
        <Alert role="status">
          <AlertTitle>
            {resultado.tem_tempo ? "Gravação não confirmada" : "Análise concluída sem salvar nos indicadores"}
          </AlertTitle>
          <AlertDescription>
            {resultado.tem_tempo
              ? "A análise foi concluída, mas a resposta não confirmou a gravação. Não é possível afirmar que estes atendimentos já entraram nos indicadores."
              : "O arquivo não traz o horário das mensagens. Sem horário não há nota nem gravação nos indicadores; a leitura por mensagem está disponível abaixo."}
          </AlertDescription>
        </Alert>
      ) : null}

      {/* O erro carrega o MOTIVO e as duas saídas: corrigir e reenviar o mesmo
          arquivo, ou escolher outro. */}
      {erro ? (
        <Alert variant="destructive">
          <AlertTitle>
            Não consegui ler{arquivo ? ` ${arquivo}` : " o arquivo"}
          </AlertTitle>
          <AlertDescription>
            <p className="whitespace-pre-line">{erro}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {ultimo ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => analisar(ultimo)}
                  disabled={ocupado}
                >
                  <RefreshCw aria-hidden />
                  Tentar de novo
                </Button>
              ) : null}
              {mapeada && !previa ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => { setErro(null); setPrevia(mapeada); }}
                  disabled={ocupado}
                >
                  Ajustar colunas
                </Button>
              ) : null}
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => entrada.current?.click()}
                disabled={ocupado}
              >
                <Upload aria-hidden />
                Escolher outro arquivo
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      ) : null}

      {previa?.mapeamento && arquivo ? (
        <ConferenciaDeColunas
          previa={previa}
          ocupado={ocupado}
          aoAjustar={ajustar}
          aoConfirmar={(mapeamento, ordem) => confirmar(mapeamento, ordem)}
          aoCancelar={() => entrada.current?.click()}
        />
      ) : null}

      {resultado && mapeada && !previa ? (
        <p className="text-sm text-muted-foreground">
          As colunas foram descobertas pelo nome e pelo conteúdo.{" "}
          <button
            type="button"
            className="underline underline-offset-4 hover:text-foreground"
            onClick={() => setPrevia(mapeada)}
            disabled={ocupado}
          >
            Estão erradas? Ajustar
          </button>
        </p>
      ) : null}

      {resultado && !previa ? <Resultado resultado={resultado} /> : null}
    </div>
  );
}

function Resultado({ resultado }: { resultado: ResultadoAnalise }) {
  const cortou = resultado.conversas_no_arquivo > resultado.conversas_analisadas;
  const titulo = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    titulo.current?.focus();
  }, [resultado]);

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <header className="flex flex-col gap-1">
        <h2 ref={titulo} tabIndex={-1} className="text-lg font-medium text-foreground">
          Resultado da análise
        </h2>
        <p className="text-sm text-muted-foreground">
          <span className="num">{resultado.conversas_analisadas}</span> de{" "}
          <span className="num">{resultado.conversas_no_arquivo}</span>{" "}
          atendimento(s) analisado(s).
        </p>
      </header>

      {/* O que ficou de FORA vem antes do resultado, na mesma linha do que a
          importação já faz: silenciar o corte faria o operador achar que
          analisou o arquivo inteiro. */}
      {cortou ? (
        <Alert>
          <AlertTitle>Análise parcial do arquivo</AlertTitle>
          <AlertDescription>
            Foram analisados {resultado.conversas_analisadas} de{" "}
            {resultado.conversas_no_arquivo} atendimentos. Cada análise aceita
            até 10 atendimentos e 40 mensagens do cliente, preservando
            atendimentos inteiros. Divida o restante em arquivos menores para
            analisar o que ficou de fora.
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
                <li key={linha.numero_linha} className="text-sm break-words">
                  <span className="num">linha {linha.numero_linha}</span>:{" "}
                  {linha.motivo}
                </li>
              ))}
            </ul>
            {resultado.rejeitadas.length < resultado.total_rejeitadas ? (
              <p className="mt-2">
                Os motivos exibidos cobrem apenas parte das linhas rejeitadas.
              </p>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      {resultado.analises.map((analise, indice) => (
        <Analise
          key={analise.conversa.id}
          analise={analise}
          referencia={resultado.referencia_conversas}
          temTempo={resultado.tem_tempo}
          dominante={indice === 0}
          leitura={indice === 0 ? (
            <Alert>
              <AlertTitle>Lido como {resultado.formato}</AlertTitle>
              <AlertDescription>
                {resultado.avisos.length > 0 ? (
                  <ul className="flex flex-col gap-1">
                    {resultado.avisos.map((aviso) => <li key={aviso}>{aviso}</li>)}
                  </ul>
                ) : "Nada precisou ser inferido na leitura."}
              </AlertDescription>
            </Alert>
          ) : null}
        />
      ))}
    </div>
  );
}

function Medida({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <dt className="text-sm text-muted-foreground">{rotulo}</dt>
      <dd className="num text-base leading-snug break-words text-foreground">{valor}</dd>
    </div>
  );
}

function Analise({
  analise,
  referencia,
  temTempo,
  dominante,
  leitura,
}: {
  analise: ConversaAnalisada;
  referencia: number;
  temTempo: boolean;
  dominante: boolean;
  leitura: ReactNode;
}) {
  // Duas causas MUITO diferentes para não haver nota, e a tela precisa
  // distinguir: "o cliente não falou" é um fato sobre o atendimento; "o
  // arquivo não tem horário" é um limite do que foi enviado. Dizer a mesma
  // frase nos dois casos mandaria procurar problema no lugar errado.
  const [tudoAberto, setTudoAberto] = useState(false);
  const [detalhesDaAnalise, setDetalhesDaAnalise] = useState(false);
  const transcricaoId = useId();
  const semNota = analise.score === null;
  // SEM HORARIO, o servidor fabrica `inicio + 1 s por mensagem` so para a ordem
  // existir e o modelo canonico aceitar a conversa -- e anula a nota. Os
  // TEMPOS derivados desse relogio inventado (duracao, esperas, hora de cada
  // fala) continuam vindo na resposta, e a tela os exibia ao lado de "o
  // arquivo nao traz horario": "Duração 7 s" de uma conversa cujo tempo
  // ninguem mediu. Aqui eles viram ausencia nomeada, nunca zero e nunca o
  // numero fabricado.
  const SEM_HORARIO = "sem horário";
  const motivoSemNota = !temTempo
    ? "o arquivo não traz horário"
    : analise.motivo_sem_sinal === "so_cortesia"
      ? "o cliente só usou fórmulas de cortesia"
      : "sem fala do cliente";

  return (
    <div className="flex min-w-0 flex-col gap-4 break-words">
      <Painel
        titulo={`Resultado — ${analise.conversa.id}`}
        nivel={dominante ? "dominante" : "apoio"}
        className="[&_h2]:min-w-0 [&_h2]:break-all"
        legenda="A nota sai do fusor, que aprendeu com 39 medidas das sete famílias do vetor — texto, emoji, tempo, emoção, léxico, estilo e incongruência. Emoção aparece na transcrição abaixo e também entra nessa conta; a ironia aparece junto, mas é leitura por mensagem — desde 04/09/2026 não pesa mais na nota."
      >
        <dl className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          <div className="flex min-w-0 flex-col gap-1.5">
            <dt className="rotulo-instrumento">
              Nota estimada
            </dt>
            <dd className="flex flex-col items-start gap-1.5">
              {/* A nota e do SERVIDOR; nula = display APAGADO + o motivo por
                  extenso, nunca 0. O motivo distingue "o cliente nao falou" de
                  "o arquivo nao traz horario": sao problemas em lugares
                  diferentes. */}
              <NotaInferida nota={semNota ? null : analise.nota}  />
              {semNota ? (
                <span className="text-sm text-muted-foreground">
                  {ROTULO_SEM_SINAL} — {motivoSemNota}
                </span>
              ) : (
                <EtiquetaCategoria categoria={analise.categoria} />
              )}
            </dd>
          </div>
          <div className="flex min-w-0 flex-col gap-0.5">
            <dt className="text-sm text-muted-foreground">Desfecho</dt>
            <dd
              className="text-base leading-snug text-foreground"
              title={EXPLICACAO_DESFECHO[analise.desfecho]}
            >
              {ROTULO_DESFECHO[analise.desfecho]}
            </dd>
          </div>
          <Medida
            rotulo="Mensagens"
            valor={`${analise.qtd_mensagens} (${analise.qtd_cliente} do cliente)`}
          />
        </dl>
        <details className="mt-5 border-t border-linha pt-3">
          <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
            Dados do atendimento
          </summary>
          <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Medida
            rotulo="Duração"
            valor={temTempo ? formatarSegundos(analise.duracao_s) : SEM_HORARIO}
          />
          <Medida
            rotulo="1ª resposta"
            valor={
              temTempo
                ? formatarEsperaOuTraco(analise.latencia_primeira_resposta_s)
                : SEM_HORARIO
            }
          />
          <Medida
            rotulo="Resposta do bot (mediana)"
            valor={
              temTempo
                ? formatarEsperaOuTraco(analise.latencia_mediana_bot_s)
                : SEM_HORARIO
            }
          />
          <Medida
            rotulo="Resposta humana (mediana)"
            valor={
              temTempo
                ? formatarEsperaOuTraco(analise.latencia_mediana_humano_s)
                : SEM_HORARIO
            }
          />
          <Medida rotulo="Canal" valor={analise.conversa.canal} />
          </dl>
        </details>
      </Painel>
      {leitura}


      <Painel
        titulo="Conversa"
        legenda="O grifo é medido por oclusão: apaga-se a palavra e pergunta-se de novo ao modelo. Verde empurrou a leitura para satisfeito, vermelho puxou para insatisfeito, e a força da cor é o tamanho do efeito. Ressalva do método: apagar uma palavra de dentro de uma expressão fixa deixa um fragmento que ninguém escreveria — o peso é verdadeiro sobre o que o modelo faz, e não deve ser lido como “esta palavra significa insatisfação”. Só a fala do cliente recebe peso: o classificador foi treinado em texto de cliente, e pontuar o roteiro do bot seria número sem lastro. Abrindo os sinais de uma fala aparecem as três probabilidades de satisfação e as oito emoções. Duas ressalvas valem para todas elas: o “desprezo” não é classe treinada — nenhum corpus em português a anota, e ele é derivado da díade raiva + nojo (Plutchik, 1980) pela média geométrica, que exige as duas emoções juntas; e a “ironia” acerta o caso de manual mas marca 6 em 10 falas sinceras de atendimento como irônicas, com 0,999 de confiança, então leia como indício e nunca como veredito. A emoção entra na nota — a ironia, não: desde 04/09/2026 ela é só leitura por mensagem, tirada do vetor do fusor porque em resenha vira detector de sentimento positivo."
        semPadding
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-linha px-5 py-3">
          <Button
            type="button"
            size="sm"
            variant="outline"
            aria-expanded={detalhesDaAnalise}
            aria-controls={transcricaoId}
            onClick={() => setDetalhesDaAnalise((atual) => !atual)}
          >
            <IconeDeAcao acao="expandir" />
            {detalhesDaAnalise ? "Ocultar detalhes da análise" : "Mostrar detalhes da análise"}
          </Button>
          {detalhesDaAnalise ? (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setTudoAberto((atual) => !atual)}
            >
              <IconeDeAcao acao="expandir" />
              {tudoAberto ? "Recolher os sinais" : "Abrir todos os sinais"}
            </Button>
          ) : null}
        </div>

        <ol id={transcricaoId} className="flex min-w-0 flex-col">
          {analise.mensagens.map((mensagem) => {
            const doCliente = mensagem.autor === "cliente";
            return (
              <li
                key={mensagem.indice}
                className="flex min-w-0 flex-col gap-2 border-b border-compasso px-5 py-4 last:border-b-0"
              >
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                  <span
                    className={`text-sm font-medium ${doCliente ? "text-dito-texto" : "text-foreground"}`}
                  >
                    {ROTULO_AUTOR[mensagem.autor]}
                  </span>
                  {/* Sem horario no arquivo, o `enviada_em` e ordem fabricada
                      pelo servidor (um segundo por fala), nao hora. */}
                  {temTempo ? (
                    <span className="num text-sm text-muted-foreground">
                      {formatarHora(
                        analise.conversa.mensagens[mensagem.indice].enviada_em,
                      )}
                    </span>
                  ) : null}
                  {detalhesDaAnalise && doCliente && mensagem.prob_satisfeito !== null ? (
                    <span className="num text-sm text-muted-foreground">
                      satisfeito {mensagem.prob_satisfeito.toFixed(2)} ·
                      insatisfeito {mensagem.prob_insatisfeito?.toFixed(2)}
                    </span>
                  ) : null}
                </div>

                <p className="whitespace-pre-wrap break-words text-base leading-relaxed text-foreground">
                  {detalhesDaAnalise ? (
                    <TextoComPesos
                      texto={mensagem.texto}
                      palavras={mensagem.palavras}
                    />
                  ) : mensagem.texto}
                </p>

                {detalhesDaAnalise && doCliente ? (
                  <SinaisDeLeitura mensagem={mensagem} aberto={tudoAberto} />
                ) : null}
              </li>
            );
          })}
        </ol>
      </Painel>

      <details className="min-w-0 border-t border-linha pt-3">
        <summary className="cursor-pointer text-sm font-medium text-foreground">
          Como o resultado foi calculado
        </summary>
        <div className="mt-4 flex min-w-0 flex-col gap-4">
          <Painel
            titulo="Sinais que influenciaram a nota"
            semPadding
          >
            {temTempo ? (
              <PainelContribuicoes
                contribuicoes={analise.contribuicoes}
                sinaisForaDoScore={analise.sinais_fora_do_score}
                totalDeFeatures={Object.keys(analise.importancias).length}
                motivoSemSinal={analise.motivo_sem_sinal}
              />
            ) : (
              // Não decompor a nota ausente usando tempos fabricados pelo leitor.
              <EstadoVazio
                className="m-5"
                titulo="Sem contribuições para esta conversa"
                explicacao="O arquivo não traz horário. Sem horário não há latência, que é um sinal usado para calcular a nota. Por isso não há nota para decompor; a leitura por mensagem continua disponível na conversa acima."
                etapa="enviar o arquivo com uma coluna de data e hora por mensagem"
              />
            )}
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
                className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-compasso px-5 py-2 last:border-b-0"
              >
                <span className="min-w-0 break-words text-sm text-foreground">{item.palavra}</span>
                <span className="flex flex-wrap items-baseline gap-x-4 text-sm text-muted-foreground">
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
      </details>
    </div>
  );
}

/**
 * Tudo que o modelo leu nesta mensagem, atras de um expansor.
 *
 * A API manda as OITO emocoes por mensagem, e esta tela mostrava so a
 * vencedora -- jogava sete fora, e junto com elas as ressalvas do desprezo
 * derivado e da ironia, que o simulador ja exibia.
 *
 * Fechado por padrao dentro de "Mostrar detalhes da analise": uma conversa
 * pode trazer quarenta falas, e oito barras em cada uma tornariam a leitura
 * inicial ilegivel. O controle global abre ou recolhe os sinais de todas
 * as falas sem consultar o modelo novamente.
 *
 * O painel em si e o MESMO componente do simulador: duas copias de um painel
 * que explica um modelo envelhecem separadas, e a que envelhece e sempre a que
 * ninguem olha.
 */
function SinaisDeLeitura({
  mensagem,
  aberto,
}: {
  mensagem: MensagemAnalisada;
  aberto: boolean;
}) {
  const emocaoTop = mensagem.emocao
    ? Object.entries(mensagem.emocao).sort((a, b) => b[1] - a[1])[0]
    : null;

  return (
    // `key` no estado do botao: sem ela, alternar "abrir todas" nao mexeria
    // num `<details>` que o leitor ja abriu ou fechou na mao -- o atributo
    // `open` so vale na montagem. Remontar e o que faz o controle global de
    // fato valer para a transcricao inteira.
    <details key={String(aberto)} open={aberto} className="group">
      <summary className="flex cursor-pointer flex-wrap items-baseline gap-x-3 text-sm text-muted-foreground marker:text-muted-foreground">
        <span>
          leitura por mensagem
        </span>
        {emocaoTop ? (
          <span>
            emoção {emocaoTop[0]}{" "}
            <span className="num">{formatarProbabilidade(emocaoTop[1])}</span>
          </span>
        ) : null}
        {mensagem.prob_ironia !== null ? (
          <span>
            ironia <span className="num">{formatarProbabilidade(mensagem.prob_ironia)}</span>{" "}
            <span>(pouco confiável)</span>
          </span>
        ) : null}
        <span className="group-open:hidden">— ver tudo</span>
      </summary>

      <div className="mt-3 flex flex-col gap-3 border-l border-linha pl-3">
        {/* As três ou nenhuma: o servidor as deriva da MESMA previsão. Um
            `?? 0` aqui desenharia "0% insatisfeito" para uma ausência — a
            invariante 2 — no dia em que esse contrato mudar. */}

        {/* Sem a prosa: ela vale UMA vez, na legenda do painel. Repetida em
            cada uma das dezenas de falas, viraria ruído e pararia de ser lida
            -- o oposto do que uma ressalva existe para fazer. */}
        <CabecasDeLeitura
          classes={
            mensagem.prob_insatisfeito !== null &&
            mensagem.prob_neutro !== null &&
            mensagem.prob_satisfeito !== null
              ? {
                  insatisfeito: mensagem.prob_insatisfeito,
                  neutro: mensagem.prob_neutro,
                  satisfeito: mensagem.prob_satisfeito,
                }
              : null
          }
          emocao={mensagem.emocao}
          ironia={mensagem.prob_ironia}
          compacto
          ressalvas={false}
        />
        <LeituraDeEstilo estilo={mensagem.estilo} />
      </div>
    </details>
  );
}
