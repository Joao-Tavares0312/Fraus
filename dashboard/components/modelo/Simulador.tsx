"use client";

import { useId, useRef, useState } from "react";
import { Play, RotateCcw } from "lucide-react";
import { simularTexto, type Simulacao } from "@/lib/api";
import { CabecasDeLeitura, LeituraDeEstilo } from "@/components/CabecasDeLeitura";
import { formatarNumero } from "@/lib/formato";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { EstadoVazio } from "@/components/EstadoVazio";
import { ValorNumerico } from "@/components/ValorNumerico"

/** Teto de `/modelo/simular`. Repetido aqui so para avisar ANTES do 400. */
const TETO = 2000;

const CLASSES = [
  {
    chave: "prob_insatisfeito",
    rotulo: "Insatisfeito",
    cor: "var(--detrator)",
    texto: "text-detrator-texto",
  },
  {
    chave: "prob_neutro",
    rotulo: "Neutro",
    cor: "var(--neutro)",
    texto: "text-neutro-texto",
  },
  {
    chave: "prob_satisfeito",
    rotulo: "Satisfeito",
    cor: "var(--promotor)",
    texto: "text-promotor-texto",
  },
] as const;

/**
 * Frases de PARTIDA, nao de exibicao.
 *
 * Elas nunca aparecem como resultado: preenchem o campo e o operador roda a
 * simulacao de verdade. Nenhum numero desta tela e simulado -- o que se ve e
 * sempre a resposta de `POST /modelo/simular`.
 *
 * A primeira e a tese do produto em uma linha: educada na superficie, e
 * exatamente o caso que uma pesquisa de NPS declarada nao captura.
 */
const PARTIDAS = [
  "ok, obrigado 🙂",
  "ja e a terceira vez que eu explico a mesma coisa e ninguem resolve 😡",
  "perfeito, resolveu na hora, muito obrigado! 😄",
];

/**
 * Simulador ao vivo: o melhor momento de demonstracao do produto.
 *
 * Digita-se uma frase, o servidor roda o classificador e devolve as tres
 * probabilidades na ORDEM FIXA das classes (0 insatisfeito, 1 neutro, 2
 * satisfeito -- invariante 8) mais os emojis detectados com a posicao relativa
 * de cada um.
 *
 * A posicao relativa nao e enfeite: um 🙂 no fim da frase e o caso que da nome
 * ao produto, e o sinal de emoji leva a posicao em conta justamente por isso.
 * Por isso ela aparece desenhada num trilho, e nao so como numero.
 *
 * A predicao vem inteira do servidor. O front nao classifica nada -- fazer
 * isso duplicaria a regra e e o mesmo erro que ja causou divergencia de
 * arredondamento na nota.
 */
