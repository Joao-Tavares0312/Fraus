"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { obterSaude } from "@/lib/api";

export type EstadoDeSaude = "verificando" | "no-ar" | "fora-do-ar";

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

  const reconsultar = useCallback(async () => {
    const resultado = await obterSaude();
    setEstado(resultado.ok ? "no-ar" : "fora-do-ar");
    return resultado.ok;
  }, []);

  useEffect(() => {
    let vivo = true;

    const verificar = async () => {
      const resultado = await obterSaude();
      if (!vivo) return;
      setEstado(resultado.ok ? "no-ar" : "fora-do-ar");
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
