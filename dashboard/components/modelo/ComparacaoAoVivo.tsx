"use client";

import { useId, useState } from "react";
import { Play } from "lucide-react";
import {
  simularComparacao,
  type ComparacaoAoVivo as Leitura,
  type LeituraAoVivo,
} from "@/lib/api";
import { fracao, milissegundos } from "@/lib/comparacao";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { EstadoVazio } from "@/components/EstadoVazio";

const TETO = 2000;
const PARTIDAS = [
  "ótimo serviço, só levou duas semanas para responder",
  "nossa, resolveu rapidinho, obrigado",
  "que absurdo, cobraram duas vezes e ninguém resolve",
];

const TAREFAS = [
  { chave: "ironia", rotulo: "Ironia" },
  { chave: "emocao", rotulo: "Emoção" },
] as const;

const CLASSES_IRONIA: Record<string, string> = {
  ironico: "irônico",
  "nao-ironico": "não irônico",
};

/**
 * UMA fala, lida agora pelas cabecas que estiverem carregadas no servidor.
 *
 * Isto nao e o laudo: uma frase nao mede modelo nenhum. Serve para ver os dois
 * respondendo a mesma coisa e quanto cada um demora NESTE servidor. Cabeca que
 * nao esta carregada aparece nomeada, com o motivo que o servidor deu --
 * nunca some, e nunca vira um valor.
 */
export function ComparacaoAoVivo() {
  const [texto, setTexto] = useState(PARTIDAS[0]);
  const [resultado, setResultado] = useState<Leitura | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [rodando, setRodando] = useState(false);
  const idCampo = useId();

  const comparar = async () => {
    const limpo = texto.trim();
    if (!limpo) {
      setErro("Digite uma fala: a API recusa texto vazio.");
      setResultado(null);
      return;
    }
    setRodando(true);
    setErro(null);
    setResultado(null);
    const resposta = await simularComparacao(limpo);
    setRodando(false);
    if (resposta.ok) setResultado(resposta.dado);
    else setErro(resposta.erro);
  };

  return (
    <div className="flex w-full min-w-0 flex-col gap-4 px-5 py-4">
      <div className="flex min-w-0 flex-col gap-2">
        <Label htmlFor={idCampo} className="text-xs text-muted-foreground">
          Fala do cliente
        </Label>
        <Textarea
          id={idCampo}
          value={texto}
          onChange={(evento) => {
            setTexto(evento.target.value);
            setResultado(null);
          }}
          onKeyDown={(evento) => {
            if ((evento.metaKey || evento.ctrlKey) && evento.key === "Enter") {
              evento.preventDefault();
              comparar();
            }
          }}
          rows={3}
          maxLength={TETO}
          className="min-w-0 max-w-full resize-y font-normal"
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" size="sm" onClick={comparar} disabled={rodando}>
            <Play aria-hidden />
            {rodando ? "Lendo…" : "Ler com os dois modelos"}
          </Button>
          <span className="text-xs text-muted-foreground">
            ou <kbd className="num">Ctrl</kbd>+<kbd className="num">Enter</kbd>
          </span>
          <span className="num ml-auto text-xs text-muted-foreground">
            {texto.length}/{TETO}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted-foreground">Começar de:</span>
          {PARTIDAS.map((partida) => (
            <Button
              key={partida}
              type="button"
              size="xs"
              variant="outline"
              onClick={() => {
                setTexto(partida);
                setResultado(null);
                setErro(null);
              }}
              className="max-w-full justify-start truncate sm:max-w-[24rem]"
            >
              <span className="truncate">{partida}</span>
            </Button>
          ))}
        </div>
      </div>

      {erro ? (
        <EstadoVazio
          titulo="A leitura lado a lado não rodou"
          explicacao={erro}
          endpoint="POST /modelo/comparacao/simular"
        />
      ) : resultado ? (
        <div className="flex min-w-0 flex-col gap-4" role="status" aria-live="polite">
          {TAREFAS.map(({ chave, rotulo }) => (
            <section key={chave} className="min-w-0 border-t border-linha pt-3">
              <h3 className="rotulo-instrumento mb-2 text-foreground">{rotulo}</h3>
              <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
                <Cabeca nome="BERTimbau fine-tunado" leitura={resultado.tarefas[chave].bertimbau} />
                <Cabeca nome="Laya" leitura={resultado.tarefas[chave].laya} />
              </div>
            </section>
          ))}
          <p className="text-xs leading-relaxed text-muted-foreground">
            Ironia decide em <span className="num">{fracao(resultado.limiar_ironia)}</span> para
            os dois modelos. O tempo é o deste servidor, e a primeira leitura
            depois de ele subir inclui carregar o modelo.
            {resultado.passada_unica
              ? " O BERTimbau está no backend multitarefa: uma passada produz as duas leituras, e o tempo dele é o mesmo nas duas."
              : ""}{" "}
            Esta leitura não é gravada e não altera nenhuma nota.
          </p>
        </div>
      ) : (
        <p className="border border-dashed border-border px-4 py-6 text-xs leading-relaxed text-muted-foreground">
          Nenhuma fala lida. Uma frase não mede modelo: os números da
          comparação estão no laudo acima.
        </p>
      )}
    </div>
  );
}

function Cabeca({ nome, leitura }: { nome: string; leitura: LeituraAoVivo }) {
  if (!leitura.disponivel) {
    return (
      <div className="min-w-0 border border-dashed border-border px-4 py-3">
        <p className="rotulo-instrumento">{nome}</p>
        <p className="mt-2 text-sm">Não carregado neste servidor</p>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{leitura.motivo}</p>
      </div>
    );
  }
  const probabilidade =
    leitura.prob_ironia ?? leitura.probabilidades?.[leitura.classe] ?? null;
  return (
    <div className="min-w-0 border border-linha px-4 py-3">
      <p className="rotulo-instrumento">{nome}</p>
      <p className="mt-2 text-sm font-medium">
        {CLASSES_IRONIA[leitura.classe] ?? leitura.classe}
      </p>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <dt>{leitura.prob_ironia === undefined ? "Probabilidade da classe" : "Probabilidade de ironia"}</dt>
        <dd className="num text-right text-medido-texto">{fracao(probabilidade)}</dd>
        <dt>Tempo</dt>
        <dd className="num text-right text-medido-texto">{milissegundos(leitura.ms)}</dd>
        <dt>Executor</dt>
        <dd className="num text-right text-foreground">{leitura.executor}</dd>
      </dl>
    </div>
  );
}
