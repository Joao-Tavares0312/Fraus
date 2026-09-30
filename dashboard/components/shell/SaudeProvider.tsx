"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { obterSaude } from "@/lib/api";
import {
  classificarSaude,
  intervaloDeSaudeMs,
  suavizarSaude,
  type EstadoDeSaude,
} from "@/lib/estado-saude";

/**
 * `duble` é um estado à parte, e não um "no-ar" com etiqueta: a API respondeu,
 * mas o que ela serve é sintético. Juntar os dois num só obrigaria cada
 * consumidor a lembrar de checar o motor, e a lição de 04/09/2026 é que esse
 * tipo de lembrete não sobrevive — foi assim que a tela anunciou "API no ar"
 * por um dia inteiro sobre números inventados.
 */
export type { EstadoDeSaude } from "@/lib/estado-saude";

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
  // Espelho do estado para quem roda fora do render (o laco de consulta e o
  // `reconsultar`): ler `estado` de dentro de um closure velho reintroduziria a
  // oscilacao que `suavizarSaude` existe para impedir.
  const estadoRef = useRef<EstadoDeSaude>("verificando");
  const aplicar = useCallback((resultado: Parameters<typeof classificarSaude>[0]) => {
    const proximo = suavizarSaude(estadoRef.current, classificarSaude(resultado));
    estadoRef.current = proximo;
    setEstado(proximo);
    return proximo;
  }, []);

  const reconsultar = useCallback(async () => {
    const resultado = await obterSaude();
    aplicar(resultado);
    return resultado.ok;
  }, [aplicar]);

  useEffect(() => {
    let vivo = true;
    let relogio: ReturnType<typeof setTimeout>;

    // setTimeout encadeado, e nao setInterval: o intervalo depende do estado
    // (rapido enquanto aquece, devagar quando pronto).
    const verificar = async () => {
      const resultado = await obterSaude();
      if (!vivo) return;
      const proximo = aplicar(resultado);
      relogio = setTimeout(verificar, intervaloDeSaudeMs(proximo));
    };

    verificar();
    return () => {
      vivo = false;
      clearTimeout(relogio);
    };
  }, [aplicar]);

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
