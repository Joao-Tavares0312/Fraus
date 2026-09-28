"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Power } from "lucide-react";
import { ENDERECO_API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useSaude, type EstadoDeSaude as Estado } from "./SaudeProvider";

const APARENCIA: Record<
  Estado,
  { rotulo: string; cor: string; detalhe: string }
> = {
  verificando: {
    rotulo: "verificando…",
    cor: "bg-muted-foreground",
    detalhe: "consultando GET /saude",
  },
  "no-ar": {
    rotulo: "API no ar",
    cor: "bg-success",
    detalhe: "GET /saude respondeu ok, com o motor real",
  },
  frio: {
    rotulo: "motor em espera",
    cor: "bg-warning",
    detalhe: "a API está pronta; o motor será carregado na primeira análise",
  },
  aquecendo: {
    rotulo: "motor aquecendo…",
    cor: "bg-warning motion-safe:animate-pulse",
    detalhe: "GET /saude respondeu, mas o motor real ainda não está pronto",
  },
  "erro-motor": {
    rotulo: "motor indisponível",
    cor: "bg-destructive",
    detalhe: "GET /saude respondeu, mas a carga do motor falhou",
  },
  // A API respondeu, mas quem pontua é o dublê: TODO número da tela é
  // sintético, inclusive os pesos por feature. Cor de aviso e não de sucesso,
  // porque isto não é um estado saudável — é uma tela que não pode ser lida
  // como medição, e muito menos apresentada como tal.
  duble: {
    rotulo: "motor dublê — números sintéticos",
    cor: "bg-warning",
    detalhe:
      "GET /saude respondeu com motor=duble: a API está de pé, mas não está medindo",
  },
  "fora-do-ar": {
    rotulo: "API fora do ar",
    cor: "bg-destructive",
    detalhe: "GET /saude não respondeu",
  },
};

/**
 * Estado de saude da API, sempre visivel no rodape da navegacao.
 *
 * Existe porque a API real do Fraus NAO sobe sem modelo treinado (invariante
 * 7): a tela em branco tem duas causas possiveis -- banco vazio ou servidor
 * fora -- e sem este indicador quem esta na frente do produto nao sabe qual.
 *
 * Cor nao e o unico canal: o rotulo textual diz o estado, e o `title` diz qual
 * endereco foi consultado.
 *
 * O POLLING nao mora mais aqui: ele vive no `SaudeProvider`, porque o aviso de
 * "API fora do ar" mostra o mesmo fato e dois pollings independentes
 * discordariam por ate 20 segundos -- este rodape dizendo "API no ar" com o
 * aviso ainda na tela.
 */
export function EstadoSaude() {
  const { estado, reconsultar } = useSaude();
  const router = useRouter();
  const [nossa, setNossa] = useState(false);
  const [desligando, setDesligando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // Só pergunta com a API RESPONDENDO -- no ar ou em dublê. São os dois
  // estados em que desligar faz sentido, e o dublê é justamente o que alguém
  // mais vai querer derrubar para subir a API real no lugar. Com ela fora, a
  // pergunta seria uma chamada por poll sem resposta útil.
  const respondendo =
    estado === "no-ar" ||
    estado === "frio" ||
    estado === "aquecendo" ||
    estado === "erro-motor" ||
    estado === "duble";

  useEffect(() => {
    // Sem `setNossa(false)` neste ramo: apagar o estado aqui seria escrever
    // durante o efeito, e o próprio render já não mostra o botão quando a API
    // não responde (ver a condição abaixo). Um estado a menos para sincronizar.
    if (!respondendo) return;
    let vivo = true;
    fetch("/api/fraus/iniciar", { cache: "no-store" })
      .then((resposta) => resposta.json())
      .then((dado: { disponivel: boolean; nossa: boolean }) => {
        if (vivo) setNossa(Boolean(dado.disponivel && dado.nossa));
      })
      .catch(() => {
        if (vivo) setNossa(false);
      });
    return () => {
      vivo = false;
    };
  }, [respondendo]);

  async function desligar() {
    setErro(null);
    setDesligando(true);
    try {
      const resposta = await fetch("/api/fraus/iniciar", { method: "DELETE" });
      const corpo = await resposta.json().catch(() => null);
      if (!resposta.ok) {
        setErro(corpo?.detail ?? `a dashboard respondeu ${resposta.status}`);
        return;
      }
      setNossa(false);
      // `reconsultar` troca o rótulo para "fora do ar" e faz o aviso com o
      // botão de subir aparecer -- o caminho de volta, no mesmo gesto.
      await reconsultar();
      router.refresh();
    } catch {
      setErro("não foi possível falar com o servidor da dashboard");
    } finally {
      setDesligando(false);
    }
  }

  const { rotulo, cor, detalhe } = APARENCIA[estado];

  return (
    <div className="flex min-w-0 flex-col gap-1">
      <div
        className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-muted-foreground"
        title={`${detalhe} — ${ENDERECO_API}`}
      >
        <span
          aria-hidden
          className={`size-2 shrink-0 rounded-full ${cor}`}
        />
        <span
          role="status"
          className="truncate group-data-[collapsible=icon]:hidden"
        >
          {rotulo}
        </span>
        <span className="sr-only">{`${rotulo}. ${detalhe}.`}</span>

        {/* Só aparece para a API que ESTA dashboard subiu. Para um uvicorn de
            terminal o botão não existe -- oferecer uma ação que levaria 409
            seria prometer um poder que a tela não tem. */}
        {respondendo && nossa ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="ml-auto h-6 shrink-0 px-1.5 text-xs group-data-[collapsible=icon]:hidden"
            onClick={desligar}
            disabled={desligando}
            title="Encerra a API que esta dashboard iniciou"
          >
            <Power aria-hidden />
            {desligando ? "desligando…" : "Desligar"}
          </Button>
        ) : null}
      </div>

      {erro ? (
        <p className="px-2 text-[11px] leading-tight text-[var(--destructive-rich-text)] group-data-[collapsible=icon]:hidden">
          {erro}
        </p>
      ) : null}
    </div>
  );
}
