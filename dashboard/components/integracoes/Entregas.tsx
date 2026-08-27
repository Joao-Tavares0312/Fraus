"use client";

import { useEffect, useState } from "react";
import { listarEntregas, type Entrega, type Veredito } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * O rotulo e a cor de um veredito de entrega.
 *
 * O `switch` e EXAUSTIVO e nao tem `default`, de proposito: o retorno declarado
 * obriga todo caminho a devolver, entao um veredito novo entrando em
 * `VEREDITOS` no Python e no tipo `Veredito` sem passar por aqui vira erro de
 * tipo no `npx tsc --noEmit`. Um `default` engoliria exatamente a divergencia
 * que o tipo existe para pegar -- e o sintoma seria um rotulo em branco na
 * tela, que ninguem le como bug.
 *
 * A cor segue a §3.3 do DESIGN.md: nada de `--primary` aqui, porque o dourado e
 * acao e foco e NUNCA dado. `sem_segredo` e o unico em vermelho porque e o
 * unico defeito da MAQUINA que hospeda -- a variavel de ambiente nao esta la, a
 * rota responde 503, e nenhuma plataforma do outro lado consegue consertar.
 */
function descreverVeredito(veredito: Veredito): {
  rotulo: string;
  cor: string;
} {
  switch (veredito) {
    case "aceita":
      return { rotulo: "aceita", cor: "text-promotor-texto" };
    case "assinatura":
      return { rotulo: "assinatura inválida", cor: "text-muted-foreground" };
    case "fora_da_janela":
      return { rotulo: "fora da janela de tempo", cor: "text-muted-foreground" };
    case "duplicada":
      return { rotulo: "reentrega", cor: "text-muted-foreground" };
    case "corpo_invalido":
      return { rotulo: "corpo fora do contrato", cor: "text-muted-foreground" };
    case "fonte_inativa":
      return { rotulo: "fonte desativada", cor: "text-muted-foreground" };
    case "sem_segredo":
      return {
        rotulo: "segredo ausente no ambiente da API",
        cor: "text-detrator-texto",
      };
  }
}

/**
 * O historico de entregas de webhook de uma fonte.
 *
 * Busca no CLIENTE, e nao no servidor da pagina: esta lista muda enquanto a
 * tela esta aberta -- e ela que o operador olha enquanto aponta a plataforma
 * para ca e ve a primeira chamada chegar. Uma lista renderizada uma vez no
 * servidor exigiria recarregar a pagina para descobrir se a integracao passou.
 */
export function Entregas({ fonteId }: { fonteId: number }) {
  /**
   * O resultado carrega a fonte a que ele pertence.
   *
   * E o que dispensa um `setEstado(null)` no corpo do efeito ao trocar de
   * fonte -- render em cascata, que o ESLint recusa. Enquanto a fonte do
   * estado nao for a fonte pedida, o que vale e o esqueleto: a lista da fonte
   * anterior nunca chega a ser exibida sob o nome da nova.
   */
  const [estado, setEstado] = useState<{
    fonteId: number;
    entregas: Entrega[] | null;
    erro: string | null;
  } | null>(null);

  useEffect(() => {
    let vivo = true;
    listarEntregas(fonteId).then((resposta) => {
      if (!vivo) return;
      setEstado(
        resposta.ok
          ? { fonteId, entregas: resposta.dado, erro: null }
          : { fonteId, entregas: null, erro: resposta.erro },
      );
    });
    // Trocar de fonte descarta a resposta em voo: sem isto, a lista da fonte
    // anterior chegando depois pintaria as entregas de outra fonte.
    return () => {
      vivo = false;
    };
  }, [fonteId]);

  const atual = estado !== null && estado.fonteId === fonteId ? estado : null;
  const erro = atual === null ? null : atual.erro;
  const entregas = atual === null ? null : atual.entregas;

  if (erro) {
    return (
      <EstadoVazio
        titulo="Não foi possível ler as entregas desta fonte"
        explicacao={erro}
        endpoint={`GET /integracoes/fontes/${fonteId}/entregas`}
      />
    );
  }

  if (entregas === null) {
    // Esqueleto com a forma do resultado, nunca roda girando (DESIGN.md §5).
    return (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-5/6" />
      </div>
    );
  }

  if (entregas.length === 0) {
    return (
      <EstadoVazio
        titulo="Nenhuma entrega registrada nesta fonte"
        explicacao="Enquanto a plataforma não chamar a rota do webhook, esta lista fica vazia — e é assim que ela deve ficar. Um exemplo aqui pareceria tráfego que nunca existiu."
        endpoint={`POST /integracoes/webhook/${fonteId}`}
      />
    );
  }

  // A contagem sai da propria lista, nunca de um contador a parte: contador
  // separado e a forma mais barata de o cabecalho dizer 18 com 17 linhas
  // abaixo dele.
  const contagem = new Map<Veredito, number>();
  for (const entrega of entregas) {
    const vistas = contagem.get(entrega.veredito);
    contagem.set(entrega.veredito, vistas === undefined ? 1 : vistas + 1);
  }

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <p className="text-xs text-muted-foreground">
        {[...contagem.entries()].map(([veredito, quantas], indice) => {
          const { rotulo, cor } = descreverVeredito(veredito);
          return (
            <span key={veredito}>
              {indice > 0 ? " · " : null}
              <span className="num tabular-nums text-foreground">{quantas}</span>{" "}
              <span className={cor}>{rotulo}</span>
            </span>
          );
        })}
      </p>

      <ul className="flex flex-col">
        {entregas.map((entrega) => {
          const { rotulo, cor } = descreverVeredito(entrega.veredito);
          return (
            <li
              key={entrega.id}
              className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 border-b border-compasso py-1.5 last:border-b-0"
            >
              <span className="num shrink-0 text-xs whitespace-nowrap text-muted-foreground">
                {formatarDataHora(entrega.recebida_em)}
              </span>
              <span className={`shrink-0 text-xs ${cor}`}>{rotulo}</span>
              <span className="num shrink-0 text-xs text-muted-foreground">
                {/* Ausencia vira travessao, nunca 0 nem string vazia
                    (invariante 2): uma entrega recusada nao gerou conversa
                    nenhuma, e um id vazio se leria como campo quebrado. */}
                conversa {entrega.conversa_id ?? "—"}
              </span>
              {entrega.motivo ? (
                <span className="min-w-0 text-xs text-muted-foreground">
                  {entrega.motivo}
                </span>
              ) : null}
            </li>
          );
        })}
      </ul>

      {/* A ressalva vai UMA vez, no pe do bloco. Repetida por linha ela viraria
          ruido e pararia de ser lida -- e ela precisa ser lida, porque explica
          por que a lista some e por que ela nao mostra o que o cliente disse. */}
      <p className="border-t border-compasso pt-2 text-xs leading-relaxed text-muted-foreground">
        O Fraus guarda as últimas 200 entregas de cada fonte e nunca o corpo da
        requisição — ele traz mensagem de cliente real.
      </p>
    </div>
  );
}
