"use client";

import { useId, useState, type ReactNode } from "react";
import { KeyRound, Pencil, Trash2 } from "lucide-react";
import type { FonteIntegracao, TipoDeFonte } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { ChaveDaFonte } from "./ChaveDaFonte";
import { ContratoDoWebhook } from "./ContratoDoWebhook";
import { Entregas } from "./Entregas";
import { SegredoDoWebhook } from "./SegredoDoWebhook";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * Uma faixa do detalhe: titulo curto, a ressalva que explica ESTE controle
 * logo abaixo dele, e o controle.
 *
 * A prosa nao mora mais no rodape do painel. Tres rodapes empilhados no pe da
 * tela sao tres ressalvas nao lidas -- a regra ja foi corrigida duas vezes
 * neste projeto. Nenhum texto foi cortado: cada um desceu para junto do
 * controle de que ele fala.
 */
function Bloco({
  titulo,
  nota,
  children,
}: {
  titulo: string;
  nota?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="min-w-0 border-t border-linha pt-4">
      <h4 className="rotulo-instrumento">
        {titulo}
      </h4>
      {nota ? (
        <p className="mt-1 max-w-[72ch] text-xs leading-relaxed text-muted-foreground">
          {nota}
        </p>
      ) : null}
      <div className="mt-3 min-w-0">{children}</div>
    </section>
  );
}

/**
 * O DETALHE do mestre-detalhe: tudo que e de UMA fonte.
 *
 * O condicional `fonte.tipo === "webhook"` deste arquivo RAMIFICA no campo
 * `tipo`, que ate esta branch era so um rotulo numa celula de tabela. Fonte
 * `csv` nao ganha bloco de webhook -- e nao ganhar e a informacao, porque URL
 * de webhook numa fonte que ninguem chama pela rede seria uma promessa.
 *
 * Ele ESPELHA a decisao do servidor, nunca a substitui: o passo 6 do porteiro
 * em `fraus/api/rotas/webhook.py` recusa entrega em fonte que nao seja
 * `webhook` com 403 `tipo_incompativel`. Enquanto essa checagem morou so aqui,
 * a tela prometia uma recusa que a API nao fazia.
 */
