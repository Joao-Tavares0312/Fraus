"use client";

/**
 * Entrar e cadastrar, no mesmo componente porque dividem tudo: o painel de
 * vidro, os campos, os estados e a regra de que o ERRO VEM DO SERVIDOR — a
 * mensagem uniforme de credencial ("e-mail ou senha inválidos") não pode
 * ganhar variações locais, e reescrevê-la aqui seria a segunda fonte de
 * verdade que o projeto proíbe.
 *
 * O cadastro tem o campo opcional de código de convite: é ele que diferencia
 * o cadastro de dev (spec 2026-08-31, §2.3). Sem código, nasce analista.
 */

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Modo = "entrar" | "cadastrar";

async function detalheDe(resposta: Response): Promise<string> {
  try {
    const corpo = (await resposta.json()) as { detail?: unknown };
    if (typeof corpo.detail === "string") return corpo.detail;
  } catch {
    // corpo não-JSON (ex.: 502 do proxy com HTML) cai no genérico abaixo
  }
  return `o servidor respondeu ${resposta.status}`;
}

export function FormularioAuth({ modo }: { modo: Modo }) {
  const roteador = useRouter();
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);

    const dados = new FormData(evento.currentTarget);
    const email = String(dados.get("email") ?? "");
    const senha = String(dados.get("senha") ?? "");

    try {
      if (modo === "cadastrar") {
        const codigo = String(dados.get("codigo_dev") ?? "").trim();
        const cadastro = await fetch("/api/fraus/auth/registrar", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            nome: String(dados.get("nome") ?? ""),
            email,
            senha,
            ...(codigo ? { codigo_dev: codigo } : {}),
          }),
        });
        if (!cadastro.ok) {
          setErro(await detalheDe(cadastro));
          return;
        }
      }
      const entrada = await fetch("/api/sessao/entrar", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, senha }),
      });
      if (!entrada.ok) {
        setErro(await detalheDe(entrada));
        return;
      }
      roteador.push("/dashboard");
      // Sem `refresh`, o layout da dashboard poderia servir um render antigo
      // de antes do cookie existir.
      roteador.refresh();
    } catch {
      setErro("não foi possível falar com o servidor");
    } finally {
      setEnviando(false);
    }
  }

  const entrando = modo === "entrar";

  return (
    <form onSubmit={enviar} className="flex flex-col gap-4" noValidate={false}>
      {modo === "cadastrar" && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="nome">Nome</Label>
          <Input id="nome" name="nome" required autoComplete="name" />
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">E-mail</Label>
        <Input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="email"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="senha">Senha</Label>
        <Input
          id="senha"
          name="senha"
          type="password"
          required
          minLength={entrando ? undefined : 8}
          autoComplete={entrando ? "current-password" : "new-password"}
        />
        {!entrando && (
          <p className="text-xs text-muted-foreground">Pelo menos 8 caracteres.</p>
        )}
      </div>

      {modo === "cadastrar" && (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="codigo_dev">Código de convite (opcional)</Label>
          <Input id="codigo_dev" name="codigo_dev" autoComplete="off" />
          <p className="text-xs text-muted-foreground">
            Só para desenvolvedores: é o código que dá acesso às telas de
            administração. Sem ele, a conta nasce de analista.
          </p>
        </div>
      )}

      {erro && (
        <p role="alert" className="text-sm text-destructive">
          {erro}
        </p>
      )}

      <Button type="submit" disabled={enviando}>
        {enviando
          ? entrando
            ? "Entrando…"
            : "Criando conta…"
          : entrando
            ? "Entrar"
            : "Criar conta"}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        {entrando ? (
          <>
            Ainda sem conta?{" "}
            <Link href="/cadastrar" className="text-primary underline-offset-4 hover:underline">
              Criar conta
            </Link>
          </>
        ) : (
          <>
            Já tem conta?{" "}
            <Link href="/entrar" className="text-primary underline-offset-4 hover:underline">
              Entrar
            </Link>
          </>
        )}
      </p>
    </form>
  );
}
