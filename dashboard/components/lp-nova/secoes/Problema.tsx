import { ChevronDown, MessagesSquare, Search } from "lucide-react";
import { ArteCompacta } from "../ArteCompacta";

export function Problema() {
  return (
    <section className="cena" data-cena="1" id="como-funciona" aria-labelledby="titulo-contexto">
      <div className="texto-cena">
        <h2 id="titulo-contexto">Uma frase não conta a conversa inteira.</h2>
        <p>Uma despedida cordial não diz, sozinha, se o problema foi resolvido. O contexto precisa entrar na leitura.</p>
        <div className="lp-widget contexto-widget">
          <div className="widget-cabecalho">
            <span className="widget-voz voz-dito"><MessagesSquare className="icone-lp" aria-hidden="true" />O que foi dito</span>
            <span className="rotulo-exemplo">Exemplo de linguagem</span>
          </div>
          <blockquote className="frase-ilustrativa"><p>“Ok, obrigado.”</p></blockquote>
          <details className="contexto-detalhes" open>
            <summary><Search className="icone-lp" aria-hidden="true" /><span>O que conferir na conversa</span><ChevronDown className="icone-lp chevron-lp" aria-hidden="true" /></summary>
            <ul className="perguntas-contexto">
              <li><strong>O pedido</strong><span>O que o cliente precisava resolver.</span></li>
              <li><strong>A resposta</strong><span>Como o chatbot tratou a solicitação.</span></li>
              <li><strong>O desfecho</strong><span>Como o atendimento terminou.</span></li>
            </ul>
          </details>
        </div>
      </div>
      <ArteCompacta etapa={1} />
    </section>
  );
}