export function Simulador({ onResultado }: { onResultado?: (resultado: Simulacao | null) => void }) {
  const [texto, setTexto] = useState(PARTIDAS[0]);
  const [resultado, setResultado] = useState<Simulacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [rodando, setRodando] = useState(false);
  // O estado desabilita o botão; a ref bloqueia atalhos no mesmo ciclo de render.
  const emCurso = useRef(false);
  const idCampo = useId();

  const simular = async () => {
    if (emCurso.current) return;
    const limpo = texto.trim();
    setResultado(null);
    onResultado?.(null);
    setErro(null);
    if (!limpo) {
      setErro("Digite alguma coisa: a API recusa texto vazio.");
      return;
    }
    emCurso.current = true;
    setRodando(true);
    try {
      const resposta = await simularTexto(limpo);
      if (resposta.ok) {
        setResultado(resposta.dado);
        onResultado?.(resposta.dado);
      } else {
        setErro(resposta.erro);
      }
    } catch (erro) {
      setErro(erro instanceof Error ? erro.message : "Não foi possível classificar a frase.");
    } finally {
      emCurso.current = false;
      setRodando(false);
    }
  };

  const excedeu = texto.length > TETO;

  return (
    <div className="flex min-w-0 flex-col gap-4 py-4" aria-busy={rodando}>
      <div className="flex flex-col gap-2">
        <Label htmlFor={idCampo} className="text-sm text-muted-foreground">
          Fala do cliente
        </Label>
        <Textarea
          id={idCampo}
          value={texto}
          onChange={(evento) => setTexto(evento.target.value)}
          onKeyDown={(evento) => {
            // Ctrl/Cmd+Enter roda: numa demonstracao ao vivo, tirar a mao do
            // teclado para clicar quebra o ritmo.
            if ((evento.metaKey || evento.ctrlKey) && evento.key === "Enter") {
              evento.preventDefault();
              simular();
            }
          }}
          rows={3}
          maxLength={TETO}
          placeholder="ok, obrigado 🙂"
          className="resize-y font-normal text-dito-texto"
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" size="sm" className="min-h-11 px-4 text-sm motion-reduce:transition-none" onClick={simular} disabled={rodando}>
            <Play aria-hidden />
            {rodando ? "Classificando…" : "Classificar"}
          </Button>
          <span className="text-xs text-muted-foreground">
            ou <kbd className="num">Ctrl</kbd>+<kbd className="num">Enter</kbd>
          </span>
          <span
            className={`num ml-auto text-xs ${excedeu ? "text-destructive" : "text-muted-foreground"}`}
          >
            {texto.length}/{TETO}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-muted-foreground">Começar de:</span>
        {PARTIDAS.map((partida) => (
          <Button
            key={partida}
            type="button"
            size="xs"
            variant="outline"
            disabled={rodando}
            onClick={() => {
              setTexto(partida);
              setResultado(null);
              onResultado?.(null);
              setErro(null);
            }}
            className="h-auto min-h-11 max-w-full justify-start px-3 py-2 text-left text-sm whitespace-normal motion-reduce:transition-none"
          >
            <RotateCcw aria-hidden />
            <span className="min-w-0">{partida}</span>
          </Button>
        ))}
      </div>

      <p role="status" className="sr-only">
        {rodando ? "Classificando a frase. Aguarde." : resultado ? "Classificação concluída." : ""}
      </p>

      {erro ? (
        <div role="alert">
          <EstadoVazio
            titulo="A simulação não rodou"
            explicacao={erro}
            endpoint="POST /modelo/simular"
          />
        </div>
      ) : resultado === null ? (
        <p className="chanfro border border-dashed border-border px-4 py-6 text-sm leading-relaxed text-muted-foreground">
          {rodando ? "Classificando a frase; os resultados anteriores foram limpos." : "Nada foi classificado ainda. Escolha um exemplo ou escreva uma frase e use Classificar. Nenhum resultado é preenchido automaticamente."}
        </p>
      ) : (
        <Resultado resultado={resultado} />
      )}
    </div>
  );
}

function Resultado({ resultado }: { resultado: Simulacao }) {
  const valores = CLASSES.map((classe) => ({
    ...classe,
    valor: resultado[classe.chave],
  }));
  const vencedora = valores.reduce((melhor, atual) =>
    atual.valor > melhor.valor ? atual : melhor,
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="border-b border-border pb-3">
        <p className="text-sm text-muted-foreground">Frase classificada</p>
        <blockquote className="mt-1 break-words text-base text-dito-texto">
          {resultado.texto}
        </blockquote>
      </div>
      <div className="flex flex-col gap-2">
        <p className="flex flex-wrap items-baseline gap-2 text-sm">
          <span className="text-muted-foreground">Classe mais provável:</span>
          <span className={`font-semibold ${vencedora.texto}`}>
            {vencedora.rotulo}
          </span>
          <span className="inline-flex items-end gap-1">
            <ValorNumerico valor={formatarNumero(vencedora.valor * 100)} rotulo={`probabilidade da classe ${vencedora.rotulo}, em porcento`} />
            <span className="num text-muted-foreground">%</span>
          </span>
        </p>

        {/* Barra empilhada na ordem fixa das classes. A largura E a
            probabilidade -- nao ha eixo escondido. */}
        <div
          className="flex h-2.5 w-full gap-px overflow-hidden rounded-sm bg-muted"
          role="img"
          aria-label={valores
            .map(
              (classe) =>
                `${classe.rotulo} ${formatarNumero(classe.valor * 100)}%`,
            )
            .join(", ")}
        >
          {valores.map((classe) => (
            <span
              key={classe.chave}
              style={{
                width: `${classe.valor * 100}%`,
                background: classe.cor,
              }}
            />
          ))}
        </div>

        <ul className="flex flex-wrap gap-x-5 gap-y-1">
          {valores.map((classe) => (
            <li key={classe.chave} className="flex items-baseline gap-1.5">
              <span
                aria-hidden
                className="size-2 shrink-0 translate-y-px"
                style={{ background: classe.cor }}
              />
              <span className="text-xs text-muted-foreground">
                {classe.rotulo}
              </span>
              <span className={`num text-xs ${classe.texto}`}>
                {formatarNumero(classe.valor * 100)}%
              </span>
            </li>
          ))}
        </ul>
      </div>

      <EmojisDetectados resultado={resultado} />
      <OutrasCabecas resultado={resultado} />
    </div>
  );
}

