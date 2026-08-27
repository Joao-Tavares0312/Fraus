/**
 * =============================================================================
 * INTEGRAÇÕES — por onde a conversa entra, e o que de fato entrou
 *
 * Duas metades que se sustentam: o cadastro das fontes (a promessa) e o
 * histórico de importação (a prova). Sem a segunda, "importado com sucesso" é
 * alegação — some da tela no instante seguinte e ninguém consegue mais dizer o
 * que ficou de fora.
 *
 * O CORPO DA TELA É O MESTRE-DETALHE das fontes: a lista à esquerda, e tudo que
 * é de uma fonte à direita. A importação de CSV desceu para a faixa do rodapé,
 * junto do histórico — ela é ação de arquivo local, não integração de rede, e
 * ocupava o topo por ordem histórica, de quando o webhook não existia.
 *
 * A regra que a interface precisa dizer em voz alta: o campo de segredo guarda
 * o NOME de uma variável de ambiente, nunca a credencial. Por isso não há campo
 * de senha nesta tela.
 * =============================================================================
 */

import {
  baseDaApi,
  listarArquivosImportaveis,
  listarFontes,
  listarTiposDeFonte,
  listarImportacoes,
} from "@/lib/api";
import { CabecalhoPagina } from "@/components/shell/CabecalhoPagina";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Painel } from "@/components/Painel";
import { Fontes } from "@/components/integracoes/Fontes";
import { Importar } from "@/components/integracoes/Importar";
import { HistoricoImportacoes } from "@/components/integracoes/HistoricoImportacoes";

export const dynamic = "force-dynamic";

export default async function PaginaIntegracoes() {
  // As quatro leituras são independentes de propósito: se o histórico cair, o
  // cadastro de fontes continua de pé, e vice-versa.
  const [fontes, importacoes, importaveis, tipos] = await Promise.all([
    listarFontes(),
    listarImportacoes(),
    listarArquivosImportaveis(),
    listarTiposDeFonte(),
  ]);

  return (
    <>
      <CabecalhoPagina
        titulo="Integrações"
        subtitulo="De onde vêm os atendimentos: as fontes cadastradas, o estado de cada credencial no ambiente da API, e o histórico do que cada importação aceitou e rejeitou."
      />

      <div className="flex min-w-0 flex-1 flex-col gap-4 px-4 py-4 sm:px-6">
        {/* AS FONTES vêm primeiro: é o mestre-detalhe da tela, e é aqui que a
            conversa passa a entrar pela rede. */}
        <Painel titulo="Fontes">
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

        {/* A FAIXA DO RODAPÉ: trazer um CSV de dentro da máquina, e a prova do
            que cada arquivo trouxe. As duas metades da mesma operação, e
            nenhuma delas é integração de rede. */}
        <div className="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
          <Painel titulo="Importar um CSV">
            {importaveis.ok ? (
              <div className="flex min-w-0 flex-col gap-3">
                {/* As duas ressalvas desceram do aparato do painel para junto
                    do controle que elas explicam: no rodapé, empilhadas com as
                    dos vizinhos, elas não eram lidas. */}
                <p className="max-w-[72ch] text-xs leading-relaxed text-muted-foreground">
                  A escolha é por lista porque a rota aceita apenas caminho
                  relativo à raiz de importação e recusa com 400 qualquer
                  caminho que escape dela. A interface devolve ao servidor
                  exatamente a string que ele publicou, sem montar caminho a
                  mão — e <strong>não há upload</strong>: subir arquivo abriria
                  uma superfície de escrita numa API sem autenticação. Colocar o
                  CSV na pasta é trabalho de quem opera a máquina.
                </p>
                <Importar
                  raiz={importaveis.dado.raiz}
                  iniciais={importaveis.dado.arquivos}
                />
              </div>
            ) : (
              <EstadoVazio
                titulo="Não foi possível ler a pasta de importação"
                explicacao={importaveis.erro}
                endpoint="GET /integracoes/arquivos"
              />
            )}
          </Painel>

          <Painel titulo="Histórico de importações" semPadding>
            {!importacoes.ok ? (
              <EstadoVazio
                className="m-5"
                titulo="O histórico não carregou"
                explicacao={`${importacoes.erro}. É ele que dá lastro a “importado com sucesso” — sem o histórico, a contagem de aceitas e rejeitadas não existe em lugar nenhum da interface.`}
                endpoint="GET /integracoes/importacoes"
              />
            ) : importacoes.dado.length === 0 ? (
              <EstadoVazio
                className="m-5"
                titulo="Nenhuma importação registrada"
                explicacao="O histórico é escrito pela própria importação: cada chamada guarda quando foi, qual arquivo, quantas conversas entraram e o motivo de cada linha rejeitada. Enquanto nenhum arquivo tiver sido processado, esta tabela fica vazia — e é assim que ela deve ficar, em vez de mostrar um exemplo."
                endpoint="POST /conversas/importar alimenta GET /integracoes/importacoes"
              />
            ) : (
              <>
                <p className="px-5 pb-3 text-xs leading-relaxed text-muted-foreground">
                  Mais recente primeiro. Arquivo recusado na porta — caminho
                  fora da raiz de importação, coluna estrutural ausente — não
                  vira linha aqui: nada foi processado, e listar a tentativa como
                  evento de dado contaria uma importação que não houve.
                </p>
                <HistoricoImportacoes historico={importacoes.dado} />
              </>
            )}
          </Painel>
        </div>
      </div>
    </>
  );
}
