"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Copy, Play, RotateCcw } from "lucide-react";
import { useSaude } from "./SaudeProvider";
import { Aparato } from "@/components/Aparato";
import { Button } from "@/components/ui/button";

type ModoLocal = {
  disponivel: boolean;
  motivo: string | null;
  comando: string;
  log: string;
  /** A ultima linha de falha do log, lida no servidor. `null` se nao houver. */
  ultimaFalha?: string | null;
};

/**
 * Reconsulta o log DEPOIS da espera, e nao reusa o `modo` que a tela carregou.
 *
 * O `modo` foi buscado antes de a API tentar subir; a falha que interessa
 * aconteceu durante a espera e so existe numa leitura nova.
 */
async function falhaDoLog(): Promise<string | null> {
  try {
    const resposta = await fetch("/api/fraus/iniciar", { cache: "no-store" });
    if (!resposta.ok) return null;
    const dado: ModoLocal = await resposta.json();
    return dado.ultimaFalha ?? null;
  } catch {
    return null;
  }
}

/** Teto da espera pela subida. A API real carrega três BERTimbau do disco. */
const TETO_MS = 90_000;
const PASSO_MS = 2_000;

/**
 * A RÉGUA DE ESTADO: o que fazer quando a API não responde.
 *
 * Isto era um `Alert variant="destructive"` de largura total, e estava errado
 * por tres razoes do DESIGN.md ao mesmo tempo: cartao como agrupador onde o
 * mundo pede regua e espaco; vermelho preenchido no topo competindo com o
 * vermelho que codifica DETRATOR no dado; e um titulo de tamanho de secao para
 * um fato que o rodape da navegacao ja anuncia.
 *
 * O que ficou: uma faixa da altura de uma barra de sistema. Ponto de estado,
 * uma frase, e a ACAO a direita -- que e a unica coisa aqui que a barra lateral
 * nao tem. O dourado de `--primary` aparece porque este e literalmente o papel
 * reservado a ele: acao primaria. O comando de terminal e o caminho do log
 * viraram APARATO recolhivel (secao 4.1), porque sao instrucao de contingencia,
 * nao a acao do momento.
 *
 * Aparece em QUALQUER tela: sem a API todas ficam vazias igual, e a acao tem de
 * estar onde o Joao ja esta olhando.
 */
