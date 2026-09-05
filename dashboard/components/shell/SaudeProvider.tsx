"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { obterSaude } from "@/lib/api";

/**
 * `duble` é um estado à parte, e não um "no-ar" com etiqueta: a API respondeu,
 * mas o que ela serve é sintético. Juntar os dois num só obrigaria cada
 * consumidor a lembrar de checar o motor, e a lição de 04/09/2026 é que esse
 * tipo de lembrete não sobrevive — foi assim que a tela anunciou "API no ar"
 * por um dia inteiro sobre números inventados.
 */
export type EstadoDeSaude = "verificando" | "no-ar" | "duble" | "fora-do-ar";

const INTERVALO_MS = 20_000;

type Contexto = {
  estado: EstadoDeSaude;
  /** Consulta agora, fora do intervalo. Devolve se a API respondeu. */
  reconsultar: () => Promise<boolean>;
};

const SaudeContexto = createContext<Contexto | null>(null);

/**
 * A saude da API, consultada UMA vez para a interface inteira.
 *
 * O indicador da barra lateral e o aviso de "API fora do ar" mostram o mesmo
 * fato. Com um polling em cada um, os dois discordariam por ate 20 segundos --
 * o rodape dizendo "API no ar" com o aviso de fora do ar ainda na tela. Uma
 * consulta, dois consumidores.
 *
 * `reconsultar` existe para os dois gestos que nao podem esperar o intervalo:
 * o botao "tentar de novo" e o fim da subida da API.
 */
export function SaudeProvider({ children }: { children: React.ReactNode }) {
  const [estado, setEstado] = useState<EstadoDeSaude>("verificando");

  // `no-ar` exige o motor DECLARADO como real. Campo ausente (API antiga) ou
  // qualquer outro valor cai em `duble`: errar para este lado custa uma
  // etiqueta a mais na tela, errar para o outro apresenta invenção como
  // medição. É a mesma precedência que a rota `/saude` aplica no servidor.
  const classificar = (resultado: Awaited<ReturnType<typeof obterSaude>>) => {
    if (!resultado.ok) return "fora-do-ar" as const;
    return resultado.dado?.motor === "real" ? ("no-ar" as const) : ("duble" as const);
  };

  const reconsultar = useCallback(async () => {
    const resultado = await obterSaude();
    setEstado(classificar(resultado));
    return resultado.ok;
  }, []);

  useEffect(() => {
    let vivo = true;

    const verificar = async () => {
      const resultado = await obterSaude();
      if (!vivo) return;
      setEstado(classificar(resultado));
    };

    verificar();
    const relogio = setInterval(verificar, INTERVALO_MS);
    return () => {
      vivo = false;
      clearInterval(relogio);
    };
  }, []);

  return (
    <SaudeContexto.Provider value={{ estado, reconsultar }}>
      {children}
    </SaudeContexto.Provider>
  );
}

/**
 * A saude compartilhada. Fora do provider devolve "verificando" e um
 * `reconsultar` que não faz nada -- um componente isolado num teste não deve
 * quebrar por falta de casca.
 */
export function useSaude(): Contexto {
  return (
    useContext(SaudeContexto) ?? {
      estado: "verificando",
      reconsultar: async () => false,
    }
  );
}
