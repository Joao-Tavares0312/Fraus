import { Letras, Palavras } from "../Palavras";

export function Problema() {
  return (
    <section id="como-funciona" className="cena r" aria-labelledby="titulo-contexto">
      <div className="blk">
        <h2 id="titulo-contexto"><Palavras texto="Uma frase não conta a conversa inteira." /></h2>
        <p className="rv">Uma despedida cordial não diz, sozinha, se o problema foi resolvido. O contexto precisa entrar na leitura.</p>
        <span className="tag chanfro d rv" data-embaralhar>Exemplo de linguagem · dito</span>
        <blockquote className="quote"><Letras texto="“Ok, obrigado.”" /></blockquote>
        <ul className="ck">
          <li className="chanfro fio rv"><b>O pedido</b>O que o cliente precisava resolver.</li>
          <li className="chanfro fio rv"><b>A resposta</b>Como o chatbot tratou a solicitação.</li>
          <li className="chanfro fio rv"><b>O desfecho</b>Como o atendimento terminou.</li>
        </ul>
      </div>
    </section>
  );
}
