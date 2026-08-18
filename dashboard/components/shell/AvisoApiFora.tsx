"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Copy, Play, RotateCcw, ServerCrash } from "lucide-react";
import { useSaude } from "./SaudeProvider";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

type ModoLocal = {
  disponivel: boolean;
  motivo: string | null;
  comando: string;
  log: string;
};

/** Teto da espera pela subida. A API real carrega três BERTimbau do disco. */
const TETO_MS = 90_000;
const PASSO_MS = 2_000;

/**
 * O que fazer quando a API nao responde -- na tela, sem procurar o terminal.
 *
 * Aparece em QUALQUER pagina, porque sem a API todas quebram igual: consertar
 * so a de Configuracoes deixaria Visao geral e Atendimentos com o mesmo erro
 * seco e nenhuma instrucao.
 *
 * O botao de iniciar so existe no MODO LOCAL (`FRAUS_MODO_LOCAL=1`), e quem
 * decide isso e o servidor: a tela pergunta a `GET /api/fraus/iniciar` antes
 * de desenhar. Sem o modo, o aviso ainda serve -- ele carrega o comando pronto
 * para copiar, que e a mesma linha que a rota executaria.
 */
export function AvisoApiFora() {
  const { estado, reconsultar } = useSaude();
  const router = useRouter();
  const [modo, setModo] = useState<ModoLocal | null>(null);
  const [subindo, setSubindo] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const [erro, setErro] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);
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
        if (vivo) setModo({ disponivel: false, motivo: null, comando: "", log: "" });
      });
    return () => {
      vivo = false;
    };
  }, [estado, modo]);

  useEffect(() => () => {
    cancelado.current = true;
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
    setErro(
      `a API não respondeu em ${TETO_MS / 1000}s. O log está em ${modo?.log ?? ".fraus-api.log"} — o motivo mais comum é modelo ausente em modelos/, que derruba o boot por design.`,
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
    await navigator.clipboard.writeText(modo.comando);
    setCopiado(true);
  }

  if (estado !== "fora-do-ar") return null;

  return (
    <div className="px-4 pt-4 sm:px-6">
      <Alert variant="destructive">
        <ServerCrash aria-hidden />
        <AlertTitle>A API não está respondendo</AlertTitle>
        <AlertDescription>
          <p className="mb-2">
            As telas ficam vazias porque o dado vem dela — não porque não há
            atendimento. {modo?.disponivel
              ? "Você pode subir a API por aqui:"
              : "Suba a API no terminal, na raiz do projeto:"}
          </p>

          {modo?.comando ? (
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <code className="num min-w-0 flex-1 overflow-x-auto rounded-sm bg-muted px-2 py-1.5 text-xs text-foreground">
                {modo.comando}
              </code>
              <Button type="button" size="sm" variant="outline" onClick={copiar}>
                {copiado ? <Check aria-hidden /> : <Copy aria-hidden />}
                {copiado ? "Copiado" : "Copiar"}
              </Button>
            </div>
          ) : null}

          {erro ? <p className="mb-3 text-foreground">{erro}</p> : null}

          <div className="flex flex-wrap items-center gap-2">
            {modo?.disponivel ? (
              <Button type="button" size="sm" onClick={iniciar} disabled={subindo}>
                <Play aria-hidden />
                {subindo ? `subindo… (${segundos}s)` : "Iniciar API"}
              </Button>
            ) : null}

            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={async () => {
                if (await reconsultar()) router.refresh();
              }}
              disabled={subindo}
            >
              <RotateCcw aria-hidden />
              Tentar de novo
            </Button>
          </div>

          {subindo ? (
            <p className="mt-2 text-xs">
              A API real carrega os três BERTimbau do disco — costuma levar de 30
              a 60 segundos na primeira subida.
            </p>
          ) : null}
        </AlertDescription>
      </Alert>
    </div>
  );
}
