"use client";

import { useCallback, useEffect, useState } from "react";
import { KeyRound, Plus, Trash2 } from "lucide-react";
import type { EstadoDeAcesso } from "@/lib/api";
import { ChaveEmClaro } from "@/components/ChaveEmClaro";
import { Painel } from "@/components/Painel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatarData } from "@/lib/formato";
import { lerListaDaResposta } from "@/lib/resposta";
import { IconeDeAcao } from "@/components/IconeDeAcao";

type ChaveAcesso = {
  id: number;
  nome: string;
  /** Os 4 últimos caracteres. O hash NUNCA sai da API. */
  dica: string | null;
  criada_em: string;
};

/**
 * Emitir, listar e revogar as chaves de acesso -- sem terminal.
 *
 * As tres rotas existiam na API desde a autenticacao (`/acesso/chaves`) e nao
 * tinham tela nenhuma: emitir uma chave para uma segunda maquina, ou cortar uma
 * que vazou, exigia montar um `curl` com a mestra na mao. A operacao mais
 * corriqueira do modelo de credenciais era a unica sem interface.
 *
 * POR QUE ELE PEDE A MESTRA. Gerenciar chave e privilegio exclusivo da mestra:
 * uma chave de acesso que pudesse emitir outra chave nao seria um posto menor,
 * e a API responde 403 a quem tenta. A dashboard tem a chave de ACESSO (no
 * cookie ou no ambiente), nunca a mestra -- entao ela precisa ser digitada, e
 * fica so na memoria deste componente: nao vai para `localStorage`, nem para
 * cookie, nem para a URL. Fechar a aba a esquece, e isso e o comportamento
 * desejado, nao uma limitacao.
 *
 * Com a API ABERTA nada disso e exigido, e o painel carrega sozinho -- e o
 * mesmo criterio do resto do modo local.
 */
