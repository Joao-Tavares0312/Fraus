"use client";

import { useId, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, KeyRound, Plus, X } from "lucide-react";
import {
  ajustarFonte,
  apagarFonte,
  criarFonte,
  listarFontes,
  type FonteIntegracao,
  type TipoDeFonte,
} from "@/lib/api";
import { ListaDeFontes } from "./ListaDeFontes";
import { PainelDaFonte } from "./PainelDaFonte";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { EstadoVazio } from "@/components/EstadoVazio";

/*
 * A lista de tipos VEM DO SERVIDOR (`GET /integracoes/tipos`), passada como
 * prop. Ela morava aqui, duplicada de `TIPOS_DE_FONTE`, e duplicata assim so
 * fica errada no dia em que um tipo novo entrar na API: o formulario seguiria
 * oferecendo os dois antigos, sem erro nenhum -- o terceiro existiria no
 * servidor e nao existiria na tela. Cadastrar um tipo que nenhum adapter le
 * seria cadastrar uma promessa.
 */

const NOVA_VAZIA = { nome: "", canal: "", tipo: "csv", variavel_segredo: "" };

/**
 * O MESTRE-DETALHE das fontes.
 *
 * A tabela saiu. Ela tinha seis colunas mais uma linha inteira por fonte so
 * para a chave, e o webhook somaria mais quatro blocos por fonte -- a doze
 * fontes a tela seria uma coluna de rolagem sem lugar nenhum para pousar. A
 * lista fica estreita e constante; a fonte escolhida abre a direita com tudo
 * que e dela.
 *
 * A SELECAO ACOMPANHA A LISTA, e isso e o que evita o painel preso num
 * fantasma: cadastrar seleciona a nova, e qualquer recarga que nao encontre
 * mais o id selecionado limpa a selecao em vez de renderizar uma fonte que o
 * servidor ja nao tem.
 */
