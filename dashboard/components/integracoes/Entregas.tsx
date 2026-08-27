"use client";

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { listarEntregas, type Entrega, type Veredito } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * A ordem canonica dos vereditos, a mesma do tipo `Veredito` e a mesma de
 * `VEREDITOS` no Python.
 *
 * Existe para o cabecalho de contagem NAO dancar: derivada da ordem de
 * aparicao na lista, ela se reorganizava a cada carregamento conforme o que
 * tinha chegado por ultimo. Esta e a tela que o operador fica olhando enquanto
 * depura -- ela nao pode trocar de forma sozinha.
 *
 * E um `Record<Veredito, number>`, e nao um array, pelo mesmo motivo de o
 * `switch` abaixo nao ter `default`: o `Record` exige TODAS as chaves, entao
 * veredito novo no tipo que nao entre aqui vira erro de tipo. Um array de
 * `Veredito[]` aceitaria a lista incompleta em silencio, e o veredito faltante
 * sumiria do cabecalho sem nunca sumir da lista.
 */
const ORDEM_DOS_VEREDITOS: Record<Veredito, number> = {
  aceita: 0,
  assinatura: 1,
  fora_da_janela: 2,
  duplicada: 3,
  corpo_invalido: 4,
  fonte_inativa: 5,
  sem_segredo: 6,
  tipo_incompativel: 7,
};

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
 * SAO DOIS ROTULOS porque sao duas frases diferentes. Na linha da lista o
 * veredito qualifica UMA entrega e o singular esta certo ("assinatura
 * invalida"); no cabecalho ele vem depois de uma contagem, e "18 aceita" e
 * agramatical. Concordar no cabecalho sem estragar a linha exige os dois.
 *
 * A cor segue a §3.3 do DESIGN.md: nada de `--primary` aqui, porque o dourado e
 * acao e foco e NUNCA dado. `sem_segredo` e o unico em vermelho porque e o
 * unico defeito da MAQUINA que hospeda -- a variavel de ambiente nao esta la, a
 * rota responde 503, e nenhuma plataforma do outro lado consegue consertar.
 */
function descreverVeredito(veredito: Veredito): {
  /** Uma entrega, na linha da lista. */
  rotulo: string;
  /** Varias entregas, depois da contagem no cabecalho. */
  plural: string;
  cor: string;
} {
  switch (veredito) {
    case "aceita":
      return {
        rotulo: "aceita",
        plural: "aceitas",
        cor: "text-promotor-texto",
      };
    case "assinatura":
      return {
        rotulo: "assinatura inválida",
        plural: "com assinatura inválida",
        cor: "text-muted-foreground",
      };
    case "fora_da_janela":
      return {
        rotulo: "fora da janela de tempo",
        plural: "fora da janela de tempo",
        cor: "text-muted-foreground",
      };
    case "duplicada":
      return {
        rotulo: "reentrega",
        plural: "reentregas",
        cor: "text-muted-foreground",
      };
    case "corpo_invalido":
      return {
        rotulo: "corpo fora do contrato",
        plural: "com corpo fora do contrato",
        cor: "text-muted-foreground",
      };
    case "fonte_inativa":
      return {
        rotulo: "fonte desativada",
        plural: "recusadas por fonte desativada",
        cor: "text-muted-foreground",
      };
    case "sem_segredo":
      return {
        rotulo: "segredo ausente no ambiente da API",
        plural: "sem segredo no ambiente da API",
        cor: "text-detrator-texto",
      };
    case "tipo_incompativel":
      return {
        rotulo: "fonte não é do tipo webhook",
        plural: "recusadas por a fonte não ser do tipo webhook",
        cor: "text-muted-foreground",
      };
  }
}

/**
 * O historico de entregas de webhook de uma fonte.
 *
 * Busca no CLIENTE, e nao no servidor da pagina: esta lista muda enquanto a
 * tela esta aberta -- e ela que o operador olha enquanto aponta a plataforma
 * para ca e ve a primeira chamada chegar. E por isso que existe o botao
 * "Atualizar": sem ele a promessa era falsa, porque descobrir se a integracao
 * passou exigiria recarregar a pagina inteira, exatamente como na lista
 * renderizada uma vez no servidor.
 *
 * BOTAO, E NAO POLLING, e a escolha e deliberada: laco de fundo bate na API sem
 * ninguem pedir, e o Fraus roda inferencia em CPU local na mesma maquina. Quem
 * disparou a chamada do outro lado sabe quando vale olhar de novo.
 */
export function Entregas({ fonteId }: { fonteId: number }) {
  /**
   * A rodada de busca. Trocar de valor E o pedido de buscar de novo.
   *
   * O botao so incrementa isto, num manipulador de evento, e quem busca
   * continua sendo o efeito unico abaixo -- nenhuma segunda copia de
   * `listarEntregas`, de tratamento de erro ou de protecao contra corrida.
   * Chamar a busca direto do `onClick` exigiria `setEstado` sincrono fora do
   * efeito e duplicaria os dois caminhos, que e como eles divergem depois.
   */
  const [rodada, setRodada] = useState(0);

  /**
   * O resultado carrega a fonte E a rodada a que ele pertence.
   *
   * E o que dispensa um `setEstado(null)` no corpo do efeito -- render em
   * cascata, que o ESLint recusa. E cobre a janela que o `vivo` nao cobre: o
   * intervalo entre a re-renderizacao com `fonteId` novo e a chegada da
   * resposta, em que a lista da fonte anterior apareceria sob o nome da nova.
   */
  const [estado, setEstado] = useState<{
    fonteId: number;
    rodada: number;
    entregas: Entrega[] | null;
    erro: string | null;
  } | null>(null);

  useEffect(() => {
    let vivo = true;
    listarEntregas(fonteId).then((resposta) => {
      if (!vivo) return;
      setEstado(
        resposta.ok
          ? { fonteId, rodada, entregas: resposta.dado, erro: null }
          : { fonteId, rodada, entregas: null, erro: resposta.erro },
      );
    });
    // Trocar de fonte ou pedir outra rodada descarta a resposta em voo: sem
    // isto, a resposta antiga chegando depois pintaria a lista de outra fonte.
    return () => {
      vivo = false;
    };
  }, [fonteId, rodada]);

  const atual =
    estado !== null && estado.fonteId === fonteId ? estado : null;
  const erro = atual === null ? null : atual.erro;
  const entregas = atual === null ? null : atual.entregas;
  // Em voo e DERIVADO, nunca um `setBuscando(true)` no efeito. Enquanto a
  // resposta desta rodada nao chegou, o botao fica desabilitado.
  const emVoo = atual === null || atual.rodada !== rodada;

  const botao = (
    <Button
      type="button"
      size="sm"
      onClick={() => setRodada((anterior) => anterior + 1)}
      disabled={emVoo}
    >
      <RefreshCw aria-hidden />
      Atualizar
    </Button>
  );

  if (erro) {
    return (
      <div className="flex min-w-0 flex-col items-start gap-3">
        <EstadoVazio
          titulo="Não foi possível ler as entregas desta fonte"
          explicacao={erro}
          endpoint={`GET /integracoes/fontes/${fonteId}/entregas`}
        />
        {botao}
      </div>
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
      <div className="flex min-w-0 flex-col items-start gap-3">
        <EstadoVazio
          titulo="Nenhuma entrega registrada nesta fonte"
          explicacao="Enquanto a plataforma não chamar a rota do webhook, esta lista fica vazia — e é assim que ela deve ficar. Um exemplo aqui pareceria tráfego que nunca existiu."
          endpoint={`POST /integracoes/webhook/${fonteId}`}
        />
        {botao}
      </div>
    );
  }

  // A contagem sai da propria lista, nunca de um contador a parte: contador
  // separado e a forma mais barata de o cabecalho dizer 18 com 17 linhas
  // abaixo dele.
  const contagem = new Map<Veredito, number>();
  for (const entrega of entregas) {
    contagem.set(entrega.veredito, (contagem.get(entrega.veredito) ?? 0) + 1);
  }
  // A ordem e a do tipo, nao a da chegada -- ver ORDEM_DOS_VEREDITOS.
  const resumo = [...contagem.entries()].sort(
    ([a], [b]) => ORDEM_DOS_VEREDITOS[a] - ORDEM_DOS_VEREDITOS[b],
  );

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          {resumo.map(([veredito, quantas], indice) => {
            const { plural, cor } = descreverVeredito(veredito);
            return (
              <span key={veredito}>
                {indice > 0 ? " · " : null}
                <span className="num tabular-nums text-foreground">
                  {quantas}
                </span>{" "}
                <span className={cor}>{plural}</span>
              </span>
            );
          })}
        </p>
        {botao}
      </div>

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