export function ChavesDeAcesso({ estado }: { estado: EstadoDeAcesso }) {
  const precisaDeMestra = estado.ligada;

  const [mestra, setMestra] = useState("");
  const [autenticado, setAutenticado] = useState(!precisaDeMestra);
  const [chaves, setChaves] = useState<ChaveAcesso[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [nomeNovo, setNomeNovo] = useState("");
  const [emitida, setEmitida] = useState<{ nome: string; chave: string } | null>(null);
  const [confirmando, setConfirmando] = useState<number | null>(null);

  /** O cabeçalho de toda chamada: a mestra digitada, quando há uma. */
  const autorizacao = useCallback((): Record<string, string> => {
    return mestra.trim() ? { authorization: `Bearer ${mestra.trim()}` } : {};
  }, [mestra]);

  const carregar = useCallback(async () => {
    setOcupado(true);
    setErro(null);
    try {
      const resposta = await fetch("/api/fraus/chaves", {
        cache: "no-store",
        headers: autorizacao(),
      });
      const leitura = await lerListaDaResposta<ChaveAcesso>(resposta);
      if (!leitura.ok) {
        // A frase da API é a instrução ("esta rota exige a chave mestra").
        setErro(leitura.erro);
        setAutenticado(false);
        return;
      }
      setChaves(leitura.itens);
      setAutenticado(true);
    } catch {
      setErro("não foi possível falar com a dashboard");
    } finally {
      setOcupado(false);
    }
  }, [autorizacao]);

  // Carrega sozinho SÓ quando não há credencial a pedir. Com a autenticação
  // ligada, quem dispara é o botão -- buscar antes teria um 403 garantido.
  //
  // O fetch é escrito aqui em vez de reusar `carregar()` porque aquele começa
  // com um `setOcupado(true)` SÍNCRONO, e escrever estado durante o efeito é o
  // que a regra do React proíbe. Numa cadeia de `.then` toda escrita já
  // aconteceu depois -- é o mesmo idioma do resto do shell.
  //
  // FALHA NÃO É LISTA VAZIA: a cadeia olhava só o corpo, e o `{detail}` de um
  // erro caía em `[]` -- "Nenhuma chave de acesso emitida" com a API fora do
  // ar. Ver `lib/resposta.ts`.
  useEffect(() => {
    if (precisaDeMestra) return;
    let vivo = true;
    fetch("/api/fraus/chaves", { cache: "no-store" })
      .then((resposta) => lerListaDaResposta<ChaveAcesso>(resposta))
      .then((leitura) => {
        if (!vivo) return;
        if (!leitura.ok) {
          setErro(leitura.erro);
          return;
        }
        setChaves(leitura.itens);
        setAutenticado(true);
      })
      .catch(() => {
        if (vivo) setErro("não foi possível falar com a dashboard");
      });
    return () => {
      vivo = false;
    };
  }, [precisaDeMestra]);

  async function emitir() {
    const nome = nomeNovo.trim();
    if (!nome) return;
    setOcupado(true);
    setErro(null);
    try {
      const resposta = await fetch("/api/fraus/chaves", {
        method: "POST",
        headers: { ...autorizacao(), "content-type": "application/json" },
        body: JSON.stringify({ nome }),
      });
      const corpo = await resposta.json().catch(() => null);
      if (!resposta.ok) {
        setErro(corpo?.detail ?? `a API respondeu ${resposta.status}`);
        return;
      }
      // A chave em claro fica na tela até ele dispensar: ela não pode ser lida
      // de novo, e recarregar a lista por cima a apagaria antes da cópia.
      setEmitida({ nome: corpo.nome, chave: corpo.chave });
      setNomeNovo("");
    } catch {
      setErro("não foi possível falar com a dashboard");
    } finally {
      setOcupado(false);
    }
  }

  async function revogar(id: number) {
    setOcupado(true);
    setErro(null);
    try {
      const resposta = await fetch(`/api/fraus/chaves/${id}`, {
        method: "DELETE",
        headers: autorizacao(),
      });
      if (!resposta.ok && resposta.status !== 204) {
        const corpo = await resposta.json().catch(() => null);
        setErro(corpo?.detail ?? `a API respondeu ${resposta.status}`);
        return;
      }
      setConfirmando(null);
      await carregar();
    } catch {
      setErro("não foi possível falar com a dashboard");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <Painel
      titulo="Chaves de acesso"
      legenda="A credencial de leitura da API — é ela que a dashboard apresenta. Cada chave aparece em claro uma única vez, na emissão: o servidor guarda apenas o hash, e a lista mostra só os quatro últimos caracteres para você reconhecer qual é qual."
      rodape="Revogar vale na chamada seguinte, sem reiniciar nada. Se uma chave de acesso vazar, revogue só ela — trocar a mestra não é necessário e desconectaria quem administra. Emitir e revogar são privilégio da mestra: a própria chave de acesso não pode gerar outra."
    >
      <div className="flex flex-col gap-3">
        {erro ? (
          <Alert variant="destructive">
            <AlertTitle>Não foi possível</AlertTitle>
            <AlertDescription>{erro}</AlertDescription>
          </Alert>
        ) : null}

        {emitida ? (
          <ChaveEmClaro chave={emitida.chave} titulo={`Chave “${emitida.nome}” — copie agora`}>
            <p>
              Não pode ser lida de novo. Use em{" "}
              <code className="num">FRAUS_CHAVE_ACESSO</code> para subir outra
              dashboard, ou em <code className="num">Authorization: Bearer</code>{" "}
              para ler a API direto. Se perdê-la, revogue e emita outra.
            </p>
            <div className="mt-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  setEmitida(null);
                  void carregar();
                }}
              ><IconeDeAcao acao="confirmar" />
                Já copiei
              </Button>
            </div>
          </ChaveEmClaro>
        ) : null}

        {precisaDeMestra && !autenticado ? (
          <div className="flex flex-col gap-2">
            <p className="text-xs leading-relaxed text-muted-foreground">
              A autenticação está ligada, e gerenciar chaves é privilégio da{" "}
              <strong className="text-foreground">mestra</strong>. Ela fica
              apenas nesta aba, em memória — não é gravada em lugar nenhum.
            </p>
            <p className="text-xs leading-relaxed text-muted-foreground">
              Se a autenticação ligou sozinha na primeira subida da API, ela
              está em <code className="num">.fraus-chaves.txt</code>, na raiz do
              projeto. Ler os atendimentos não precisa dela — a dashboard já usa
              a chave de acesso do mesmo arquivo.
            </p>
            <Label htmlFor="mestra-chaves" className="text-foreground">
              Chave mestra
            </Label>
            <Input
              id="mestra-chaves"
              type="password"
              autoComplete="off"
              className="num"
              placeholder="frm_…"
              value={mestra}
              onChange={(evento) => setMestra(evento.target.value)}
              onKeyDown={(evento) => {
                if (evento.key === "Enter" && mestra.trim()) void carregar();
              }}
            />
            <div>
              <Button
                type="button"
                size="sm"
                onClick={() => void carregar()}
                disabled={ocupado || mestra.trim() === ""}
              >
                <KeyRound aria-hidden />
                {ocupado ? "Consultando…" : "Ver as chaves"}
              </Button>
            </div>
          </div>
        ) : null}

        {autenticado ? (
          <>
            {chaves === null ? (
              <p className="text-xs text-muted-foreground">
                {/* Com a leitura falhada, "carregando" ficaria ali para sempre. */}
                {erro
                  ? "A lista de chaves não pôde ser lida — o motivo está acima."
                  : "carregando…"}
              </p>
            ) : chaves.length === 0 ? (
              <p className="text-xs leading-relaxed text-muted-foreground">
                Nenhuma chave de acesso emitida. Enquanto a API estiver aberta
                isso não impede nada; depois de ligar a autenticação, a dashboard
                precisa de uma para ler.
              </p>
            ) : (
              <ul className="flex flex-col divide-y divide-[var(--linha)] rounded-md border border-[var(--linha)]">
                {chaves.map((chave) => (
                  <li
                    key={chave.id}
                    className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-xs"
                  >
                    <span className="min-w-0 flex-1 truncate text-foreground">
                      {chave.nome}
                    </span>
                    <span className="num shrink-0 text-muted-foreground">
                      {chave.dica ? `····${chave.dica}` : "—"}
                    </span>
                    <span className="num shrink-0 text-muted-foreground">
                      {formatarData(chave.criada_em)}
                    </span>
                    {confirmando === chave.id ? (
                      <span className="flex shrink-0 items-center gap-1">
                        {/* Confirmação inline em vez de `confirm()`: o diálogo
                            nativo some no meio de uma ação irreversível e não
                            diz o que vai acontecer. */}
                        <span className="text-muted-foreground">revogar?</span>
                        <Button
                          type="button"
                          size="sm"
                          variant="destructive"
                          className="h-6 px-2"
                          onClick={() => void revogar(chave.id)}
                          disabled={ocupado}
                        ><IconeDeAcao acao="remover" />
                          Sim
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2"
                          onClick={() => setConfirmando(null)}
                        ><IconeDeAcao acao="cancelar" />
                          Não
                        </Button>
                      </span>
                    ) : (
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="h-6 shrink-0 px-2"
                        onClick={() => setConfirmando(chave.id)}
                        disabled={ocupado}
                        title={`Revoga a chave “${chave.nome}” imediatamente`}
                      >
                        <Trash2 aria-hidden />
                        Revogar
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            <div className="flex flex-wrap items-end gap-2">
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <Label htmlFor="nome-chave" className="text-foreground">
                  Nome da nova chave
                </Label>
                <Input
                  id="nome-chave"
                  autoComplete="off"
                  placeholder="notebook-joao"
                  value={nomeNovo}
                  onChange={(evento) => setNomeNovo(evento.target.value)}
                  onKeyDown={(evento) => {
                    if (evento.key === "Enter" && nomeNovo.trim()) void emitir();
                  }}
                />
              </div>
              <Button
                type="button"
                size="sm"
                onClick={() => void emitir()}
                disabled={ocupado || nomeNovo.trim() === ""}
              >
                <Plus aria-hidden />
                {ocupado ? "Emitindo…" : "Emitir chave"}
              </Button>
            </div>
            <p className="text-[11px] leading-tight text-muted-foreground">
              O nome é para você reconhecer a chave depois — ele não dá nem tira
              permissão nenhuma. Toda chave de acesso lê a API inteira.
            </p>
          </>
        ) : null}
      </div>
    </Painel>
  );
}
