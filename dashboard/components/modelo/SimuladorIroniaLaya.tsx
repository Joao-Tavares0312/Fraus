"use client";

import { useId, useState } from "react";
import { Play, RotateCcw } from "lucide-react";
import { simularIroniaLaya, type ConfiguracaoIroniaLaya, type SimulacaoIroniaLaya } from "@/lib/api";
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

const BASE = {
  contexto: "",
  instrucao: "A fala do cliente é irônica? Considere incongruência entre o sentido literal e a situação descrita.",
  criterio_ironico: "há ironia ou incongruência entre elogio literal e situação negativa",
  criterio_literal: "a fala é literal e não irônica",
};
const PERFIS = {
  // A Laya multilingual e subconfiante para ironia em portugues: no conjunto
  // de verificacao do artefato, exemplos ironicos conhecidos ficaram entre
  // 0,2255 e 0,3028. A tela apresenta sempre uma das duas classes.
  conservador: { limiar: 0.5, confianca_minima: 0.0 },
  equilibrado: { limiar: 0.3, confianca_minima: 0.0 },
  sensivel: { limiar: 0.2, confianca_minima: 0.0 },
} as const;
type Perfil = keyof typeof PERFIS | "customizado";

export function SimuladorIroniaLaya() {
  const [texto, setTexto] = useState(PARTIDAS[0]);
  const [resultado, setResultado] = useState<SimulacaoIroniaLaya | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [rodando, setRodando] = useState(false);
  const [perfil, setPerfil] = useState<Perfil>("equilibrado");
  const [configuracao, setConfiguracao] = useState<ConfiguracaoIroniaLaya>({ ...BASE, ...PERFIS.equilibrado });
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
    setResultado(null);
    const resposta = await simularIroniaLaya(limpo, configuracao);
    setRodando(false);
    if (resposta.ok) setResultado(resposta.dado);
    else {
      setErro(resposta.erro);
      setResultado(null);
    }
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
              simular();
            }
          }}
          rows={4}
          maxLength={TETO}
          className="min-w-0 max-w-full resize-y font-normal"
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

      <div className="grid min-w-0 grid-cols-1 gap-4 border-y border-linha py-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-2">
          <Label className="text-xs text-muted-foreground">Perfil de decisão</Label>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(PERFIS) as Array<keyof typeof PERFIS>).map((nome) => (
              <Button key={nome} type="button" size="xs" variant={perfil === nome ? "default" : "outline"}
                onClick={() => {
                  setPerfil(nome);
                  setConfiguracao((atual) => ({ ...atual, ...PERFIS[nome] }));
                  setResultado(null);
                }}>
                {nome}
              </Button>
            ))}
          </div>
          <label className="mt-2 text-xs text-muted-foreground">
            Limiar de ironia <b className="num text-foreground">{formatarNumero(configuracao.limiar * 100)}%</b>
            <input className="mt-2 block w-full accent-primary" type="range" min="0" max="1" step="0.05"
              value={configuracao.limiar} onChange={(evento) => {
                setPerfil("customizado");
                setConfiguracao((atual) => ({ ...atual, limiar: Number(evento.target.value) }));
                setResultado(null);
              }} />
          </label>
          <p className="text-xs leading-relaxed text-muted-foreground">
            O perfil ajusta o limiar da decisão para português.
          </p>
        </div>
        <div className="flex min-w-0 flex-col gap-2">
          <Label htmlFor={`${idCampo}-contexto`} className="text-xs text-muted-foreground">Contexto anterior da conversa · opcional</Label>
          <Textarea id={`${idCampo}-contexto`} value={configuracao.contexto}
            onChange={(evento) => {
              setConfiguracao((atual) => ({ ...atual, contexto: evento.target.value }));
              setResultado(null);
            }}
            rows={5} maxLength={6000} placeholder="Cliente já tentou resolver três vezes; o pedido foi cancelado sem aviso…"
            className="min-w-0 max-w-full resize-y font-normal" />
        </div>
      </div>

      <details className="min-w-0 rounded-lg border border-border px-4 py-3">
        <summary className="cursor-pointer text-sm font-medium">Instrução e critérios avançados</summary>
        <div className="mt-4 grid gap-3">
          {([ ["instrucao", "Instrução"], ["criterio_ironico", "Critério para irônico"], ["criterio_literal", "Critério para literal"] ] as const).map(([chave, rotulo]) => (
            <label key={chave} className="text-xs text-muted-foreground">{rotulo}
              <Textarea value={configuracao[chave]}
                onChange={(evento) => {
                  setConfiguracao((atual) => ({ ...atual, [chave]: evento.target.value }));
                  setResultado(null);
                }}
                rows={2} maxLength={600} className="mt-1 min-w-0 max-w-full resize-y font-normal text-foreground" />
            </label>
          ))}
          <Button type="button" size="xs" variant="outline" className="w-fit" onClick={() => {
            setPerfil("equilibrado");
            setConfiguracao({ ...BASE, ...PERFIS.equilibrado });
            setResultado(null);
          }}>Restaurar configuração padrão</Button>
        </div>
      </details>

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
  const ironico = resultado.classe === "ironico" || (
    resultado.classe === "inconclusivo" && resultado.prob_ironia >= resultado.limiar
  );
  return (
    <div className="min-w-0 border-t border-linha pt-4" role="status" aria-live="polite">
      <p className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1 text-sm">
        <span className="text-muted-foreground">Resultado:</span>
        <strong className={ironico ? "text-detrator-texto" : "text-promotor-texto"}>
          {ironico ? "Irônico" : "Não irônico"}
        </strong>
      </p>
    </div>
  );
}
