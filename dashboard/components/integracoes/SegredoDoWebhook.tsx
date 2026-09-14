"use client";

import { useId, useState } from "react";
import { Pencil, ShieldPlus } from "lucide-react";
import { gerarSegredo, type FonteIntegracao } from "@/lib/api";
import { ChaveEmClaro } from "@/components/ChaveEmClaro";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/**
 * O segredo de assinatura do webhook: gerar, copiar, colocar no ambiente.
 *
 * O segredo em claro vive apenas no estado deste componente. Nada de
 * localStorage, sessionStorage ou URL -- ele tem que morrer quando a tela sai,
 * pelo mesmo motivo documentado em `ChaveDaFonte.tsx`: o servidor NAO guarda
 * copia nenhuma dele, nem o hash, e nao ha rota para reler. Aqui e ate mais
 * forte que na chave `frs_` -- o Fraus precisa do segredo em claro toda vez
 * para RECOMPUTAR o HMAC, e por isso ele mora numa variavel de ambiente da
 * maquina, fora do banco.
 */
export function SegredoDoWebhook({
  fonte,
  ocupada,
  aoTrocarVariavel,
}: {
  fonte: FonteIntegracao;
  ocupada: boolean;
  /**
   * Corrige o NOME da variável sem recriar a fonte — recriar trocaria o id,
   * e com ele a URL que a plataforma já tem configurada.
   */
  aoTrocarVariavel: (variavel: string | null) => Promise<boolean>;
}) {
  const identificador = useId();
  const [editando, setEditando] = useState(false);
  const [variavelEmEdicao, setVariavelEmEdicao] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [segredo, setSegredo] = useState<string | null>(null);

  const semVariavel = fonte.variavel_segredo === null;

  async function gerar() {
    setOcupado(true);
    setErro(null);
    const resposta = await gerarSegredo(fonte.id);
    setOcupado(false);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }
    setSegredo(resposta.dado.segredo);
  }

  return (
    <div className="flex min-w-0 flex-col gap-3">
      {erro ? (
        <Alert variant="destructive">
          <AlertTitle>Não foi possível</AlertTitle>
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      ) : null}

      {/* Sem segunda copia do aviso de "copie agora": ele e parte da
          credencial, mora no `ChaveEmClaro` junto da chave `frs_` e da mestra,
          e duas copias divergiriam -- a que divergisse prometeria menos. */}
      {segredo ? (
        <ChaveEmClaro
          chave={segredo}
          titulo="Copie agora — este segredo não pode ser lido de novo"
        >
          <p>
            O Fraus não guarda cópia dele, nem o hash: ele precisa do valor em
            claro para recalcular a assinatura, e por isso mora no ambiente da
            máquina. Se você perder, o conserto é gerar outro — e a plataforma
            para de ser aceita até receber a cópia nova.
          </p>
        </ChaveEmClaro>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={gerar}
          disabled={ocupado || semVariavel}
        >
          <ShieldPlus aria-hidden />
          {segredo ? "Gerar outro segredo" : "Gerar segredo de assinatura"}
        </Button>

        {semVariavel ? (
          <span className="text-xs text-muted-foreground">
            Cadastre antes o nome da variável de ambiente desta fonte: sem ela
            não há onde o valor morar, e um segredo gerado agora se perderia na
            mesma tela.
          </span>
        ) : null}
      </div>

      {editando ? (
        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={async (evento) => {
            evento.preventDefault();
            // Fecha só com o aceite: na recusa o nome digitado ainda é preciso.
            if (await aoTrocarVariavel(variavelEmEdicao.trim() || null)) setEditando(false);
          }}
        >
          <div className="flex min-w-0 flex-col gap-1">
            <Label htmlFor={`${identificador}-variavel`} className="text-xs font-normal text-muted-foreground">
              Nome da variável de ambiente — o nome, nunca o segredo
            </Label>
            <Input
              id={`${identificador}-variavel`}
              className="num h-8 w-64 max-w-full"
              value={variavelEmEdicao}
              placeholder="FRAUS_SEGREDO_WHATSAPP"
              autoFocus
              onChange={(evento) => setVariavelEmEdicao(evento.target.value)}
            />
          </div>
          <Button type="submit" size="sm" disabled={ocupada}>
            Salvar
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={() => setEditando(false)} disabled={ocupada}>
            Cancelar
          </Button>
        </form>
      ) : (
        <Button
          type="button"
          size="xs"
          variant="ghost"
          className="self-start"
          onClick={() => {
            setVariavelEmEdicao(fonte.variavel_segredo ?? "");
            setEditando(true);
          }}
          disabled={ocupada}
        >
          <Pencil aria-hidden />
          {semVariavel ? "Nomear a variável de ambiente" : "Corrigir o nome da variável"}
        </Button>
      )}

      <ol className="flex flex-col gap-1.5 text-xs leading-relaxed text-muted-foreground">
        <li>
          <span className="num text-foreground">1.</span> Gere o segredo aqui —
          ele aparece uma única vez.
        </li>
        <li>
          <span className="num text-foreground">2.</span> Defina{" "}
          <code className="num rounded-sm bg-muted px-1 py-0.5 text-foreground">
            {fonte.variavel_segredo ?? "a variável de ambiente da fonte"}
          </code>{" "}
          no ambiente onde a API roda e reinicie-a.
        </li>
        <li>
          <span className="num text-foreground">3.</span> Entregue a{" "}
          <strong>mesma cópia</strong> à plataforma que vai assinar as entregas.
          Os dois lados precisam do mesmo valor: é o que o HMAC compara.
        </li>
      </ol>

      {!semVariavel && !fonte.configurada ? (
        <Alert variant="destructive">
          <AlertTitle>
            A variável{" "}
            <code className="num">{fonte.variavel_segredo}</code> não está
            definida no ambiente da API
          </AlertTitle>
          <AlertDescription>
            {/* NOMEAR O STATUS e o inteiro deste aviso: 503 manda o operador
                olhar a maquina, 401 o mandaria depurar a requisicao de quem
                integra -- por um defeito que nao e de quem integra. */}
            <p>
              Enquanto isso, a rota do webhook responde{" "}
              <strong>503</strong> — não 401. O problema está na máquina que
              hospeda a API, não na requisição da plataforma.
            </p>
          </AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
