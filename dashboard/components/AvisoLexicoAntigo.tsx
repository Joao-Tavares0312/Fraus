"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  INTERVALO_DE_CONSULTA_MS,
  lerProgresso,
  type EstadoDoServidor,
  type Leitura,
} from "@/lib/repontuacao";

const ROTA = "/api/fraus/conversas/repontuar";

/**
 * "41 de 62 atendimentos foram pontuados com um lexico ou modelo anterior."
 *
 * O `score` e gravado na importacao, entao curar uma palavra (ou retreinar o
 * fusor, ou mudar a regra da cortesia) NAO mexe no que ja existe -- e um banco com conversas pontuadas antes e depois soma duas reguas
 * no mesmo agregado. Esconder isso seria apresentar como um numero o que sao
 * dois; nomear a divergencia e o unico caminho honesto.
 *
 * As duas contagens sao do BANCO INTEIRO e ignoram o recorte de periodo de
 * proposito: um aviso que sumisse ao filtrar esconderia o problema exatamente de
 * quem estivesse investigando um numero estranho.
 *
 * REPONTUAR RODA EM SEGUNDO PLANO desde 15/09/2026: o POST responde na hora e
 * este componente consulta o progresso ate o fim. Antes a tela segurava a
 * requisicao pelo banco inteiro, e o proxy desistia em bancos grandes. Uma
 * repontuacao ja em andamento (outra aba, outra pessoa) e retomada ao montar,
 * em vez de oferecer um botao que responderia 409.
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
  const [leitura, setLeitura] = useState<Leitura>({ tipo: "parado" });
  const [erroDeRede, setErroDeRede] = useState<string | null>(null);
  // Ligado ao montar (para retomar uma que ja rodava) e a cada clique. O laco
  // de consulta vive num efeito so, que se desliga sozinho quando o servidor
  // diz que acabou -- e morre com o componente.
  const [acompanhando, setAcompanhando] = useState(true);

  useEffect(() => {
    if (!acompanhando) return;
    let vivo = true;
    let temporizador: ReturnType<typeof setTimeout> | undefined;

    async function consultar() {
      try {
        const resposta = await fetch(ROTA, { cache: "no-store" });
        if (!vivo) return;
        if (resposta.status === 404) {
          setLeitura(lerProgresso(null));
          setAcompanhando(false);
          return;
        }
        if (!resposta.ok) {
          const corpo = await resposta.json().catch(() => null);
          if (!vivo) return;
          setErroDeRede(corpo?.detail ?? `a API respondeu ${resposta.status}`);
          setAcompanhando(false);
          return;
        }
        const atual = lerProgresso((await resposta.json()) as EstadoDoServidor);
        if (!vivo) return;
        setLeitura(atual);
        if (atual.tipo === "rodando") {
          temporizador = setTimeout(() => void consultar(), INTERVALO_DE_CONSULTA_MS);
          return;
        }
        setAcompanhando(false);
        // O servidor e quem tem a contagem nova: recarregar a rota e o que faz
        // o aviso sumir, em vez de esconde-lo por conta propria no cliente.
        if (atual.tipo === "concluido") router.refresh();
      } catch {
        if (!vivo) return;
        setErroDeRede("não foi possível falar com a dashboard");
        setAcompanhando(false);
      }
    }

    void consultar();
    return () => {
      vivo = false;
      if (temporizador) clearTimeout(temporizador);
    };
  }, [acompanhando, router]);

  async function repontuar() {
    setErroDeRede(null);
    try {
      const resposta = await fetch(ROTA, { method: "POST" });
      // 409 e "ja ha uma rodando": nao e erro de quem clicou, e so acompanhar.
      if (!resposta.ok && resposta.status !== 409) {
        const corpo = await resposta.json().catch(() => null);
        setErroDeRede(corpo?.detail ?? `a API respondeu ${resposta.status}`);
        return;
      }
      setLeitura({ tipo: "rodando", feitas: 0, total: 0, fracao: 0 });
      setAcompanhando(true);
    } catch {
      setErroDeRede("não foi possível falar com a dashboard");
    }
  }

  const rodando = leitura.tipo === "rodando";

  return (
    <Alert>
      <AlertTitle>
        <span className="num">{defasadas}</span> de{" "}
        <span className="num">{total}</span> atendimentos foram pontuados com um
        léxico ou modelo anterior
      </AlertTitle>
      <AlertDescription className="flex flex-col gap-2">
        <span>
          Os números desta tela somam duas réguas. Repontuar recalcula o banco
          inteiro com o léxico e o modelo vigentes — roda os três classificadores de novo por
          atendimento, em segundo plano. Enquanto roda, a mistura continua: a
          tela só fica numa régua quando terminar.
        </span>

        {rodando ? (
          <div className="flex flex-col gap-1" aria-live="polite">
            <span>
              Repontuando: <span className="num">{leitura.feitas}</span> de{" "}
              <span className="num">{leitura.total}</span>
            </span>
            <div
              role="progressbar"
              aria-label="Progresso da repontuação"
              aria-valuemin={0}
              aria-valuemax={leitura.total}
              aria-valuenow={leitura.feitas}
              className="h-1 w-full max-w-xs overflow-hidden rounded-full bg-muted"
            >
              <div
                className="h-full bg-foreground/70"
                style={{ width: `${Math.round(leitura.fracao * 100)}%` }}
              />
            </div>
          </div>
        ) : null}

        {leitura.tipo === "falhou" ? (
          <span className="text-destructive" aria-live="polite">
            A repontuação parou em <span className="num">{leitura.feitas}</span> de{" "}
            <span className="num">{leitura.total}</span>: {leitura.mensagem}. O que
            já foi recalculado ficou gravado; repontuar de novo termina o resto.
          </span>
        ) : null}

        {erroDeRede ? <span className="text-destructive">{erroDeRede}</span> : null}

        <span>
          <Button
            type="button"
            size="sm"
            onClick={() => void repontuar()}
            disabled={rodando}
          >
            <RefreshCw aria-hidden />
            {rodando ? "Repontuando…" : "Repontuar tudo"}
          </Button>
        </span>
      </AlertDescription>
    </Alert>
  );
}
