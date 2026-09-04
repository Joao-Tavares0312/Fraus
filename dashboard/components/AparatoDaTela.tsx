"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Aparato } from "./Aparato";

/**
 * O APARATO DA TELA -- um, no pe, e nao um por painel.
 *
 * O QUE MUDOU E POR QUE. A §4.1 do DESIGN.md tirou a prosa metodologica de
 * cima do dado e a mandou para o rodape do sistema, e isso funcionou. O que
 * ela nao resolveu: com seis paineis por tela, "Método e ressalvas" passou a
 * aparecer seis vezes, identico, e repeticao le como ruido em vez de rigor.
 *
 * O QUE NAO MUDA: nenhum texto de honestidade sai da tela -- recolher e
 * permitido, remover nao. E os rotulos curtos (`estimativa`, `observado`,
 * `sem sinal`) NAO sao aparato: continuam colados ao numero, sempre visiveis,
 * como a propria §4.1 diz.
 *
 * POR QUE CONTEXTO, e nao a tela juntando a prosa na mao: a ressalva pertence
 * ao painel que a produz. Se a tela a digitasse, ela envelheceria separada do
 * painel -- o mesmo defeito que o `Aparato` foi extraido para resolver.
 */

type Ressalva = { titulo: string; conteudo: ReactNode };

const Contexto = createContext<{
  registrar: (r: Ressalva) => void;
  remover: (titulo: string) => void;
} | null>(null);

/**
 * A lista viaja num contexto SEPARADO do de escrita: quem so registra
 * (`Painel`) nao precisa re-renderizar quando a lista muda, e quem so le
 * (`AparatoDaTela`) nao precisa das funcoes. Um contexto unico faria cada
 * painel da tela re-renderizar a cada inscricao dos vizinhos.
 */
const ListaContexto = createContext<Ressalva[]>([]);

export function ProvedorDeAparato({ children }: { children: ReactNode }) {
  const [ressalvas, setRessalvas] = useState<Ressalva[]>([]);

  const registrar = useCallback((nova: Ressalva) => {
    setRessalvas((atuais) => {
      const semAAntiga = atuais.filter((r) => r.titulo !== nova.titulo);
      return [...semAAntiga, nova];
    });
  }, []);

  const remover = useCallback((titulo: string) => {
    setRessalvas((atuais) => atuais.filter((r) => r.titulo !== titulo));
  }, []);

  const valor = useMemo(() => ({ registrar, remover }), [registrar, remover]);

  return (
    <Contexto.Provider value={valor}>
      <ListaContexto.Provider value={ressalvas}>
        {children}
      </ListaContexto.Provider>
    </Contexto.Provider>
  );
}

/**
 * Chamado pelo painel que PRODUZ a ressalva. Fora do provedor vira no-op de
 * proposito: um painel usado solto nao deve quebrar a pagina.
 */
export function useRegistrarRessalva(titulo: string, conteudo: ReactNode) {
  const ctx = useContext(Contexto);
  const temConteudo = Boolean(conteudo);

  useEffect(() => {
    if (!ctx || !temConteudo) return;
    ctx.registrar({ titulo, conteudo });
    return () => ctx.remover(titulo);
    // `conteudo` fica FORA das dependencias: ele e JSX, recriado a cada render,
    // e incluir isso reinscreveria a ressalva em laco infinito. O titulo e a
    // identidade da entrada.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ctx, titulo, temConteudo]);
}

export function AparatoDaTela({ className }: { className?: string }) {
  const ressalvas = useContext(ListaContexto);
  if (ressalvas.length === 0) return null;

  return (
    <Aparato className={className}>
      <div className="mt-2 flex max-w-[72ch] flex-col gap-4 text-xs leading-relaxed text-muted-foreground">
        {ressalvas.map((r) => (
          <section key={r.titulo}>
            <h3 className="mb-1 font-semibold text-foreground">{r.titulo}</h3>
            {r.conteudo}
          </section>
        ))}
      </div>
    </Aparato>
  );
}
