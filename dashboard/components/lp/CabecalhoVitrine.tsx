import Link from "next/link";
import { ArrowRight } from "lucide-react";
import {
  TelemetriaTopo,
  TelemetriaValor,
} from "@/components/instrumento/TelemetriaTopo";
import { MarcaFraus } from "@/components/shell/MarcaFraus";
import { FATOS_DO_MODELO, emDuasCasas } from "./fatos";

/**
 * O TOPO DA VITRINE: a faixa de telemetria (a assinatura da Regua) e, por
 * baixo dela, a pilula de vidro (a assinatura da Aurora).
 *
 * A telemetria so diz FATOS do produto -- sete familias, 39 features, zero
 * LLM, NPS estimativa --, os mesmos do CLAUDE.md. Nada de metrica de uso.
 *
 * A pilula e o unico vidro da pagina, e ela merece: fica FIXA sobre um hero
 * que tem um orbe brilhando atras, entao ha o que borrar. No celular ela perde
 * os links de secao e fica com a marca e o "Acessar".
 */
export function CabecalhoVitrine() {
  return (
    <header className="vt-topo">
      <TelemetriaTopo
        esquerda={
          <>
            <span className="sm:hidden">
              FRAUS · LLM <TelemetriaValor>00</TelemetriaValor>
            </span>
            <span className="hidden sm:inline">
              FRAUS / OBSERVATÓRIO DE CONVERSAS
            </span>
          </>
        }
        direita={
          <>
            SINAIS{" "}
            <TelemetriaValor>{emDuasCasas(FATOS_DO_MODELO.familias)}</TelemetriaValor> ·
            FEATURES <TelemetriaValor>{FATOS_DO_MODELO.features}</TelemetriaValor> ·
            LLM <TelemetriaValor>{emDuasCasas(FATOS_DO_MODELO.llms)}</TelemetriaValor> ·
            NPS{" "}
            <TelemetriaValor>ESTIMATIVA</TelemetriaValor>
          </>
        }
      />
      <nav aria-label="Navegação principal" className="vt-nav">
        <Link
          href="/"
          aria-label="Fraus — início"
          className="vt-nav__marca"
        >
          <MarcaFraus tamanho={24} />
          <span>FRAUS</span>
        </Link>
        <a href="#leitura" className="vt-nav__elo">
          Leitura
        </a>
        <a href="#sistema" className="vt-nav__elo">
          Sistema
        </a>
        <a href="#metodo" className="vt-nav__elo">
          Método
        </a>
        <Link href="/cadastrar" className="vt-nav__elo hidden lg:inline">
          Cadastro
        </Link>
        <Link href="/entrar" className="vt-nav__acessar">
          Acessar <ArrowRight aria-hidden className="size-3.5" />
        </Link>
      </nav>
    </header>
  );
}
