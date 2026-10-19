/**
 * =============================================================================
 * INTEGRAÇÕES — por onde a conversa entra, e o que de fato entrou
 *
 * O TARS vem primeiro (19/10/2026): é a integração pronta, em dois cliques.
 * Abaixo, o mestre-detalhe das fontes genéricas de webhook.
 *
 * A importação de arquivo por pasta do servidor SAIU desta tela: na Vercel a
 * pasta não existe, e arquivo entra pela tela Analisar, que salva nos
 * indicadores. As rotas de importação continuam na API.
 *
 * A regra que a interface precisa dizer em voz alta: o campo de segredo guarda
 * o NOME de uma variável de ambiente, nunca a credencial. Por isso não há campo
 * de senha nesta tela.
 * =============================================================================
 */

import { baseDaApi, listarFontes, listarTiposDeFonte } from "@/lib/api";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Painel } from "@/components/Painel";
import { Fontes } from "@/components/integracoes/Fontes";
import { ConectarTars } from "@/components/integracoes/ConectarTars";

export const dynamic = "force-dynamic";

export default async function PaginaIntegracoes() {
  const [fontes, tipos] = await Promise.all([listarFontes(), listarTiposDeFonte()]);

  return (
    <>
      <CabecalhoPagina
        titulo="Integrações"
        subtitulo="Conecte o chatbot e os atendimentos chegam sozinhos, já pontuados e somados aos indicadores."
      />

      {/* SEM flex-1: ver o comentario identico em app/dashboard/page.tsx. */}
      <div className="flex min-w-0 flex-col gap-4 px-4 py-4 sm:px-6">
        <Painel titulo="TARS" nivel="dominante" semPadding>
          {fontes.ok ? (
            <ConectarTars fontes={fontes.dado} baseDaApi={baseDaApi()} />
          ) : (
            <EstadoVazio
              className="m-5"
              titulo="As fontes não carregaram"
              explicacao={`${fontes.erro}. Sem a listagem não dá para saber se o TARS já está conectado.`}
              endpoint="GET /integracoes/fontes"
            />
          )}
        </Painel>

        <details className="group">
          <summary className="cursor-pointer px-1 text-sm text-muted-foreground hover:text-foreground">
            Outras integrações — webhook assinado para qualquer plataforma
          </summary>
          <div className="mt-3">
            {/* A regra que esta seção precisa dizer em voz alta: o campo de
                segredo guarda o NOME de uma variável de ambiente, nunca a
                credencial. Recolher é permitido; remover não. */}
            <Painel
              titulo="Fontes"
              legenda="Cada fonte registra por onde a conversa entra. O segredo não mora aqui: o que se guarda é o nome da variável de ambiente que a API lê na máquina onde ela roda."
            >
              {fontes.ok ? (
                <Fontes
                  iniciais={fontes.dado}
                  tipos={tipos.ok ? tipos.dado : []}
                  baseDaApi={baseDaApi()}
                />
              ) : (
                <EstadoVazio
                  titulo="As fontes não carregaram"
                  explicacao={`${fontes.erro}. Sem a listagem não há como dizer quais integrações existem nem quais credenciais estão presentes — e desenhar uma lista plausível aqui seria inventar integração.`}
                  endpoint="GET /integracoes/fontes"
                />
              )}
            </Painel>
          </div>
        </details>
      </div>
    </>
  );
}
