"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Download, FileUp, RefreshCw } from "lucide-react";
import {
  importarArquivo,
  listarArquivosImportaveis,
  type ArquivoImportavel,
  type ResultadoImportacao,
} from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EstadoVazio } from "@/components/EstadoVazio";

/**
 * Importar um CSV pela interface.
 *
 * Ate aqui a tela de Integracoes registrava de onde a conversa ENTRARIA e
 * mostrava o que ja tinha entrado, mas nao deixava trazer nada: o unico
 * caminho era `curl` no terminal. Uma tela que se chama "de onde vem os
 * atendimentos" e nao importa atendimento e uma promessa pela metade.
 *
 * A ESCOLHA E POR LISTA, nao por campo de texto. A rota aceita caminho
 * relativo a raiz de importacao e recusa qualquer escape, entao um campo livre
 * so serviria para digitar errado -- e caminho errado volta como "arquivo nao
 * encontrado" sem dizer quais existem. A interface nunca monta caminho a mao:
 * manda de volta exatamente a string que a listagem devolveu.
 *
 * Nao ha upload. Subir arquivo abriria uma superficie de escrita numa API sem
 * autenticacao, e a raiz de importacao existe justamente para limitar de onde
 * o servidor le. Colocar o arquivo na pasta e trabalho de quem opera a maquina.
 */
export function Importar({
  raiz,
  iniciais,
}: {
  raiz: string;
  iniciais: ArquivoImportavel[];
}) {
  const router = useRouter();
  const [arquivos, setArquivos] = useState(iniciais);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<
    (ResultadoImportacao & { arquivo: string }) | null
  >(null);

  async function recarregar() {
    setOcupado("lista");
    setErro(null);
    const resposta = await listarArquivosImportaveis();
    setOcupado(null);
    if (resposta.ok) setArquivos(resposta.dado.arquivos);
    else setErro(resposta.erro);
  }

  async function importar(caminho: string) {
    setOcupado(caminho);
    setErro(null);
    setResultado(null);
    const resposta = await importarArquivo(caminho);
    setOcupado(null);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }
    setResultado({ ...resposta.dado, arquivo: caminho });
    // O histórico e os indicadores das outras telas mudaram: revalida o que o
    // servidor renderizou em vez de manter a página descrevendo o passado.
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-4 px-5 py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          Arquivos em{" "}
          <code className="num rounded-sm bg-muted px-1 py-0.5 text-foreground">
            {raiz}/
          </code>
          . Coloque o CSV nessa pasta para ele aparecer aqui.
        </p>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={recarregar}
          disabled={ocupado !== null}
        >
          <RefreshCw aria-hidden />
          Reler a pasta
        </Button>
      </div>

      {erro ? (
        <Alert variant="destructive">
          <AlertTitle>A importação falhou</AlertTitle>
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      ) : null}

      {/* O resultado nomeia o que ficou DE FORA, nao so o que entrou:
          "importado com sucesso" sem a contagem de rejeitadas esconde
          exatamente a linha que o operador precisa consertar. */}
      {resultado ? (
        <Alert>
          <AlertTitle>
            <span className="num">{resultado.importadas}</span> atendimento(s)
            importado(s) de {resultado.arquivo}
          </AlertTitle>
          <AlertDescription>
            {resultado.rejeitadas === 0 ? (
              "Nenhuma linha foi rejeitada."
            ) : (
              <>
                <span className="num">{resultado.rejeitadas}</span> linha(s)
                rejeitada(s). O motivo de cada uma fica no histórico abaixo.
              </>
            )}
          </AlertDescription>
        </Alert>
      ) : null}

      {arquivos.length === 0 ? (
        <EstadoVazio
          titulo="Nenhum CSV na pasta de importação"
          explicacao={`A raiz de importação (${raiz}/) não tem nenhum arquivo .csv. Ela é a única pasta de onde o servidor aceita ler — caminho que escape dela é recusado com 400.`}
          endpoint="GET /integracoes/arquivos"
        />
      ) : (
        <ul className="flex flex-col">
          {arquivos.map((arquivo) => (
            <li
              key={arquivo.caminho}
              className="flex flex-wrap items-center justify-between gap-3 border-b border-compasso py-2 last:border-b-0"
            >
              <span className="flex min-w-0 items-center gap-2">
                <FileUp
                  aria-hidden
                  className="size-4 shrink-0 text-muted-foreground"
                />
                <span className="num truncate text-sm text-foreground">
                  {arquivo.caminho}
                </span>
                <span className="num shrink-0 text-xs text-muted-foreground">
                  {formatarBytes(arquivo.bytes)}
                </span>
              </span>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => importar(arquivo.caminho)}
                disabled={ocupado !== null}
              >
                <Download aria-hidden />
                {ocupado === arquivo.caminho ? "Importando…" : "Importar"}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Tamanho legivel. Arquivo de atendimento raramente passa de alguns MB. */
function formatarBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} kB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
