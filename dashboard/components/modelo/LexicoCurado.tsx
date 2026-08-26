"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Painel } from "@/components/Painel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatarData } from "@/lib/formato";

type TermoCurado = {
  id: number;
  tipo: "palavra" | "emoji";
  termo: string;
  peso: number;
  motivo: string | null;
  criado_em: string;
};

const PESOS_DE_PALAVRA = [
  [-1, "negativa"],
  [0, "neutra"],
  [1, "positiva"],
] as const;

/**
 * O que o analista ensinou ao lexico.
 *
 * A ESCALA DE CADA TIPO E IMPOSTA PELA INTERFACE, e nao so validada no
 * servidor: palavra tem TRES OPCOES, nunca campo numerico livre. Um campo de
 * texto convidaria a digitar -0,7, que a API recusa com 400 -- e a tela nao pode
 * oferecer o que o servidor recusa. Emoji e continuo porque a escala do Emoji
 * Sentiment Ranking e continua.
 *
 * A CONTAGEM SO APARECE COM TERMOS. Um score influenciado por curadoria humana
 * nao pode se apresentar como inferencia pura do modelo -- mesma regra que faz o
 * NPS carregar "estimativa" --, mas anunciar uma intervencao que nao houve e o
 * erro simetrico.
 */
export function LexicoCurado() {
  const [curados, setCurados] = useState<TermoCurado[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [tipo, setTipo] = useState<"palavra" | "emoji">("palavra");
  const [termo, setTermo] = useState("");
  const [peso, setPeso] = useState<number>(-1);
  const [motivo, setMotivo] = useState("");
  const [confirmando, setConfirmando] = useState<number | null>(null);

  const carregar = useCallback(async () => {
    try {
      const resposta = await fetch("/api/fraus/lexico/curado", {
        cache: "no-store",
      });
      const corpo = await resposta.json().catch(() => null);
      if (!resposta.ok) {
        setErro(corpo?.detail ?? `a API respondeu ${resposta.status}`);
        return;
      }
      setCurados(Array.isArray(corpo) ? corpo : []);
    } catch {
      setErro("não foi possível falar com a dashboard");
    }
  }, []);

  // Mesmo idioma do resto do shell: a cadeia de `.then` garante que toda
  // escrita de estado aconteça DEPOIS do efeito, nunca durante.
  useEffect(() => {
    let vivo = true;
    fetch("/api/fraus/lexico/curado", { cache: "no-store" })
      .then((resposta) => resposta.json())
      .then((corpo) => {
        if (vivo) setCurados(Array.isArray(corpo) ? corpo : []);
      })
      .catch(() => {
        if (vivo) setErro("não foi possível falar com a dashboard");
      });
    return () => {
      vivo = false;
    };
  }, []);

  async function cadastrar() {
    const limpo = termo.trim();
    if (!limpo) return;
    setOcupado(true);
    setErro(null);
    try {
      const resposta = await fetch("/api/fraus/lexico/curado", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          tipo,
          termo: limpo,
          peso,
          motivo: motivo.trim() || null,
        }),
      });
      const corpo = await resposta.json().catch(() => null);
      if (!resposta.ok) {
        // A MENSAGEM DA API SOBE COMO VEIO: ela nomeia a escala recusada, e
        // reescrevê-la aqui duplicaria a regra em dois lugares.
        setErro(corpo?.detail ?? `a API respondeu ${resposta.status}`);
        return;
      }
      setTermo("");
      setMotivo("");
      await carregar();
    } catch {
      setErro("não foi possível falar com a dashboard");
    } finally {
      setOcupado(false);
    }
  }

  async function revogar(id: number) {
    setOcupado(true);
    setErro(null);
    try {
      const resposta = await fetch(`/api/fraus/lexico/curado/${id}`, {
        method: "DELETE",
      });
      if (!resposta.ok && resposta.status !== 204) {
        const corpo = await resposta.json().catch(() => null);
        setErro(corpo?.detail ?? `a API respondeu ${resposta.status}`);
        return;
      }
      setConfirmando(null);
      await carregar();
    } catch {
      setErro("não foi possível falar com a dashboard");
    } finally {
      setOcupado(false);
    }
  }

  const palavras = curados?.filter((c) => c.tipo === "palavra").length ?? 0;
  const emojis = curados?.filter((c) => c.tipo === "emoji").length ?? 0;

  return (
    <Painel
      titulo="Léxico curado"
      legenda="Palavras e emojis que o treino não pegou, ou que valem outra coisa neste domínio. O peso alimenta o sinal léxico e o fusor decide o quanto isso move a nota — ninguém edita o score aqui."
      rodape="A curadoria VENCE o SentiLex-PT02 e o Emoji Sentiment Ranking, então ela serve tanto para preencher buraco quanto para corrigir polaridade errada. Peso neutro silencia um termo que o léxico base lê errado. Vale da próxima pontuação em diante: o que já foi pontuado só muda com Repontuar, na Visão geral."
      acessorio={
        palavras + emojis > 0 ? (
          <span className="num text-xs text-muted-foreground">
            {palavras} palavra(s) · {emojis} emoji(s)
          </span>
        ) : null
      }
    >
      <div className="flex flex-col gap-3">
        {erro ? (
          <Alert variant="destructive">
            <AlertTitle>Não foi possível</AlertTitle>
            <AlertDescription>{erro}</AlertDescription>
          </Alert>
        ) : null}

        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant={tipo === "palavra" ? "default" : "outline"}
            aria-pressed={tipo === "palavra"}
            onClick={() => {
              setTipo("palavra");
              setPeso(-1);
            }}
          >
            Palavra
          </Button>
          <Button
            type="button"
            size="sm"
            variant={tipo === "emoji" ? "default" : "outline"}
            aria-pressed={tipo === "emoji"}
            onClick={() => {
              setTipo("emoji");
              setPeso(0);
            }}
          >
            Emoji
          </Button>
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="termo-curado" className="text-foreground">
            {tipo === "palavra" ? "Palavra ou expressão" : "Emoji"}
          </Label>
          <Input
            id="termo-curado"
            autoComplete="off"
            className={tipo === "emoji" ? "num" : undefined}
            placeholder={tipo === "palavra" ? "lentíssimo" : "🫠"}
            value={termo}
            onChange={(evento) => setTermo(evento.target.value)}
            onKeyDown={(evento) => {
              if (evento.key === "Enter" && termo.trim()) void cadastrar();
            }}
          />
        </div>

        {tipo === "palavra" ? (
          /* Três opções, a escala do SentiLex. O rótulo é textual junto do
             estado -- categoria nunca é comunicada só por cor. */
          <fieldset className="flex flex-col gap-1">
            <legend className="text-sm text-foreground">Peso</legend>
            <div className="flex flex-wrap gap-3">
              {PESOS_DE_PALAVRA.map(([valor, rotulo]) => (
                <label
                  key={rotulo}
                  className="flex items-center gap-1.5 text-sm text-muted-foreground"
                >
                  {/* `accent-color` em vez de um controle reconstruído: o
                      radio nativo já tem o foco, o teclado e o leitor de tela
                      certos, e o único desvio do sistema de design era a cor
                      roxa que o navegador escolhe sozinho. */}
                  <input
                    type="radio"
                    name="peso-curado"
                    className="size-3.5 accent-[var(--primary)]"
                    checked={peso === valor}
                    onChange={() => setPeso(valor)}
                  />
                  {rotulo}
                </label>
              ))}
            </div>
          </fieldset>
        ) : (
          <div className="flex flex-col gap-1">
            <Label htmlFor="peso-emoji" className="text-foreground">
              Peso
            </Label>
            <div className="flex items-center gap-3">
              <input
                id="peso-emoji"
                type="range"
                min={-1}
                max={1}
                step={0.01}
                value={peso}
                onChange={(evento) => setPeso(Number(evento.target.value))}
                className="min-w-0 flex-1 accent-[var(--primary)]"
              />
              {/* `.num` porque é número que se compara: monoespaçado. */}
              <span className="num w-12 shrink-0 text-right text-sm text-foreground">
                {peso.toFixed(2)}
              </span>
            </div>
          </div>
        )}

        <div className="flex flex-col gap-1">
          <Label htmlFor="motivo-curado" className="text-foreground">
            Por que este peso <span className="text-muted-foreground">(opcional)</span>
          </Label>
          <Input
            id="motivo-curado"
            autoComplete="off"
            placeholder="reclamação comum no nosso suporte"
            value={motivo}
            onChange={(evento) => setMotivo(evento.target.value)}
          />
        </div>

        <div>
          <Button
            type="button"
            size="sm"
            onClick={() => void cadastrar()}
            disabled={ocupado || termo.trim() === ""}
          >
            <Plus aria-hidden />
            {ocupado ? "Salvando…" : "Cadastrar"}
          </Button>
        </div>

        {curados === null ? (
          <p className="text-xs text-muted-foreground">carregando…</p>
        ) : curados.length === 0 ? (
          /* ESTADO VAZIO NOMEIA O QUE FALTA, nunca "0 termos". */
          <p className="text-xs leading-relaxed text-muted-foreground">
            Nenhum termo curado. O léxico usa só o SentiLex-PT02 (79.189 formas)
            e o Emoji Sentiment Ranking (751 emojis, anotados em 2015).
          </p>
        ) : (
          <ul className="flex flex-col divide-y divide-[var(--linha)] rounded-md border border-[var(--linha)]">
            {curados.map((curado) => (
              <li
                key={curado.id}
                className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-xs"
              >
                <span className="num shrink-0 text-foreground">
                  {curado.termo}
                </span>
                <span className="num shrink-0 text-muted-foreground">
                  {curado.tipo === "palavra"
                    ? (PESOS_DE_PALAVRA.find(([v]) => v === curado.peso)?.[1] ??
                      curado.peso)
                    : curado.peso.toFixed(2)}
                </span>
                <span className="min-w-0 flex-1 truncate text-muted-foreground">
                  {curado.motivo ?? "—"}
                </span>
                <span className="num shrink-0 text-muted-foreground">
                  {formatarData(curado.criado_em)}
                </span>
                {confirmando === curado.id ? (
                  <span className="flex shrink-0 items-center gap-1">
                    {/* Confirmação inline em vez de `confirm()`: o diálogo
                        nativo some no meio de uma ação irreversível e é a única
                        peça que ficaria fora do sistema de design. */}
                    <span className="text-muted-foreground">revogar?</span>
                    <Button
                      type="button"
                      size="sm"
                      variant="destructive"
                      className="h-6 px-2"
                      onClick={() => void revogar(curado.id)}
                      disabled={ocupado}
                    >
                      Sim
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="h-6 px-2"
                      onClick={() => setConfirmando(null)}
                    >
                      Não
                    </Button>
                  </span>
                ) : (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-6 shrink-0 px-2"
                    onClick={() => setConfirmando(curado.id)}
                    disabled={ocupado}
                    title={`Devolve “${curado.termo}” ao léxico base`}
                  >
                    <Trash2 aria-hidden />
                    Revogar
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Painel>
  );
}
