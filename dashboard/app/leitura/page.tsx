import { CenaLeitura } from "@/components/lp-nova/CenaLeitura";

// Harness da Task 6: so a cena e uma pagina alta para rolar. A Task 7 troca
// pelas sete secoes.
export default function PaginaLeitura() {
  return (
    <CenaLeitura>
      <style>{`.ln-cena{position:fixed;inset:0;width:100vw;height:100vh;display:block;z-index:0}
      .ln-regime{position:fixed;right:16px;bottom:12px;font:12px monospace;color:#aaa;z-index:2}
      .ln-frase{position:relative;z-index:1;font:600 64px sans-serif;color:transparent;margin:40vh 0 0 8vw;display:inline-block}`}</style>
      <span data-ln="frase" className="ln-frase">ok, obrigado 🙂</span>
      <div style={{ height: "700vh" }} />
    </CenaLeitura>
  );
}
