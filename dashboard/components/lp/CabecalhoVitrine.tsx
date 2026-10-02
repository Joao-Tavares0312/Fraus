import Link from "next/link";
import { MarcaFraus } from "@/components/shell/MarcaFraus";
import { FATOS_DO_MODELO, emDuasCasas } from "./fatos";

/**
 * O TOPO DA VITRINE: marca, telemetria e "Acessar", numa faixa so.
 *
 * A telemetria so diz FATOS do produto (zero LLM, NPS estimativa) e quanto da
 * leitura ja foi rolado -- o motor escreve o percentual em `data-vt="leitura"`
 * e a barra dourada em `data-vt="progresso"`. Dourado e telemetria e acao,
 * nunca dado. No celular sobram a marca, o LLM 00 e o acesso.
 */
export function CabecalhoVitrine() {
  return (
    <header className="vt-topo">
      <nav aria-label="Navegação principal" className="vt-wrap vt-topo__faixa">
        <Link href="/" aria-label="Fraus — início" className="vt-marca">
          <MarcaFraus tamanho={22} />
          <span>Fraus</span>
        </Link>
        <div className="vt-telemetria" aria-label="Telemetria">
          <span>
            LLM <em>{emDuasCasas(FATOS_DO_MODELO.llms)}</em>
          </span>
          <span className="vt-opcional">
            NPS <em>estimativa</em>
          </span>
          <span className="vt-opcional">
            leitura <em data-vt="leitura">000%</em>
          </span>
        </div>
        <Link href="/entrar" className="vt-acessar">
          Acessar
        </Link>
      </nav>
      <div aria-hidden className="vt-progresso" data-vt="progresso" />
    </header>
  );
}
