/**
 * =============================================================================
 * CONFIGURAÇÕES — a parte "mexer" da dashboard
 *
 * Visão geral e Atendimentos olham. Esta tela muda o comportamento da leitura,
 * e por isso ela é conservadora em dois pontos:
 *
 *   1. Só existe controle para o que a API PERSISTE. Não há interruptor por
 *      sinal (texto/emoji/tempo): os três estão fundidos nos coeficientes de um
 *      modelo já treinado, desligar um exigiria retreinar, e um controle que
 *      não faz o que diz é pior que a ausência dele.
 *   2. A validação mora no servidor. O `400` da API nomeia o problema, e é a
 *      frase dele que chega à tela — reescrevê-la como "erro ao salvar" seria
 *      trocar a única instrução útil por um rótulo.
 * =============================================================================
 */

import { obterConfiguracoes, obterEstadoDeAcesso } from "@/lib/api";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Painel } from "@/components/Painel";
import { FaixasNps } from "@/components/configuracoes/FaixasNps";
import { LimiaresLatencia } from "@/components/configuracoes/LimiaresLatencia";
import { Autenticacao } from "@/components/configuracoes/Autenticacao";
import { ChavesDeAcesso } from "@/components/configuracoes/ChavesDeAcesso";
import type { Faixas } from "@/components/configuracoes/EscalaNps";

export const dynamic = "force-dynamic";

const SUBTITULO =
  "O que esta tela muda vale na LEITURA: as faixas decidem em que categoria cada nota já medida cai, e os limiares decidem onde a espera passa a ser chamada de longa. Nenhum score é recalculado aqui.";

export default async function PaginaConfiguracoes() {
  // As duas em paralelo: uma nao depende da outra, e /acesso/estado responde
  // mesmo quando /configuracoes leva 401 por falta de credencial.
  const [resultado, acesso] = await Promise.all([
    obterConfiguracoes(),
    obterEstadoDeAcesso(),
  ]);

  if (!resultado.ok) {
    return (
      <>
        <CabecalhoPagina titulo="Configurações" subtitulo={SUBTITULO} />
        <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
          {/* O painel de autenticação vem TAMBÉM neste caminho, e de propósito:
              401 por falta de credencial é justamente quando saber o estado da
              autenticação explica o erro logo abaixo. */}

          {acesso.ok ? (
            <Autenticacao estado={acesso.dado} semCredencial={acesso.dado.ligada} />
          ) : null}

          {/* Vem junto neste caminho porque emitir uma chave de acesso é
              exatamente o conserto do 401 que derrubou a leitura acima. */}
          {acesso.ok ? <ChavesDeAcesso estado={acesso.dado} /> : null}

          <EstadoVazio
            titulo="A configuração não carregou"
            explicacao={`${resultado.erro}. Sem ela não há faixa vigente nem padrão de fábrica a exibir — e preencher os campos com 0–6/7–8/9–10 digitados aqui criaria uma segunda fonte da mesma regra, que é exatamente o defeito que esta tela existe para não ter.`}
            endpoint="GET /configuracoes"
          />
        </div>
      </>
    );
  }

  const { vigente, fabrica } = resultado.dado;

  return (
    <>
      <CabecalhoPagina titulo="Configurações" subtitulo={SUBTITULO} />

      <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
        {acesso.ok ? <Autenticacao estado={acesso.dado} /> : null}

        {acesso.ok ? <ChavesDeAcesso estado={acesso.dado} /> : null}

        <Painel
          titulo="Faixas de NPS"
          legenda="Qual nota é detrator, neutro e promotor. É a mesma faixa que o servidor usa para responder /indicadores e /conversas, no mesmo instante — não existe cópia dela na interface."
          semPadding
          rodape="A regra que o servidor cobra: as faixas precisam cobrir 0 a 10 inteiro, sem buraco e sem sobreposição. Ela não é reimplementada aqui — quando a configuração não fecha, a mensagem que aparece é a da API, que diz qual nota ficou de fora."
        >
          <FaixasNps
            vigente={vigente.faixas_nps as Faixas}
            fabrica={fabrica.faixas_nps as Faixas}
          />
        </Painel>

        <Painel
          titulo="Limiares de latência"
          legenda="Onde a interface corta imediato, saudável, longo e crítico. Precisam ser crescentes, em segundos."
          semPadding
          rodape="Os três cortes alimentam a faixa de referência do cartão “Latência mediana” na visão geral e a anotação de espera de cada resposta na transcrição. Eram fixos no código até esta tela existir."
        >
          <LimiaresLatencia
            vigente={vigente.limiares_latencia_s}
            fabrica={fabrica.limiares_latencia_s}
          />
        </Painel>

        <Painel
          titulo="O que esta tela não configura"
          legenda="Ausência declarada, não esquecimento."
        >
          <ul className="flex list-disc flex-col gap-2 pl-5 text-xs leading-relaxed text-muted-foreground">
            <li>
              <strong className="text-foreground">
                Ligar e desligar sinais (texto, emoji, tempo).
              </strong>{" "}
              Os três estão fundidos nos coeficientes de um modelo já treinado:
              desligar um exigiria retreinar o fusor. Um interruptor que não faz
              o que diz é pior que a ausência dele — os pesos de cada sinal estão
              visíveis na tela Modelo.
            </li>
            <li>
              <strong className="text-foreground">
                Corrigir score, nota ou categoria de um atendimento.
              </strong>{" "}
              Os três são derivados no servidor e nunca aceitos do cliente. O que
              muda aqui é a faixa pela qual eles são lidos.
            </li>
            <li>
              <strong className="text-foreground">
                Desligar a autenticação.
              </strong>{" "}
              Ligar é um clique; desligar não é botão. Um controle que baixa a
              defesa numa tela sem login não tem contrapartida de risco
              aceitável — desligar é trabalho de ambiente (apagar a variável e a
              linha do banco).
            </li>
            <li>
              <strong className="text-foreground">
                Limiar de latência do modelo.
              </strong>{" "}
              O sinal de tempo lê os timestamps crus; os cortes acima são de
              exibição. Latência nunca é persistida.
            </li>
          </ul>
        </Painel>
      </div>
    </>
  );
}
