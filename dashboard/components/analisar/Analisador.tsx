"use client";

import { useRef, useState } from "react";
import { FileText, RefreshCw, Upload } from "lucide-react";
import {
  analisarUpload,
  previaUpload,
  salvarPerfilMapeamento,
  type ConversaAnalisada,
  type MapeamentoConfirmado,
  type OrdemData,
  type PreviaLeitura,
  type MensagemAnalisada,
  type ResultadoAnalise,
} from "@/lib/api";
import {
  BarraDeClasses,
  CabecasDeLeitura,
  LeituraDeEstilo,
} from "@/components/CabecasDeLeitura";
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
import { PainelContribuicoes } from "@/components/PainelContribuicoes";
import { TextoComPesos } from "./TextoComPesos";
import { ConferenciaDeColunas } from "./ConferenciaDeColunas";

/** Teto do lado do cliente, espelhando o do servidor -- recusa antes de subir. */
const TETO_BYTES = 200_000;

const ACEITOS = ".csv,.tsv,.xlsx,.xlsm,.json,.jsonl,.txt,.docx,.pdf";

export function Analisador() {
  const entrada = useRef<HTMLInputElement>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [arquivo, setArquivo] = useState<string | null>(null);
  /** O último arquivo escolhido, para "tentar de novo" sem reabrir o seletor. */
  const [ultimo, setUltimo] = useState<File | null>(null);
  const [resultado, setResultado] = useState<ResultadoAnalise | null>(null);
  /** Leitura inferida aguardando conferência. Nula quando o formato é conhecido. */
  const [previa, setPrevia] = useState<PreviaLeitura | null>(null);
  /** Falha ao gravar o perfil — não impede a análise, mas não pode sumir. */
  const [avisoPerfil, setAvisoPerfil] = useState<string | null>(null);
  /**
   * Contador, não booleano: dragenter/dragleave disparam para CADA filho que
   * o cursor cruza, e um booleano apagaria o realce ao passar sobre o ícone
   * dentro da própria área.
   */
  const [arrastando, setArrastando] = useState(0);

  async function analisar(escolhido: File) {
    setErro(null);
    setResultado(null);
    setPrevia(null);
    setAvisoPerfil(null);
    setArquivo(escolhido.name);
    setUltimo(escolhido);

    if (escolhido.size > TETO_BYTES) {
      setErro(
        `O arquivo tem ${Math.round(escolhido.size / 1024).toLocaleString("pt-BR")} kB, acima do limite de ${Math.round(TETO_BYTES / 1024).toLocaleString("pt-BR")} kB. Esta tela examina um atendimento por vez; para um lote inteiro, use a importação em Integrações.`,
      );
      return;
    }

    // A prévia vem ANTES do modelo: é só leitura, responde rápido e diz se as
    // colunas foram inferidas. Formato conhecido segue direto para a análise;
    // inferido para na conferência — coluna errada não dá erro, dá nota errada.
    setOcupado(true);
    const lida = await previaUpload(escolhido);
    if (!lida.ok) {
      setOcupado(false);
      setErro(lida.erro);
      return;
    }
    if (lida.dado.mapeamento) {
      setOcupado(false);
      setPrevia(lida.dado);
      return;
    }
    const resposta = await analisarUpload(escolhido);
    setOcupado(false);
    if (resposta.ok) setResultado(resposta.dado);
    else setErro(resposta.erro);
  }

  async function ajustar(mapeamento: MapeamentoConfirmado, ordemData: OrdemData | null) {
    if (!ultimo) return;
    setOcupado(true);
    const lida = await previaUpload(ultimo, { mapeamento, ordemData });
    setOcupado(false);
    if (lida.ok) {
      setErro(null);
      setPrevia(lida.dado);
    } else {
      setErro(lida.erro);
    }
  }

  async function confirmar(
    mapeamento: MapeamentoConfirmado,
    ordemData: OrdemData | null,
    salvarComo: string | null,
  ) {
    if (!ultimo || !previa?.mapeamento) return;
    setOcupado(true);
    setErro(null);
    if (salvarComo) {
      const salvo = await salvarPerfilMapeamento({
        nome: salvarComo,
        colunas: previa.mapeamento.colunas,
        papeis: mapeamento,
        ordem_data: ordemData,
      });
      if (!salvo.ok) {
        setAvisoPerfil(`O perfil não foi salvo: ${salvo.erro} A análise seguiu com as colunas escolhidas.`);
      }
    }
    const resposta = await analisarUpload(ultimo, { mapeamento, ordemData });
    setOcupado(false);
    if (resposta.ok) {
      setPrevia(null);
      setResultado(resposta.dado);
    } else {
      setErro(resposta.erro);
    }
  }

  async function aoEscolher(evento: React.ChangeEvent<HTMLInputElement>) {
    const escolhido = evento.target.files?.[0];

    // Zerar o valor do input É O CONSERTO, não faxina. Um `<input type=file>`
    // só dispara `change` quando o valor MUDA -- escolher o mesmo arquivo de
    // novo não dispara nada, e a tela ficava parada mostrando o erro anterior
    // sem nenhum sinal de que o clique foi ignorado. Justamente o caso mais
    // comum: corrigir o arquivo e reenviar com o mesmo nome.
    evento.target.value = "";

    if (escolhido) await analisar(escolhido);
  }

  return (
    <div className="flex flex-col gap-4">
      <Painel
        titulo="Arquivo do atendimento"
        legenda="Nada aqui entra no banco: nem a conversa, nem a nota, nem o arquivo. Analisar não muda o NPS de ninguém — é a diferença entre esta tela e a importação. O conteúdo é lido no seu navegador e interpretado em memória pelo servidor; nenhum byte é gravado em disco."
      >
        <div className="flex flex-col gap-3 px-5 py-4">
          <div className="text-sm text-muted-foreground">
            <p>Leio planilha, JSON, WhatsApp e transcrição — e descubro as colunas sozinho:</p>
            <ul className="mt-1.5 flex flex-col gap-1 text-xs">
              <li>
                <strong className="text-foreground">.csv</strong>,{" "}
                <strong className="text-foreground">.xlsx</strong> e{" "}
                <strong className="text-foreground">.json</strong> — qualquer
                estrutura com uma coluna de fala e uma de quem falou. Reconheço
                o formato do Fraus e o export da Totalk; nos outros,{" "}
                <strong>infiro</strong> qual coluna é texto, autor, data e
                conversa, e o resultado diz o que inferi. Com horário, a
                conversa recebe nota.
              </li>
              <li>
                <strong className="text-foreground">.txt</strong> do{" "}
                <em>Exportar conversa</em> do WhatsApp — traz horário, recebe
                nota; quem abre a conversa é lido como cliente.
              </li>
              <li>
                <strong className="text-foreground">.docx</strong>,{" "}
                <strong className="text-foreground">.pdf</strong> e .txt em
                prosa — transcrição em linhas{" "}
                <code className="num">Autor: mensagem</code>. Sem horário no
                texto <strong>não há nota</strong>, só a leitura por mensagem —
                o porquê aparece no resultado.
              </li>
            </ul>
          </div>

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
            className="group flex flex-col items-center gap-2 rounded-md border border-dashed border-input px-6 py-8 text-center transition-colors duration-200 ease-fluid data-[arrastando]:border-primary data-[arrastando]:bg-primary/5"
          >
            <input
              ref={entrada}
              type="file"
              accept={ACEITOS}
              className="sr-only"
              onChange={aoEscolher}
            />
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
            >
              {ocupado ? "Analisando…" : "Escolher arquivo"}
            </Button>
            {arquivo ? (
              <span className="num mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
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

      {/* O erro carrega o MOTIVO e as duas saídas: corrigir e reenviar o mesmo
          arquivo, ou escolher outro. Recusa que só diz "não foi possível"
          deixa a pessoa sem próximo passo — e o arquivo errado é o caso comum,
          porque cada um exporta do sistema que tem. */}
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
                  Tentar de novo com este arquivo
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
          nomeArquivo={arquivo}
          aoAjustar={ajustar}
          aoConfirmar={confirmar}
          aoCancelar={() => {
            setPrevia(null);
            entrada.current?.click();
          }}
        />
      ) : null}

      {avisoPerfil ? (
        <Alert>
          <AlertTitle>Perfil de mapeamento</AlertTitle>
          <AlertDescription>{avisoPerfil}</AlertDescription>
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
      {/* Como o arquivo foi ENTENDIDO vem antes de tudo. Uma análise cuja
          procedência não aparece é número sem lastro: o mesmo CSV pode ser
          lido como formato do Fraus ou como export da Totalk, e as duas
          leituras inferem coisas diferentes. */}
      <Alert>
        <AlertTitle>Lido como {resultado.formato}</AlertTitle>
        <AlertDescription>
          {!resultado.tem_tempo ? (
            <p className="mb-1 text-warning-rich-text">
              Sem nota para a conversa — o arquivo não traz horário.
            </p>
          ) : null}
          {resultado.avisos.length > 0 ? (
            <ul className="flex flex-col gap-1">
              {resultado.avisos.map((aviso) => (
                <li key={aviso}>{aviso}</li>
              ))}
            </ul>
          ) : (
            "Nada precisou ser inferido na leitura."
          )}
        </AlertDescription>
      </Alert>

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
          temTempo={resultado.tem_tempo}
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
  temTempo,
}: {
  analise: ConversaAnalisada;
  referencia: number;
  temTempo: boolean;
}) {
  // Duas causas MUITO diferentes para não haver nota, e a tela precisa
  // distinguir: "o cliente não falou" é um fato sobre o atendimento; "o
  // arquivo não tem horário" é um limite do que foi enviado. Dizer a mesma
  // frase nos dois casos mandaria procurar problema no lugar errado.
  const [tudoAberto, setTudoAberto] = useState(false);
  const semNota = analise.score === null;
  const motivoSemNota = !temTempo
    ? "o arquivo não traz horário"
    : "sem fala do cliente";

  return (
    <div className="flex flex-col gap-4">
      <Painel
        titulo={`Resultado — ${analise.conversa.id}`}
        legenda="A nota sai do fusor, que aprendeu com 38 medidas das sete famílias do vetor — texto, emoji, tempo, emoção, léxico, estilo e incongruência. Emoção aparece na transcrição abaixo e também entra nessa conta; a ironia aparece junto, mas é leitura por mensagem — desde 04/09/2026 não pesa mais na nota."
      >
        <dl className="grid grid-cols-2 gap-x-6 gap-y-4 px-5 py-4 sm:grid-cols-4">
          <div className="flex min-w-0 flex-col gap-1">
            <dt className="text-xs text-muted-foreground">Nota inferida</dt>
            <dd className="flex items-baseline gap-2">
              {semNota ? (
                <span className="text-sm text-muted-foreground">
                  {motivoSemNota}
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
        titulo="Contribuições das features nesta conversa"
        legenda="Com sinal, ordenadas por magnitude. Isto é `contribuicoes` — o que pesou NESTA conversa —, não `importancias`, que é o peso global do modelo."
        semPadding
      >
        <PainelContribuicoes
          contribuicoes={analise.contribuicoes}
          sinaisForaDoScore={analise.sinais_fora_do_score}
          totalDeFeatures={Object.keys(analise.importancias).length}
        />
      </Painel>

      <Painel
        titulo="A conversa, palavra a palavra"
        legenda="O grifo é medido por oclusão: apaga-se a palavra e pergunta-se de novo ao modelo. Verde empurrou a leitura para satisfeito, vermelho puxou para insatisfeito, e a força da cor é o tamanho do efeito. Ressalva do método: apagar uma palavra de dentro de uma expressão fixa deixa um fragmento que ninguém escreveria — o peso é verdadeiro sobre o que o modelo faz, e não deve ser lido como “esta palavra significa insatisfação”. Só a fala do cliente recebe peso: o classificador foi treinado em texto de cliente, e pontuar o roteiro do bot seria número sem lastro. Abrindo os sinais de uma fala aparecem as três probabilidades de satisfação e as oito emoções. Duas ressalvas valem para todas elas: o “desprezo” não é classe treinada — nenhum corpus em português a anota, e ele é derivado da díade raiva + nojo (Plutchik, 1980) pela média geométrica, que exige as duas emoções juntas; e a “ironia” acerta o caso de manual mas marca 6 em 10 falas sinceras de atendimento como irônicas, com 0,999 de confiança, então leia como indício e nunca como veredito. A emoção entra na nota — a ironia, não: desde 04/09/2026 ela é só leitura por mensagem, tirada do vetor do fusor porque em resenha vira detector de sentimento positivo."
        semPadding
      >
        {/* Abre as oito emoções de TODAS as falas de uma vez. Existe porque a
            escolha entre "resumo em uma linha" e "detalhe completo" é do
            leitor, não minha: numa conversa de quarenta mensagens o detalhe
            aberto por padrão é ilegível, e fechado sem este botão daria
            quarenta cliques para ver o que a API já mandou. */}
        <div className="flex justify-end border-b border-linha px-5 py-2">
          <Button
            type="button"
            size="xs"
            variant="ghost"
            onClick={() => setTudoAberto((atual) => !atual)}
          >
            {tudoAberto ? "Recolher os sinais" : "Abrir todos os sinais"}
          </Button>
        </div>

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

                {doCliente && (mensagem.emocao || mensagem.prob_ironia !== null) ? (
                  <SinaisDeLeitura mensagem={mensagem} aberto={tudoAberto} />
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
 * Tudo que o modelo leu nesta mensagem, atras de um expansor.
 *
 * A API manda as OITO emocoes por mensagem, e esta tela mostrava so a
 * vencedora -- jogava sete fora, e junto com elas as ressalvas do desprezo
 * derivado e da ironia, que o simulador ja exibia.
 *
 * POR QUE FECHADO POR PADRAO, e nao aberto como no simulador: o simulador
 * analisa UMA frase; aqui uma conversa tem quarenta mensagens, e oito barras
 * em cada uma dariam trezentas barras numa pagina so. A linha de resumo
 * continua mostrando o essencial sem clique -- emocao vencedora e ironia --,
 * e o detalhe fica a um clique de distancia em vez de existir so na API.
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
      <summary className="flex cursor-pointer flex-wrap items-baseline gap-x-3 text-xs text-muted-foreground marker:text-muted-foreground">
        <span className="text-[11px] uppercase tracking-wide">
          leitura por frase
        </span>
        {emocaoTop ? (
          <span>
            emoção {emocaoTop[0]}{" "}
            <span className="num">{emocaoTop[1].toFixed(2)}</span>
          </span>
        ) : null}
        {mensagem.prob_ironia !== null ? (
          <span>
            ironia <span className="num">{mensagem.prob_ironia.toFixed(2)}</span>{" "}
            <span>(pouco confiável)</span>
          </span>
        ) : null}
        <span className="group-open:hidden">— ver tudo</span>
      </summary>

      <div className="mt-3 flex flex-col gap-3 border-l border-linha pl-3">
        {mensagem.prob_satisfeito !== null ? (
          <BarraDeClasses
            insatisfeito={mensagem.prob_insatisfeito ?? 0}
            neutro={mensagem.prob_neutro ?? 0}
            satisfeito={mensagem.prob_satisfeito}
          />
        ) : null}
        {/* Sem a prosa: ela vale UMA vez, na legenda do painel. Repetida em
            cada uma das dezenas de falas, viraria ruído e pararia de ser lida
            -- o oposto do que uma ressalva existe para fazer. */}
        <CabecasDeLeitura
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