export function Fontes({
  iniciais,
  tipos: TIPOS,
  baseDaApi,
}: {
  iniciais: FonteIntegracao[];
  /** Publicados por `GET /integracoes/tipos` — nunca digitados aqui. */
  tipos: TipoDeFonte[];
  /**
   * O endereço da API no exemplo de `curl`. Vem por prop, do servidor: é lá
   * que `FRAUS_API_URL` existe, e uma variável pública só para exibir isto
   * seria um segundo endereço configurável que pode discordar do real.
   */
  baseDaApi: string;
}) {
  const router = useRouter();
  const identificador = useId();
  const [fontes, setFontes] = useState(iniciais);
  const [nova, setNova] = useState(NOVA_VAZIA);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupada, setOcupada] = useState<number | "nova" | null>(null);
  const [selecionada, setSelecionada] = useState<number | null>(
    iniciais[0]?.id ?? null,
  );
  const [cadastrando, setCadastrando] = useState(false);

  // O formulario aparece quando alguem pede `[+]` OU quando nao ha nada para
  // escolher -- e a segunda metade e DERIVADA, nao um estado inicial. Inicial
  // ela ja deixou a tela sem saida uma vez: quem entrava com fontes (formulario
  // fechado) e removia todas ficava numa tela cujo estado vazio mandava "comece
  // pelo formulario acima", sem formulario acima nenhum.
  const formularioAberto = cadastrando || fontes.length === 0;

  const podeCadastrar =
    ocupada !== "nova" && nova.nome.trim() !== "" && nova.canal.trim() !== "";
  const fonteAberta = fontes.find((fonte) => fonte.id === selecionada) ?? null;

  /**
   * Recarrega a lista e, se pedido, mira numa fonte.
   *
   * `mirar` existe porque o cadastro precisa selecionar a fonte que acabou de
   * nascer, e o id dela so existe DEPOIS da resposta. Sem isso, cadastrar
   * deixaria o painel direito na fonte anterior.
   */
  async function recarregar(mirar?: number) {
    const resposta = await listarFontes();
    if (resposta.ok) {
      setFontes(resposta.dado);
      setSelecionada((atual) => {
        const alvo = mirar ?? atual;
        return resposta.dado.some((fonte) => fonte.id === alvo) ? alvo : null;
      });
    }
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
    setCadastrando(false);
    await recarregar(resposta.dado.id);
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

  /**
   * Renomeia e DEVOLVE se deu certo.
   *
   * O booleano nao e enfeite: quem chama fecha o campo de edicao, e fechar
   * antes da resposta joga fora o nome digitado exatamente no caso em que ele
   * ainda e preciso -- o da recusa. So o servidor sabe se o nome passou.
   */
  async function confirmarRenome(fonte: FonteIntegracao, nome: string) {
    setErro(null);
    setOcupada(fonte.id);
    const resposta = await ajustarFonte(fonte.id, { nome });
    setOcupada(null);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return false;
    }
    await recarregar();
    return true;
  }

  async function trocarVariavel(fonte: FonteIntegracao, variavel: string | null) {
    setErro(null);
    setOcupada(fonte.id);
    const resposta = await ajustarFonte(fonte.id, { variavel_segredo: variavel });
    setOcupada(null);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return false;
    }
    await recarregar();
    return true;
  }

  async function remover(fonte: FonteIntegracao) {
    setErro(null);
    setOcupada(fonte.id);
    const resposta = await apagarFonte(fonte.id);
    setOcupada(null);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return false;
    }
    // Remover a fonte aberta limpa a selecao: o painel direito nao pode
    // continuar exibindo um cadastro que o servidor acabou de apagar.
    if (selecionada === fonte.id) setSelecionada(null);
    await recarregar();
    return true;
  }

  return (
    <div className="flex min-w-0 flex-col gap-4">
      {formularioAberto ? (
        <div className="min-w-0 border border-linha bg-muted/20 p-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="titulo-instrumento text-sm text-foreground">
              Cadastrar uma fonte
            </h3>
            {fontes.length > 0 ? (
              <Button
                type="button"
                size="xs"
                variant="ghost"
                onClick={() => setCadastrando(false)}
              >
                <X aria-hidden />
                Fechar
              </Button>
            ) : null}
          </div>

          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_10rem_minmax(0,1.3fr)_auto]">
            <div className="min-w-0">
              <Label htmlFor={`${identificador}-nome`} className="text-xs xl:min-h-9 xl:items-end">
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
                onKeyDown={(evento) => {
                  if (evento.key === "Enter" && podeCadastrar) adicionar();
                }}
              />
            </div>

            <div className="min-w-0">
              <Label htmlFor={`${identificador}-canal`} className="text-xs xl:min-h-9 xl:items-end">
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
                onKeyDown={(evento) => {
                  if (evento.key === "Enter" && podeCadastrar) adicionar();
                }}
              />
            </div>

            <div className="min-w-0">
              <Label htmlFor={`${identificador}-tipo`} className="text-xs xl:min-h-9 xl:items-end">
                Tipo
              </Label>
              <Select
                value={nova.tipo}
                onValueChange={(valor) =>
                  setNova({ ...nova, tipo: valor ?? "csv" })
                }
              >
                <SelectTrigger
                  id={`${identificador}-tipo`}
                  className="mt-1 w-full"
                >
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
              <p className="mt-1 text-[0.6875rem] leading-relaxed text-muted-foreground">
                {TIPOS.find((tipo) => tipo.valor === nova.tipo)?.ajuda}
              </p>
            </div>

            <div className="min-w-0">
              <Label htmlFor={`${identificador}-segredo`} className="text-xs xl:min-h-9 xl:items-end">
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
                onKeyDown={(evento) => {
                  if (evento.key === "Enter" && podeCadastrar) adicionar();
                }}
              />
              {/* A prosa de honestidade nao foi cortada: ela desceu do rodape
                  do painel para debaixo do proprio campo que explica. */}
              <p
                id={`${identificador}-segredo-ajuda`}
                className="mt-2 max-w-[72ch] text-[0.6875rem] leading-relaxed text-muted-foreground"
              >
                <KeyRound
                  aria-hidden
                  className="mr-1 inline size-3 -translate-y-px"
                />
                O campo do segredo guarda o{" "}
                <strong className="text-foreground">
                  nome de uma variável de ambiente
                </strong>{" "}
                — <span className="num">FRAUS_TOKEN_ZENDESK</span>, não o token.
                Por isso não existe campo de senha nesta tela: credencial em
                texto puro dentro do SQLite vazaria junto com o backup. Quem lê
                a variável é a API, na máquina onde ela roda.
              </p>
            </div>

            <div className="flex items-start sm:items-end">
              <Button type="button" onClick={adicionar} disabled={!podeCadastrar}>
                <Plus aria-hidden />
                {ocupada === "nova" ? "Cadastrando…" : "Cadastrar"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {erro ? (
        <Alert variant="destructive">
          <AlertTriangle aria-hidden />
          <AlertTitle>A API recusou a operação</AlertTitle>
          <AlertDescription>
            <span className="text-destructive">{erro}</span>
          </AlertDescription>
        </Alert>
      ) : null}

      {/* Abaixo de `lg` a coluna mestre vira uma faixa acima do painel, e a
          regua muda de lado junto (borda de baixo em vez de borda a direita):
          uma linha vertical entre dois blocos empilhados nao separa nada. */}
      <div className="grid min-w-0 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,15rem)_minmax(0,1fr)] lg:gap-6">
        <div className="min-w-0 border-b border-linha pb-2 lg:border-r lg:border-b-0 lg:pr-4 lg:pb-0">
          <ListaDeFontes
            fontes={fontes}
            tipos={TIPOS}
            selecionada={selecionada}
            aoSelecionar={(id) => {
              setSelecionada(id);
              setCadastrando(false);
            }}
            aoCadastrar={() => setCadastrando(true)}
          />
        </div>

        <div className="min-w-0">
          {fonteAberta ? (
            // `key` remonta o detalhe ao trocar de fonte: o renome em curso e a
            // confirmacao de remocao sao de UMA fonte, e carrega-los para a
            // proxima ofereceria "Remover" com o nome trocado.
            <PainelDaFonte
              key={fonteAberta.id}
              fonte={fonteAberta}
              tipos={TIPOS}
              baseDaApi={baseDaApi}
              ocupada={ocupada === fonteAberta.id}
              aoRenomear={confirmarRenome}
              aoTrocarVariavel={trocarVariavel}
              aoAlternarAtiva={alternarAtiva}
              aoRemover={remover}
            />
          ) : fontes.length === 0 ? (
            <EstadoVazio
              titulo="Nenhuma fonte cadastrada"
              explicacao="O cadastro de fontes registra por onde a conversa entra: nome, canal, tipo e o nome da variável de ambiente que carrega a credencial. Enquanto ele estiver vazio, os atendimentos importados continuam existindo — a fonte é o registro da origem, não a origem do dado. Comece pelo formulário acima."
              endpoint="POST /integracoes/fontes"
            />
          ) : (
            <EstadoVazio
              titulo="Escolha uma fonte à esquerda"
              // A tela abre já na primeira fonte, de propósito: é tela de
              // operação, e obrigar um clique para ver qualquer coisa seria
              // cerimônia. Este vazio é o do caminho em que a seleção se
              // desfez — a fonte aberta foi removida, ou sumiu numa recarga.
              explicacao="Chave de API, segredo de assinatura, contrato do webhook e histórico de entregas são de uma fonte por vez. A fonte que estava aberta aqui não existe mais na lista — escolha outra à esquerda para continuar."
            />
          )}
        </div>
      </div>
    </div>
  );
}
