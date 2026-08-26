"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

/**
 * "41 de 62 atendimentos foram pontuados com um lexico anterior."
 *
 * O `score` e gravado na importacao, entao curar uma palavra NAO mexe no que ja
 * existe -- e um banco com conversas pontuadas antes e depois soma duas reguas
 * no mesmo agregado. Esconder isso seria apresentar como um numero o que sao
 * dois; nomear a divergencia e o unico caminho honesto.
 *
 * As duas contagens sao do BANCO INTEIRO e ignoram o recorte de periodo de
 * proposito: um aviso que sumisse ao filtrar esconderia o problema exatamente de
 * quem estivesse investigando um numero estranho.
 *
 * Com `defasadas === 0` este componente nao e renderizado pela pagina.
 */
export function AvisoLexicoAntigo({
  defasadas,
  total,
}: {
  defasadas: number;
  total: number;
}) {
  const router = useRouter();
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function repontuar() {
    setOcupado(true);
    setErro(null);
    try {
      const resposta = await fetch("/api/fraus/conversas/repontuar", {
        method: "POST",
      });
      if (!resposta.ok) {
        const corpo = await resposta.json().catch(() => null);
        setErro(corpo?.detail ?? `a API respondeu ${resposta.status}`);
        return;
      }
      // O servidor e quem tem a contagem nova: recarregar a rota e o que faz o
      // aviso sumir, em vez de esconde-lo por conta propria no cliente.
      router.refresh();
    } catch {
      setErro("não foi possível falar com a dashboard");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <Alert>
      <AlertTitle>
        <span className="num">{defasadas}</span> de{" "}
        <span className="num">{total}</span> atendimentos foram pontuados com um
        léxico anterior
      </AlertTitle>
      <AlertDescription className="flex flex-col gap-2">
        <span>
          Os números desta tela somam duas réguas. Repontuar recalcula o banco
          inteiro com o léxico vigente — roda os três classificadores de novo por
          atendimento, então leva alguns segundos e a tela espera.
        </span>
        {erro ? <span className="text-destructive">{erro}</span> : null}
        <span>
          <Button
            type="button"
            size="sm"
            onClick={() => void repontuar()}
            disabled={ocupado}
          >
            <RefreshCw aria-hidden />
            {ocupado ? "Repontuando…" : "Repontuar tudo"}
          </Button>
        </span>
      </AlertDescription>
    </Alert>
  );
}
