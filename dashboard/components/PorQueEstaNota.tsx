"use client";

import { useState } from "react";
import { simularContrafactual } from "@/lib/api";
import type { Contrafactual, Explicacao } from "@/lib/api";
import { ROTULO_SINAL, type PesoDaFeature, type SinalDaFeature } from "@/lib/derivacoes";
import { formatarComSinal, formatarNumero } from "@/lib/formato";
import { BarrasDeFeature } from "./BarrasDeFeature";
import { EstadoVazio } from "./EstadoVazio";

/** Abaixo disto o efeito arredonda para zero na tela: nao vira barra. */
const EFEITO_MINIMO = 1;

/**
 * "Por que esta nota": a explicacao EXATA do servidor, so desenhada aqui.
 *
 * Nada e calculado no cliente (invariante 3): frases, efeitos por familia e
 * o antes/depois do contrafactual chegam prontos. O que este componente
 * decide e so o que NAO desenhar -- familia com efeito < 1 ponto fica fora,
 * porque "0,0 pontos" diria que o sinal foi medido e nao pesou. Sem
 * explicacao o estado vazio nomeia o que falta (invariante 2): a pagina
 * so monta este componente quando ha contribuicoes, entao a ausencia aqui e
 * API antiga ou motor sem decomposicao -- nunca "sem sinal do cliente", que
 * e o estado vazio do PainelContribuicoes.
 */
export function PorQueEstaNota({
  conversaId,
  explicacao,
  comSinal,
}: {
  conversaId: string;
  explicacao: Explicacao | null;
  /**
   * `atribuicao.contribuicoes !== null`, dado que o servidor ja mandou. Sem
   * sinal do cliente o unico vazio da tela e o do PainelContribuicoes, que
   * nomeia o `motivoSemSinal`; um segundo empilharia e diria menos.
   */
  comSinal: boolean;
}) {
  if (!comSinal) return null;
  if (!explicacao) {
    return (
      <EstadoVazio
        className="m-5"
        titulo="Explicação indisponível nesta versão da API"
        explicacao="Esta conversa tem sinal do cliente, mas a resposta da API não trouxe o campo `explicacao` (API mais antiga que a dashboard, ou motor sem decomposição). Nenhum efeito por sinal é mostrado em vez de inventar um."
        endpoint="GET /conversas/{id}/atribuicao"
      />
    );
  }

  const familias: PesoDaFeature[] = Object.entries(explicacao.efeitos)
    .filter(([, efeito]) => Math.abs(efeito) >= EFEITO_MINIMO)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .map(([familia, efeito], _i, todas) => ({
      nome: familia,
      rotulo: ROTULO_SINAL[familia as SinalDaFeature] ?? familia,
      sinal: familia as SinalDaFeature,
      valor: efeito,
      fracao: Math.abs(efeito) / Math.abs(todas[0][1]),
    }));

  return (
    <div className="flex flex-col gap-4 border-b border-border px-5 py-4">
      <ul className="flex flex-col gap-1.5">
        {explicacao.frases.map((frase) => (
          <li key={frase} className="text-sm text-foreground">
            {frase}
          </li>
        ))}
      </ul>

      {familias.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="rotulo-instrumento">efeito por família, em pontos de score</p>
          <BarrasDeFeature
            features={familias}
            modo="divergente"
            formatarValor={(valor) => `${formatarComSinal(valor, 1)} pts`}
          />
        </div>
      )}

      <p className="max-w-[62ch] text-xs text-muted-foreground">{explicacao.aviso}</p>

      <FormularioContrafactual conversaId={conversaId} />
    </div>
  );
}

function FormularioContrafactual({ conversaId }: { conversaId: string }) {
  const [segundos, setSegundos] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<Contrafactual | null>(null);

  async function calcular(evento: React.FormEvent) {
    evento.preventDefault();
    const valor = Number(segundos);
    if (segundos.trim() === "" || !Number.isFinite(valor)) return;
    setCarregando(true);
    setErro(null);
    const resposta = await simularContrafactual(conversaId, {
      primeira_resposta_s: valor,
    });
    setCarregando(false);
    if (resposta.ok) {
      setResultado(resposta.dado);
    } else {
      // O 422 explica por que a hipotese foi recusada: some so quando o
      // proximo calculo der certo.
      setResultado(null);
      setErro(resposta.erro);
    }
  }

  return (
    <form onSubmit={calcular} className="flex flex-col gap-2 border-t border-compasso pt-3">
      <label htmlFor="contrafactual-s" className="text-xs text-foreground">
        E se a primeira resposta tivesse chegado em
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <input
          id="contrafactual-s"
          type="number"
          inputMode="decimal"
          min={0}
          max={86400}
          step="any"
          value={segundos}
          onChange={(e) => setSegundos(e.target.value)}
          className="num h-8 w-28 border border-linha bg-transparent px-2 text-xs text-foreground"
        />
        <span className="text-xs text-muted-foreground">segundos?</span>
        <button
          type="submit"
          disabled={carregando || segundos.trim() === ""}
          className="h-8 border border-linha px-3 text-xs text-foreground hover:bg-accent disabled:opacity-50"
        >
          {carregando ? "Calculando…" : "Calcular"}
        </button>
      </div>

      <div aria-live="polite" className="flex flex-col gap-1">
        {erro && <p className="text-xs text-detrator-texto">{erro}</p>}
        {resultado && (
          <>
            <p className="num text-xs text-foreground">
              antes {formatarNumero(resultado.antes.score, 1)} → depois{" "}
              {formatarNumero(resultado.depois.score, 1)} (
              {formatarComSinal(resultado.delta_score, 1)} pts) · nota{" "}
              {formatarNumero(resultado.antes.nota, 1)} →{" "}
              {formatarNumero(resultado.depois.nota, 1)} ·{" "}
              {resultado.antes.categoria} → {resultado.depois.categoria}
            </p>
            <p className="max-w-[62ch] text-xs text-muted-foreground">
              {resultado.metodo}
            </p>
          </>
        )}
      </div>
    </form>
  );
}