export function AvisoApiFora() {
  const { estado, reconsultar } = useSaude();
  const router = useRouter();
  const [modo, setModo] = useState<ModoLocal | null>(null);
  const [subindo, setSubindo] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const [erro, setErro] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);
  /** A copia falhou -- ver o `catch` de `copiar`. */
  const [falhouCopia, setFalhouCopia] = useState(false);
  const cancelado = useRef(false);

  useEffect(() => {
    // Só pergunta quando há motivo: com a API no ar, a rota nem é consultada.
    if (estado !== "fora-do-ar" || modo !== null) return;
    let vivo = true;
    fetch("/api/fraus/iniciar", { cache: "no-store" })
      .then((resposta) => resposta.json())
      .then((dado: ModoLocal) => {
        if (vivo) setModo(dado);
      })
      .catch(() => {
        if (vivo) setModo({ disponivel: false, motivo: null, comando: "", log: "", ultimaFalha: null });
      });
    return () => {
      vivo = false;
    };
  }, [estado, modo]);

  useEffect(() => {
    // O `false` na ENTRADA não é redundante: em desenvolvimento o React monta,
    // desmonta e remonta o componente, e o cleanup do primeiro mount deixava a
    // bandeira levantada para sempre. O efeito era o contador de "subindo…"
    // travado em 0s e a espera morta na primeira volta -- o botão ficava
    // girando enquanto a API subia normalmente atrás dele.
    cancelado.current = false;
    return () => {
      cancelado.current = true;
    };
  }, []);

  const esperarSubir = useCallback(async () => {
    const inicio = Date.now();
    while (Date.now() - inicio < TETO_MS) {
      await new Promise((resolver) => setTimeout(resolver, PASSO_MS));
      if (cancelado.current) return;
      setSegundos(Math.round((Date.now() - inicio) / 1000));
      if (await reconsultar()) {
        setSubindo(false);
        // A tela inteira foi renderizada com a API fora: recarregar é o que
        // troca os estados vazios pelo dado real, sem o João apertar F5.
        router.refresh();
        return;
      }
    }
    setSubindo(false);
    // O QUE O LOG DIZ, e não o que costuma ser. Esta mensagem afirmava
    // "o motivo mais comum é modelo ausente em modelos/" -- e num caso real o
    // modelo estava no lugar e o uvicorn morria por porta já tomada, o que
    // mandou procurar no lugar errado. A tela nomeia o que sabe; quando não
    // sabe, diz que não sabe e aponta o log.
    const doLog = await falhaDoLog();
    setErro(
      doLog
        ? `a API não respondeu em ${TETO_MS / 1000}s. A última falha no log foi: ${doLog} — log completo em ${modo?.log ?? ".fraus-api.log"}.`
        : `a API não respondeu em ${TETO_MS / 1000}s e o log não registrou falha — veja ${modo?.log ?? ".fraus-api.log"}.`,
    );
  }, [reconsultar, router, modo]);

  async function iniciar() {
    setErro(null);
    setSubindo(true);
    setSegundos(0);
    try {
      const resposta = await fetch("/api/fraus/iniciar", { method: "POST" });
      const corpo = await resposta.json().catch(() => null);
      if (resposta.status === 200) {
        // Já estava no ar — outra aba subiu, ou o polling estava atrasado.
        setSubindo(false);
        await reconsultar();
        router.refresh();
        return;
      }
      if (!resposta.ok) {
        setSubindo(false);
        setErro(corpo?.detail ?? `a dashboard respondeu ${resposta.status}`);
        return;
      }
      await esperarSubir();
    } catch {
      setSubindo(false);
      setErro("não foi possível falar com o servidor da dashboard");
    }
  }

  async function copiar() {
    if (!modo?.comando) return;
    try {
      await navigator.clipboard.writeText(modo.comando);
      setCopiado(true);
      setFalhouCopia(false);
    } catch {
      // `navigator.clipboard` so existe em contexto seguro (HTTPS ou
      // localhost). Num IP de LAN por HTTP a promise rejeita, e sem isto o
      // botao ficava mudo -- justamente nesta faixa, que ja e a tela de quando
      // algo nao esta funcionando.
      setFalhouCopia(true);
    }
  }

  if (estado !== "fora-do-ar") return null;

  return (
    <div className="border-b border-[var(--linha)] bg-card/40">
      <div className="flex min-w-0 flex-col gap-2 px-4 py-2.5 sm:px-6">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2">
          {/* O ponto carrega o estado; o rótulo textual vem colado, porque cor
              nunca é o único canal. Pulsa só enquanto sobe -- movimento que
              comunica estado, e o único desta faixa. */}
          <span className="flex shrink-0 items-center gap-2">
            <span
              aria-hidden
              className={`size-2 rounded-full bg-destructive ${subindo ? "motion-safe:animate-pulse" : ""}`}
            />
            <span className="text-sm font-medium text-foreground">
              {subindo ? "Subindo a API" : "API fora do ar"}
            </span>
          </span>

          <p role="status" className="min-w-0 flex-1 text-xs text-muted-foreground">
            {subindo ? (
              <>
                carregando os três BERTimbau do disco —{" "}
                <span className="num text-foreground">{segundos}s</span>, costuma
                levar de 30 a 60
              </>
            ) : (
              "as telas ficam vazias porque o dado vem dela, não porque não há atendimento"
            )}
          </p>

          <span className="flex shrink-0 items-center gap-2">
            {modo?.disponivel ? (
              <Button type="button" size="sm" onClick={iniciar} disabled={subindo}>
                <Play aria-hidden />
                {subindo ? "subindo…" : "Iniciar API"}
              </Button>
            ) : null}
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={async () => {
                if (await reconsultar()) router.refresh();
              }}
              disabled={subindo}
            >
              <RotateCcw aria-hidden />
              Tentar de novo
            </Button>
          </span>
        </div>

        {erro ? (
          <p className="max-w-[75ch] text-xs text-[var(--destructive-rich-text)]">
            {erro}
          </p>
        ) : null}

        {/* APARATO: instrução de contingência, a um gesto de distância. Fica
            fechada porque o botão ao lado resolve o caso normal -- e continua
            existindo porque nem todo caso é o normal. */}
        {modo?.comando ? (
          <Aparato
            className="min-w-0"
            rotulo={
              modo.disponivel ? "subir pelo terminal" : "como subir no terminal"
            }
          >
            <div className="mt-2 flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <code className="num min-w-0 flex-1 overflow-x-auto rounded-sm bg-muted px-2 py-1.5 text-foreground">
                {modo.comando}
              </code>
              <Button type="button" size="sm" variant="outline" onClick={copiar}>
                {copiado ? <Check aria-hidden /> : <Copy aria-hidden />}
                {copiado ? "Copiado" : "Copiar"}
              </Button>
            </div>
            {falhouCopia ? (
              <p role="status" className="mt-2 text-xs text-muted-foreground">
                O navegador não deixou copiar — a área de transferência só
                funciona em HTTPS ou em <span className="num">localhost</span>.
                Selecione o comando acima e copie à mão.
              </p>
            ) : null}
            {modo.motivo ? (
              <p className="mt-2 text-xs text-muted-foreground">
                O botão não aparece porque {modo.motivo}.
              </p>
            ) : null}
          </Aparato>
        ) : null}
      </div>
    </div>
  );
}