/**
 * Emocao e ironia da frase -- as duas cabecas de LEITURA POR FRASE.
 *
 * O painel em si mora em `CabecasDeLeitura`, compartilhado com a analise de
 * arquivo: as duas telas leem os mesmos campos da mesma API, e manter duas
 * copias faria uma delas envelhecer sem a ressalva que a outra ja tem.
 *
 * Elas entram DEPOIS de uma linha e nunca dentro da barra de classes. Para a
 * emocao, a media por conversa e que entra nas 39 features do fusor (desde
 * 21/08/2026), nao o numero desta frase isolada. Para a IRONIA a separacao e
 * ainda mais literal: desde 04/09/2026 ela nao entra no vetor de jeito nenhum
 * -- e leitura, nao nota. Encostar "ironia 99%" na barra de satisfacao
 * convidaria a ler esta frase como causa direta de uma nota que ela nao move.
 */
function OutrasCabecas({ resultado }: { resultado: Simulacao }) {
  if (!resultado.emocao && resultado.prob_ironia == null && !resultado.estilo) return null;
  return (
    <div className="border-t border-linha pt-3">
      {/* Uma frase só: as sete emoções à vista, nada recolhido. */}
      <CabecasDeLeitura
        emocao={resultado.emocao ?? null}
        ironia={resultado.prob_ironia ?? null}
        recolher={false}
      />
      <LeituraDeEstilo estilo={resultado.estilo ?? null} />
    </div>
  );
}

/**
 * Os emojis achados na frase, com o score do lexicon e a POSICAO RELATIVA.
 *
 * O trilho e a frase inteira, da esquerda (inicio) para a direita (fim), e
 * cada emoji fica onde ele apareceu. Emoji e fala, entao o trilho veste ambar.
 */
function EmojisDetectados({ resultado }: { resultado: Simulacao }) {
  if (resultado.emojis.length === 0) {
    return (
      <p className="text-xs leading-relaxed text-muted-foreground">
        Nenhum emoji detectado nesta frase. As probabilidades acima são da
        cabeça de satisfação, não do fusor.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-xs font-medium text-foreground">
        Emojis detectados{" "}
        <span className="font-normal text-muted-foreground">
          — score do lexicon e onde cada um caiu na frase
        </span>
      </h3>

      <div className="relative h-8 w-full rounded-sm bg-dito-fraco">
        <span
          aria-hidden
          className="absolute inset-y-0 left-0 w-px bg-border"
        />
        <span
          aria-hidden
          className="absolute inset-y-0 right-0 w-px bg-border"
        />
        {resultado.emojis.map((emoji, indice) => (
          <span
            key={`${emoji.emoji}-${indice}`}
            title={`${emoji.emoji} · score ${formatarNumero(emoji.score, 3)} · posição ${formatarNumero(emoji.posicao_relativa, 2)}`}
            className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 text-lg leading-none"
            style={{ left: `${emoji.posicao_relativa * 100}%` }}
          >
            {emoji.emoji}
          </span>
        ))}
      </div>
      <div className="flex justify-between text-[0.6875rem] text-muted-foreground">
        <span>início da frase</span>
        <span>fim da frase</span>
      </div>

      <ul className="flex flex-wrap gap-2">
        {resultado.emojis.map((emoji, indice) => (
          <li
            key={`item-${emoji.emoji}-${indice}`}
            className="inline-flex items-center gap-2 rounded-sm border border-border px-2 py-1 text-xs"
          >
            <span aria-hidden className="text-base leading-none">
              {emoji.emoji}
            </span>
            <span
              className={`num ${
                emoji.score > 0.05
                  ? "text-promotor-texto"
                  : emoji.score < -0.05
                    ? "text-detrator-texto"
                    : "text-muted-foreground"
              }`}
            >
              {emoji.score > 0 ? "+" : ""}
              {formatarNumero(emoji.score, 3)}
            </span>
            <span className="num text-muted-foreground">
              pos. {formatarNumero(emoji.posicao_relativa, 2)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
