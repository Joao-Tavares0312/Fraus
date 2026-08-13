"use client";

import { useId, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, KeyRound, Pencil, Plus, Trash2 } from "lucide-react";
import {
  ajustarFonte,
  apagarFonte,
  criarFonte,
  listarFontes,
  type FonteIntegracao,
} from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EstadoVazio } from "@/components/EstadoVazio";

/**
 * Os tipos que a ingestao de fato sabe tratar hoje, iguais a `TIPOS_DE_FONTE`
 * do servidor. Cadastrar um tipo que nenhum adapter le seria cadastrar uma
 * promessa -- a fonte apareceria na tela sem nunca trazer conversa nenhuma.
 */
const TIPOS = [
  { valor: "csv", rotulo: "CSV", ajuda: "arquivo importado por /conversas/importar" },
  { valor: "webhook", rotulo: "Webhook", ajuda: "recebe eventos da plataforma" },
] as const;

const NOVA_VAZIA = { nome: "", canal: "", tipo: "csv", variavel_segredo: "" };

export function Fontes({ iniciais }: { iniciais: FonteIntegracao[] }) {
  const router = useRouter();
  const identificador = useId();
  const [fontes, setFontes] = useState(iniciais);
  const [nova, setNova] = useState(NOVA_VAZIA);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupada, setOcupada] = useState<number | "nova" | null>(null);
  const [renomeando, setRenomeando] = useState<number | null>(null);
  const [nomeEmEdicao, setNomeEmEdicao] = useState("");
  const [confirmandoRemocao, setConfirmandoRemocao] = useState<number | null>(
    null,
  );

  async function recarregar() {
    const resposta = await listarFontes();
    if (resposta.ok) setFontes(resposta.dado);
    router.refresh();
  }

  async function adicionar() {
    setErro(null);
    setOcupada("nova");
    const resposta = await criarFonte({
      nome: nova.nome,
      canal: nova.canal,
      tipo: nova.tipo,
      variavel_segredo: nova.variavel_segredo.trim() || null,
    });
    setOcupada(null);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }
    setNova(NOVA_VAZIA);
    await recarregar();
  }

  async function alternarAtiva(fonte: FonteIntegracao) {
    setErro(null);
    setOcupada(fonte.id);
    const resposta = await ajustarFonte(fonte.id, { ativa: !fonte.ativa });
    setOcupada(null);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }
    await recarregar();
  }

  async function confirmarRenome(fonte: FonteIntegracao) {
    setErro(null);
    setOcupada(fonte.id);
    const resposta = await ajustarFonte(fonte.id, { nome: nomeEmEdicao });
    setOcupada(null);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }
    setRenomeando(null);
    await recarregar();
  }

  async function remover(fonte: FonteIntegracao) {
    setErro(null);
    setOcupada(fonte.id);
    const resposta = await apagarFonte(fonte.id);
    setOcupada(null);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }
    setConfirmandoRemocao(null);
    await recarregar();
  }

  return (
    <div className="flex min-w-0 flex-col">
      <div className="border-b border-border p-5">
        <h3 className="text-sm font-medium text-foreground">
          Cadastrar uma fonte
        </h3>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_10rem_minmax(0,1.3fr)_auto]">
          <div className="min-w-0">
            <Label htmlFor={`${identificador}-nome`} className="text-xs">
              Nome
            </Label>
            <Input
              id={`${identificador}-nome`}
              className="mt-1"
              value={nova.nome}
              placeholder="Suporte — Zendesk"
              onChange={(evento) =>
                setNova({ ...nova, nome: evento.target.value })
              }
            />
          </div>

          <div className="min-w-0">
            <Label htmlFor={`${identificador}-canal`} className="text-xs">
              Canal
            </Label>
            <Input
              id={`${identificador}-canal`}
              className="mt-1"
              value={nova.canal}
              placeholder="webchat, whatsapp, instagram…"
              onChange={(evento) =>
                setNova({ ...nova, canal: evento.target.value })
              }
            />
          </div>

          <div className="min-w-0">
            <Label htmlFor={`${identificador}-tipo`} className="text-xs">
              Tipo
            </Label>
            <Select
              value={nova.tipo}
              onValueChange={(valor) =>
                setNova({ ...nova, tipo: valor ?? "csv" })
              }
            >
              <SelectTrigger id={`${identificador}-tipo`} className="mt-1 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIPOS.map(({ valor, rotulo }) => (
                  <SelectItem key={valor} value={valor}>
                    {rotulo}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="min-w-0">
            <Label htmlFor={`${identificador}-segredo`} className="text-xs">
              Nome da variável de ambiente do segredo
            </Label>
            <Input
              id={`${identificador}-segredo`}
              className="num mt-1"
              type="text"
              autoComplete="off"
              spellCheck={false}
              value={nova.variavel_segredo}
              placeholder="FRAUS_TOKEN_ZENDESK"
              aria-describedby={`${identificador}-segredo-ajuda`}
              onChange={(evento) =>
                setNova({ ...nova, variavel_segredo: evento.target.value })
              }
            />
          </div>

          <div className="flex items-end">
            <Button
              type="button"
              onClick={adicionar}
              disabled={
                ocupada === "nova" ||
                nova.nome.trim() === "" ||
                nova.canal.trim() === ""
              }
            >
              <Plus aria-hidden />
              {ocupada === "nova" ? "Cadastrando…" : "Cadastrar"}
            </Button>
          </div>
        </div>

        <p
          id={`${identificador}-segredo-ajuda`}
          className="mt-3 max-w-[80ch] text-xs leading-relaxed text-muted-foreground"
        >
          <KeyRound aria-hidden className="mr-1 inline size-3 -translate-y-px" />
          O campo do segredo guarda o{" "}
          <strong className="text-foreground">
            nome de uma variável de ambiente
          </strong>{" "}
          — <span className="num">FRAUS_TOKEN_ZENDESK</span>, não o token. Por
          isso não existe campo de senha nesta tela: credencial em texto puro
          dentro do SQLite vazaria junto com o backup. Quem lê a variável é a
          API, na máquina onde ela roda.
        </p>
      </div>

      {erro ? (
        <div className="border-b border-border p-5 pb-0">
          <Alert variant="destructive">
            <AlertTriangle aria-hidden />
            <AlertTitle>A API recusou a operação</AlertTitle>
            <AlertDescription>
              <span className="text-destructive">{erro}</span>
            </AlertDescription>
          </Alert>
        </div>
      ) : null}

      {fontes.length === 0 ? (
        <EstadoVazio
          className="m-5"
          titulo="Nenhuma fonte cadastrada"
          explicacao="O cadastro de fontes registra por onde a conversa entra: nome, canal, tipo e o nome da variável de ambiente que carrega a credencial. Enquanto ele estiver vazio, os atendimentos importados continuam existindo — a fonte é o registro da origem, não a origem do dado."
          endpoint="POST /integracoes/fontes"
        />
      ) : (
        <div className="min-w-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fonte</TableHead>
                <TableHead>Canal</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Segredo</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {fontes.map((fonte) => {
                const emEdicao = renomeando === fonte.id;
                const confirmando = confirmandoRemocao === fonte.id;

                return (
                  <TableRow key={fonte.id}>
                    <TableCell className="min-w-56 align-top">
                      {emEdicao ? (
                        <div className="flex items-center gap-2">
                          <Label
                            htmlFor={`${identificador}-renome-${fonte.id}`}
                            className="sr-only"
                          >
                            Novo nome da fonte
                          </Label>
                          <Input
                            id={`${identificador}-renome-${fonte.id}`}
                            className="h-7"
                            autoFocus
                            value={nomeEmEdicao}
                            onChange={(evento) =>
                              setNomeEmEdicao(evento.target.value)
                            }
                          />
                          <Button
                            type="button"
                            size="xs"
                            onClick={() => confirmarRenome(fonte)}
                            disabled={
                              ocupada === fonte.id || nomeEmEdicao.trim() === ""
                            }
                          >
                            Salvar
                          </Button>
                          <Button
                            type="button"
                            size="xs"
                            variant="ghost"
                            onClick={() => setRenomeando(null)}
                          >
                            Cancelar
                          </Button>
                        </div>
                      ) : (
                        <>
                          <span className="text-sm text-foreground">
                            {fonte.nome}
                          </span>
                          <span className="num mt-0.5 block text-[0.6875rem] text-muted-foreground">
                            cadastrada em {formatarData(fonte.criada_em)}
                          </span>
                        </>
                      )}

                      {confirmando ? (
                        <div className="mt-2 rounded-md border border-border bg-muted/40 p-3">
                          <p className="max-w-[70ch] text-xs leading-relaxed text-foreground">
                            Remover <strong>{fonte.nome}</strong> apaga só o
                            cadastro da origem.{" "}
                            <strong>
                              Nenhum atendimento já importado é apagado
                            </strong>{" "}
                            — conversa que entrou é dado medido, e apagar a
                            origem não pode reescrever o histórico.
                          </p>
                          <div className="mt-2 flex gap-2">
                            <Button
                              type="button"
                              size="xs"
                              variant="destructive"
                              onClick={() => remover(fonte)}
                              disabled={ocupada === fonte.id}
                            >
                              {ocupada === fonte.id
                                ? "Removendo…"
                                : "Remover o cadastro"}
                            </Button>
                            <Button
                              type="button"
                              size="xs"
                              variant="ghost"
                              onClick={() => setConfirmandoRemocao(null)}
                            >
                              Manter
                            </Button>
                          </div>
                        </div>
                      ) : null}
                    </TableCell>

                    <TableCell className="align-top text-sm text-muted-foreground">
                      {fonte.canal}
                    </TableCell>

                    <TableCell className="align-top text-sm text-muted-foreground">
                      {TIPOS.find((tipo) => tipo.valor === fonte.tipo)?.rotulo ??
                        fonte.tipo}
                    </TableCell>

                    <TableCell className="align-top">
                      <Badge variant={fonte.ativa ? "outline" : "ghost"}>
                        {fonte.ativa ? "Ativa" : "Inativa"}
                      </Badge>
                    </TableCell>

                    <TableCell className="min-w-56 align-top">
                      {fonte.variavel_segredo ? (
                        <>
                          <span className="num block text-xs text-foreground">
                            {fonte.variavel_segredo}
                          </span>
                          <span
                            className={`mt-0.5 block text-[0.6875rem] ${
                              fonte.configurada
                                ? "text-promotor-texto"
                                : "text-detrator-texto"
                            }`}
                          >
                            {fonte.configurada
                              ? "variável definida no ambiente da API"
                              : "variável ausente no ambiente da API"}
                          </span>
                        </>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          nenhuma variável nomeada
                        </span>
                      )}
                    </TableCell>

                    <TableCell className="align-top">
                      <div className="flex justify-end gap-1.5">
                        <Button
                          type="button"
                          size="xs"
                          variant="ghost"
                          onClick={() => {
                            setRenomeando(fonte.id);
                            setNomeEmEdicao(fonte.nome);
                            setConfirmandoRemocao(null);
                          }}
                          disabled={emEdicao}
                        >
                          <Pencil aria-hidden />
                          Renomear
                        </Button>
                        <Button
                          type="button"
                          size="xs"
                          variant="outline"
                          onClick={() => alternarAtiva(fonte)}
                          disabled={ocupada === fonte.id}
                        >
                          {fonte.ativa ? "Desativar" : "Ativar"}
                        </Button>
                        <Button
                          type="button"
                          size="xs"
                          variant="ghost"
                          onClick={() => {
                            setConfirmandoRemocao(fonte.id);
                            setRenomeando(null);
                          }}
                          disabled={confirmando}
                        >
                          <Trash2 aria-hidden />
                          Remover
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