export function PainelDaFonte({
  fonte,
  tipos: TIPOS,
  baseDaApi,
  ocupada,
  aoRenomear,
  aoTrocarVariavel,
  aoAlternarAtiva,
  aoRemover,
}: {
  fonte: FonteIntegracao;
  tipos: TipoDeFonte[];
  baseDaApi: string;
  ocupada: boolean;
  /**
   * Devolve se o servidor aceitou. O campo de edição só fecha com `true`:
   * fechar antes da resposta perde o nome digitado justamente na recusa, que é
   * quando ele ainda é preciso para corrigir e reenviar.
   */
  aoRenomear: (fonte: FonteIntegracao, nome: string) => Promise<boolean>;
  /** Devolve se o servidor aceitou; ver `aoRenomear`. */
  aoTrocarVariavel: (fonte: FonteIntegracao, variavel: string | null) => Promise<boolean>;
  aoAlternarAtiva: (fonte: FonteIntegracao) => void;
  /** Devolve se o servidor aceitou; ver `aoRenomear`. */
  aoRemover: (fonte: FonteIntegracao) => Promise<boolean>;
}) {
  const identificador = useId();
  const [renomeando, setRenomeando] = useState(false);
  const [nomeEmEdicao, setNomeEmEdicao] = useState("");
  const [confirmandoRemocao, setConfirmandoRemocao] = useState(false);

  /**
   * Renomeia e só fecha o campo se deu certo.
   *
   * O `await` é o ponto: sem ele o formulário desmontava no mesmo quadro em que
   * a chamada partia, e nada do que vem depois da resposta chegava a existir na
   * tela -- nem o `disabled` durante o envio, nem o nome digitado de volta para
   * corrigir depois de um 4xx.
   */
  async function salvarRenome() {
    if (nomeEmEdicao.trim() === "") return;
    const aceitou = await aoRenomear(fonte, nomeEmEdicao);
    if (aceitou) setRenomeando(false);
  }

  async function confirmarRemocao() {
    const aceitou = await aoRemover(fonte);
    if (aceitou) setConfirmandoRemocao(false);
  }

  const rotuloTipo =
    TIPOS.find((tipo) => tipo.valor === fonte.tipo)?.rotulo ?? fonte.tipo;
  const ehWebhook = fonte.tipo === "webhook";

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <header className="flex min-w-0 flex-col gap-3">
        <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-4 gap-y-2">
          <div className="min-w-0">
            {renomeando ? (
              <div className="flex flex-wrap items-center gap-2">
                <Label
                  htmlFor={`${identificador}-renome`}
                  className="sr-only"
                >
                  Novo nome da fonte
                </Label>
                <Input
                  // `useId`, como o resto da familia. O id fixo funcionava so
                  // porque um unico painel fica montado por vez -- era a unica
                  // id global do modulo, e colidiria calada no dia em que dois
                  // detalhes coexistissem.
                  id={`${identificador}-renome`}
                  className="h-8 w-56"
                  autoFocus
                  value={nomeEmEdicao}
                  onChange={(evento) => setNomeEmEdicao(evento.target.value)}
                  onKeyDown={(evento) => {
                    if (evento.key === "Enter") salvarRenome();
                    if (evento.key === "Escape") setRenomeando(false);
                  }}
                />
                <Button
                  type="button"
                  size="xs"
                  onClick={salvarRenome}
                  disabled={ocupada || nomeEmEdicao.trim() === ""}
                >
                  {ocupada ? "Salvando…" : "Salvar"}
                </Button>
                <Button
                  type="button"
                  size="xs"
                  variant="ghost"
                  onClick={() => setRenomeando(false)}
                >
                  Cancelar
                </Button>
              </div>
            ) : (
              <h3 className="titulo-instrumento truncate text-base text-foreground">
                {fonte.nome}
              </h3>
            )}
            <p className="mt-1 text-xs text-muted-foreground">
              {fonte.canal} · {rotuloTipo} ·{" "}
              <span className="num">
                cadastrada em {formatarData(fonte.criada_em)}
              </span>
            </p>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-1.5">
            <Badge variant={fonte.ativa ? "outline" : "ghost"}>
              {fonte.ativa ? "Ativa" : "Inativa"}
            </Badge>
            <Button
              type="button"
              size="xs"
              variant="ghost"
              onClick={() => {
                setNomeEmEdicao(fonte.nome);
                setRenomeando(true);
                setConfirmandoRemocao(false);
              }}
              disabled={renomeando}
            >
              <Pencil aria-hidden />
              Renomear
            </Button>
            <Button
              type="button"
              size="xs"
              variant="outline"
              onClick={() => aoAlternarAtiva(fonte)}
              disabled={ocupada}
            >
              {fonte.ativa ? "Desativar" : "Ativar"}
            </Button>
            <Button
              type="button"
              size="xs"
              variant="ghost"
              onClick={() => {
                setConfirmandoRemocao(true);
                setRenomeando(false);
              }}
              disabled={confirmandoRemocao}
            >
              <Trash2 aria-hidden />
              Remover
            </Button>
          </div>
        </div>

        {/* A ressalva do segredo desceu do rodape do painel para o lado do
            proprio estado que ela qualifica: e aqui, lendo "variavel definida",
            que alguem pode concluir que o valor esta certo. */}
        <div className="min-w-0 rounded-sm border border-compasso bg-muted/30 p-3">
          <p className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
            <span className="text-xs text-muted-foreground">
              <KeyRound
                aria-hidden
                className="mr-1 inline size-3 -translate-y-px"
              />
              Segredo:
            </span>
            {fonte.variavel_segredo ? (
              <>
                <span className="num text-xs text-foreground">
                  {fonte.variavel_segredo}
                </span>
                <span
                  className={`text-[0.6875rem] ${
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
          </p>
          {/* A ressalva so aparece quando ha o que ressalvar. Sem variavel
              nomeada nao existe "variavel definida" para ninguem interpretar
              errado, e o paragrafo viraria ruido -- que e como ressalva para de
              ser lida. Ela nao foi cortada: mora ao lado do estado que
              qualifica, e aparece em toda fonte que nomeia uma variavel. */}
          {fonte.variavel_segredo ? (
            <p className="mt-1.5 max-w-[72ch] text-[0.6875rem] leading-relaxed text-muted-foreground">
              “Variável definida” responde apenas se a variável existe no
              ambiente da API, verificado a cada leitura — não se o valor dela
              está correto. O valor nunca sai da API, nem mascarado: máscara
              vaza tamanho e prefixo por um caminho mais lento.
            </p>
          ) : null}
        </div>

        {confirmandoRemocao ? (
          <div className="rounded-sm border border-border bg-muted/40 p-3">
            <p className="max-w-[70ch] text-xs leading-relaxed text-foreground">
              Remover <strong>{fonte.nome}</strong> apaga só o cadastro da
              origem.{" "}
              <strong>Nenhum atendimento já importado é apagado</strong> —
              conversa que entrou é dado medido, e apagar a origem não pode
              reescrever o histórico.
            </p>
            <div className="mt-2 flex gap-2">
              <Button
                type="button"
                size="xs"
                variant="destructive"
                onClick={confirmarRemocao}
                disabled={ocupada}
              >
                {ocupada ? "Removendo…" : "Remover o cadastro"}
              </Button>
              <Button
                type="button"
                size="xs"
                variant="ghost"
                onClick={() => setConfirmandoRemocao(false)}
              >
                Manter
              </Button>
            </div>
          </div>
        ) : null}
      </header>

      <Bloco
        titulo="Chave de API"
        nota="Credencial do envio direto para POST /ingestao. Ela aparece uma única vez: o servidor guarda só o hash, e não há rota para reler."
      >
        <ChaveDaFonte fonte={fonte} base={baseDaApi} />
      </Bloco>

      {/* O CONDICIONAL. Fonte csv nao ganha bloco de webhook -- e o primeiro
          lugar em que o campo `tipo` deixa de ser rotulo e passa a decidir o
          que existe na tela. */}
      {ehWebhook ? (
        <>
          <Bloco
            titulo="Segredo de assinatura"
            nota="O que a plataforma usa para assinar cada entrega, e o que a API usa para conferir. Ele mora no ambiente da máquina, não no banco."
          >
            <SegredoDoWebhook
              fonte={fonte}
              ocupada={ocupada}
              aoTrocarVariavel={(variavel) => aoTrocarVariavel(fonte, variavel)}
            />
          </Bloco>

          <Bloco
            titulo="Contrato do webhook"
            nota="A URL desta fonte e os três cabeçalhos que a entrega precisa trazer."
          >
            <ContratoDoWebhook fonte={fonte} base={baseDaApi} />
          </Bloco>

          <Bloco
            titulo="Entregas"
            nota="O que de fato chegou nesta URL, e o veredito de cada tentativa — é aqui que se descobre se a integração passou."
          >
            <Entregas fonteId={fonte.id} />
          </Bloco>
        </>
      ) : (
        <Bloco titulo="Webhook">
          <p className="max-w-[72ch] text-xs leading-relaxed text-muted-foreground">
            Esta fonte é do tipo{" "}
            <span className="text-foreground">{rotuloTipo}</span> e não recebe
            entrega pela rede: não há URL de webhook, segredo de assinatura nem
            histórico de entregas para ela. Exibir os três aqui prometeria um
            endereço que a API recusa — a rota do webhook confere o tipo da
            fonte no servidor e responde <span className="num">403</span>, mesmo
            com assinatura válida.
          </p>
        </Bloco>
      )}
    </div>
  );
}
