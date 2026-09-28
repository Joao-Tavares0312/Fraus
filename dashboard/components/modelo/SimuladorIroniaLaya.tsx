"use client";

import { useId, useState } from "react";
import { Play, RotateCcw } from "lucide-react";
import { simularIroniaLaya, type SimulacaoIroniaLaya } from "@/lib/api";
import { formatarNumero } from "@/lib/formato";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { EstadoVazio } from "@/components/EstadoVazio";

const TETO = 2000;
const PARTIDAS = [
  "ótimo serviço, só levou duas semanas para responder",
  "nossa, resolveu rapidinho, obrigado",
  "perfeito, cancelaram meu pedido sem avisar",
];

export function SimuladorIroniaLaya() {
  const [texto, setTexto] = useState(PARTIDAS[0]);
  const [resultado, setResultado] = useState<SimulacaoIroniaLaya | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [rodando, setRodando] = useState(false);
  const idCampo = useId();

  const simular = async () => {
    const limpo = texto.trim();
    if (!limpo) {
      setErro("Digite uma fala: a API recusa texto vazio.");
      setResultado(null);
      return;
    }
    setRodando(true);
    setErro(null);
    const resposta = await simularIroniaLaya(limpo);
    setRodando(false);
    if (resposta.ok) setResultado(resposta.dado);
    else {
      setErro(resposta.erro);
      setResultado(null);
    }
  };

  return (
    <div className="flex min-w-0 flex-col gap-4 px-5 py-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor={idCampo} className="text-xs text-muted-foreground">
          Fala do cliente
        </Label>
        <Textarea
          id={idCampo}
          value={texto}
          onChange={(evento) => setTexto(evento.target.value)}
          onKeyDown={(evento) => {
            if ((evento.metaKey || evento.ctrlKey) && evento.key === "Enter") {
              evento.preventDefault();
              simular();
            }
          }}
          rows={4}
          maxLength={TETO}
          className="resize-y font-normal"
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" size="sm" onClick={simular} disabled={rodando}>
            <Play aria-hidden />
            {rodando ? "Classificando…" : "Classificar ironia"}
          </Button>
          <span className="text-xs text-muted-foreground">
            ou <kbd className="num">Ctrl</kbd>+<kbd className="num">Enter</kbd>
          </span>
          <span className="num ml-auto text-xs text-muted-foreground">
            {texto.length}/{TETO}
          </span>
        </div>
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
            className="max-w-[24rem] justify-start truncate"
          >
            <RotateCcw aria-hidden />
            <span className="truncate">{partida}</span>
          </Button>
        ))}
      </div>

      {erro ? (
        <EstadoVazio
          titulo="A leitura de ironia não rodou"
          explicacao={erro}
          endpoint="POST /modelo/ironia-laya/simular"
        />
      ) : resultado ? (
        <Resultado resultado={resultado} />
      ) : (
        <p className="rounded-lg border border-dashed border-border px-4 py-6 text-xs leading-relaxed text-muted-foreground">
          Nenhuma fala classificada. Esta aba executa somente a cabeça Laya de
          ironia; satisfação, emoção, emojis e fusor não são carregados.
        </p>
      )}
    </div>
  );
}

function Resultado({ resultado }: { resultado: SimulacaoIroniaLaya }) {
  const ironia = resultado.prob_ironia * 100;
  const literal = resultado.prob_nao_ironico * 100;
  return (
    <div className="flex flex-col gap-3 border-t border-linha pt-4">
      <p className="flex flex-wrap items-baseline gap-2 text-sm">
        <span className="text-muted-foreground">Classe mais provável:</span>
        <strong className={resultado.classe === "ironico" ? "text-detrator-texto" : "text-promotor-texto"}>
          {resultado.classe === "ironico" ? "Irônico" : "Não irônico"}
        </strong>
      </p>
      <div
        className="flex h-2.5 overflow-hidden rounded-sm bg-muted"
        role="img"
        aria-label={`Não irônico ${formatarNumero(literal)}%, irônico ${formatarNumero(ironia)}%`}
      >
        <span className="bg-promotor" style={{ width: `${literal}%` }} />
        <span className="bg-detrator" style={{ width: `${ironia}%` }} />
      </div>
      <div className="flex flex-wrap justify-between gap-3 text-xs">
        <span className="text-promotor-texto">Não irônico <b className="num">{formatarNumero(literal)}%</b></span>
        <span className="text-detrator-texto">Irônico <b className="num">{formatarNumero(ironia)}%</b></span>
      </div>
      <dl className="grid gap-2 border-t border-linha pt-3 text-xs sm:grid-cols-3">
        <div><dt className="text-muted-foreground">Modelo</dt><dd className="num mt-1">{resultado.modelo}</dd></div>
        <div><dt className="text-muted-foreground">Checkpoint</dt><dd className="num mt-1">{resultado.checkpoint}</dd></div>
        <div><dt className="text-muted-foreground">Revisão</dt><dd className="num mt-1 truncate" title={resultado.revisao}>{resultado.revisao.slice(0, 12)}</dd></div>
      </dl>
      <p className="text-xs leading-relaxed text-muted-foreground">
        Leitura experimental: não altera a nota, o NPS ou dados persistidos.
      </p>
    </div>
  );
}
