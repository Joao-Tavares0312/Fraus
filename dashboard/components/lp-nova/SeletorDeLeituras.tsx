"use client";

import { useEffect, useId, useState } from "react";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { falasDecisivas, marcasDaAtribuicao, type MarcaAtribuicao } from "@/lib/derivacoes";
import { humorDaCategoria } from "@/lib/lp-nova/humor";
import { concordaComRoteiro, dataDaGravacao, type ConjuntoLeituras, type IdLeitura, type Leitura } from "@/lib/lp-nova/leituras";
import { useCena } from "./CenaLeitura";

const TITULOS: Record<IdLeitura, { aba: string; tese: string }> = {
  obrigado: { aba: "O obrigado", tese: "Agradeceu e saiu sem solução." },
  ironia: { aba: "A ironia", tese: "Elogiou para reclamar." },
  espera: { aba: "A espera", tese: "Educado do início ao fim, esperando." },
  promotor: { aba: "O promotor", tese: "Resolveu na hora, e o elogio é sincero." },
  "sem-sinal": { aba: "Sem sinal", tese: "O cliente nunca escreveu." },
};

const ROTULO_SENTIDO = {
  puxou_para_baixo: "puxou a nota para baixo",
  puxou_para_cima: "puxou a nota para cima",
  sem_inclinacao: "sem inclinação clara",
} as const;

function porcentagem(v: number) {
  return `${Math.round(v * 100)}%`;
}

/**
 * A CONVERSAO DA PAGINA: o visitante escolhe uma leitura e ve o Fraus ler.
 *
 * Tudo que aparece aqui veio do servidor na gravacao: nota, categoria e a
 * probabilidade por mensagem. As marcas saem de `marcasDaAtribuicao`, a MESMA
 * funcao da transcricao da dashboard -- uma fonte so para "o que puxou a nota".
 * A cena de fundo muda de humor com a categoria escolhida.
 */
export function SeletorDeLeituras({ conjunto }: { conjunto: ConjuntoLeituras }) {
  const [atual, setAtual] = useState<IdLeitura>("obrigado");
  const { definirHumor } = useCena();
  const base = useId();
  const leitura = conjunto.leituras.find((l) => l.id === atual) as Leitura;

  useEffect(() => {
    const { humor, cinza } = humorDaCategoria(leitura.categoria);
    definirHumor(humor, cinza);
  }, [leitura, definirHumor]);

  const marcas = marcasDaAtribuicao(leitura.mensagens);
  const decisivas = falasDecisivas(marcas);

  return (
    <div className="ln-seletor">
      <div role="tablist" aria-label="Leituras gravadas" className="ln-abas">
        {conjunto.leituras.map((l) => (
          <button
            key={l.id}
            role="tab"
            id={`${base}-aba-${l.id}`}
            aria-selected={l.id === atual}
            aria-controls={`${base}-painel`}
            tabIndex={l.id === atual ? 0 : -1}
            className="ln-aba"
            onClick={() => setAtual(l.id)}
            onKeyDown={(e) => {
              const i = conjunto.leituras.findIndex((x) => x.id === atual);
              const passo = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
              if (!passo) return;
              const proxima = conjunto.leituras[(i + passo + conjunto.leituras.length) % conjunto.leituras.length];
              setAtual(proxima.id);
              document.getElementById(`${base}-aba-${proxima.id}`)?.focus();
            }}
          >
            {TITULOS[l.id].aba}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`${base}-painel`} aria-labelledby={`${base}-aba-${atual}`} className="ln-painel">
        <ol className="ln-conversa" aria-label="Transcrição">
          {leitura.conversa.mensagens.map((m, indice) => {
            const marca: MarcaAtribuicao | undefined = marcas.get(indice);
            return (
              <li key={indice} className={`ln-msg ln-msg--${m.autor}`} data-sentido={marca?.sentido}>
                <span className="ln-rotulo">{m.autor}</span>
                <p className="ln-msg__texto">{m.texto}</p>
                {marca && marca.sentido !== "sem_inclinacao" && (
                  <span className="ln-msg__marca">
                    {ROTULO_SENTIDO[marca.sentido]} · {porcentagem(marca.probInsatisfeito)} insatisfeito
                  </span>
                )}
              </li>
            );
          })}
        </ol>

        <aside className="ln-veredito" aria-label="O que o Fraus mediu">
          {/* O ROTEIRO e o que nos escrevemos; o veredito embaixo e o que o motor leu. */}
          <div>
            <span className="ln-rotulo">roteiro da conversa</span>
            <p className="titulo-vitrine ln-veredito__tese">{TITULOS[atual].tese}</p>
          </div>
          <div className="ln-veredito__nota">
            <SegmentoLED valor={leitura.nota === null ? null : String(leitura.nota)} rotulo="nota estimada" altura={64} cor="medido" traco="fino" celulas={2} />
            <span className="ln-rotulo">
              {leitura.categoria ? (
                <>
                  nota estimada · <strong>{leitura.categoria}</strong>
                </>
              ) : (
                <>sem sinal · sem fala do cliente, sem nota</>
              )}
            </span>
          </div>
          {!concordaComRoteiro(leitura) && (
            <p className="ln-veredito__discorda" role="note">
              O Fraus leu diferente do roteiro. A leitura fica como o motor disse: esconder o erro seria escolher a
              conversa a dedo.
            </p>
          )}
          {decisivas.length > 0 && (
            <p className="ln-veredito__decisiva">
              {decisivas.length === 1 ? "Uma fala decidiu." : `${decisivas.length} falas inclinaram a nota.`} A mais forte:{" "}
              <q>{leitura.conversa.mensagens[decisivas[0].indice]?.texto}</q>
            </p>
          )}
        </aside>
      </div>

      <p className="ln-procedencia">
        Leitura gravada pelo motor de produção em {dataDaGravacao(conjunto.procedencia.gravado_em)} · modelo{" "}
        {conjunto.procedencia.modelo} · conversas sintéticas, escritas para esta página · nota é estimativa, não NPS
        declarado.
      </p>
    </div>
  );
}
