/**
 * =============================================================================
 * INTEGRAÇÕES — por onde a conversa entra, e o que de fato entrou
 *
 * Duas metades que se sustentam: o cadastro das fontes (a promessa) e o
 * histórico de importação (a prova). Sem a segunda, "importado com sucesso" é
 * alegação — some da tela no instante seguinte e ninguém consegue mais dizer o
 * que ficou de fora.
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
  // As duas leituras são independentes de propósito: se o histórico cair, o
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
        {/* A IMPORTACAO vem primeiro: e a acao da tela. Cadastro de fonte e
            historico descrevem e comprovam; so este bloco traz atendimento
            para dentro do produto. */}
        <Painel
          titulo="Importar atendimentos"
          legenda="A rota aceita apenas caminho relativo à raiz de importação, e recusa com 400 qualquer caminho que escape dela — inclusive caminho absoluto e `../..`. Por isso a escolha é por lista: a interface devolve ao servidor exatamente a string que ele publicou, sem montar caminho a mão."
          semPadding
          rodape="Não há upload por aqui de propósito. Subir arquivo abriria uma superfície de escrita numa API sem autenticação; colocar o CSV na pasta é trabalho de quem opera a máquina."
        >
          {importaveis.ok ? (
            <Importar
              raiz={importaveis.dado.raiz}
              iniciais={importaveis.dado.arquivos}
            />
          ) : (
            <EstadoVazio
              className="m-5"
              titulo="Não foi possível ler a pasta de importação"
              explicacao={importaveis.erro}
              endpoint="GET /integracoes/arquivos"
            />
          )}
        </Painel>

        <Painel
          titulo="Fontes"
          legenda="Cada fonte registra por onde a conversa entra. O segredo não mora aqui: o que se guarda é o nome da variável de ambiente que a API lê na máquina onde ela roda."
          semPadding
          rodape="“Variável definida” responde apenas se a variável existe no ambiente da API, verificado a cada leitura — não se o valor dela está correto. O valor nunca sai da API, nem mascarado: máscara vaza tamanho e prefixo por um caminho mais lento."
        >
          {fontes.ok ? (
            <Fontes
              iniciais={fontes.dado}
              tipos={tipos.ok ? tipos.dado : []}
              baseDaApi={baseDaApi()}
            />
          ) : (
            <EstadoVazio
              className="m-5"
              titulo="As fontes não carregaram"
              explicacao={`${fontes.erro}. Sem a listagem não há como dizer quais integrações existem nem quais credenciais estão presentes — e desenhar uma lista plausível aqui seria inventar integração.`}
              endpoint="GET /integracoes/fontes"
            />
          )}
        </Painel>

        <Painel
          titulo="Histórico de importações"
          legenda="Mais recente primeiro. Quantas conversas cada arquivo trouxe, quantas linhas ficaram de fora e por quê — o relato vem do servidor, que registra o mesmo que devolveu na importação."
          semPadding
          rodape="Arquivo recusado na porta (caminho fora da raiz de importação, coluna estrutural ausente) não vira linha aqui: nada foi processado, e listar a tentativa como evento de dado contaria uma importação que não houve."
        >
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
            <HistoricoImportacoes historico={importacoes.dado} />
          )}
        </Painel>
      </div>
    </>
  );
}
