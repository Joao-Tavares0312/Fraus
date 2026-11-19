"""Hook oficial do mkdocs-to-pdf: Mermaid em SVG antes do WeasyPrint.

Material encapsula diagramas no navegador; dump-dom nao preserva esse conteudo.
No PDF, usamos a mesma biblioteca Mermaid, com rotulos SVG (sem foreignObject),
fora do seletor do Material. Falha de renderizacao bloqueia o PDF, nao o site.
"""
import base64
import hashlib
from pathlib import Path
from urllib.request import urlopen


def pre_js_render(soup, logger):
    diagramas = soup.select('.mermaid')
    if not diagramas:
        return soup
    for diagrama in diagramas:
        diagrama['class'] = ['fraus-pdf-mermaid']
        # O plugin conserva <code> dentro de <pre>; Mermaid.run le innerHTML.
        # Remova apenas o invólucro, preservando a fonte textual do diagrama.
        fonte = diagrama.get_text()
        diagrama.clear()
        diagrama.string = fonte
    cache = Path.home() / '.cache' / 'fraus' / 'mermaid-11.17.2.min.js'
    codigo = cache.read_bytes() if cache.is_file() else urlopen(
        'https://unpkg.com/mermaid@11.17.2/dist/mermaid.min.js', timeout=30
    ).read()
    if hashlib.sha256(codigo).hexdigest() != '581ed7d74bd9048d0e3a91363927d72ef22942d7722546b27f7cc29e35390eb8':
        raise RuntimeError('Biblioteca Mermaid do PDF divergente do hash fixado')
    if not cache.is_file():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(codigo)
    # Evita depender da rede/TLS do subprocesso Chromium e do seu relogio virtual.
    biblioteca = soup.new_tag('script', src='data:text/javascript;base64,' + base64.b64encode(codigo).decode())
    soup.body.append(biblioteca)
    executar = soup.new_tag('script')
    executar.string = """
mermaid.initialize({startOnLoad: false, securityLevel: 'strict', theme: 'neutral',
  htmlLabels: false, fontFamily: 'sans-serif', flowchart: {htmlLabels: false}});
mermaid.run({nodes: document.querySelectorAll('.fraus-pdf-mermaid')}).then(() => {
  for (const diagrama of document.querySelectorAll('.fraus-pdf-mermaid')) {
    const svg = diagrama.querySelector('svg');
    if (!svg || svg.querySelector('.error-icon')) throw new Error('SVG Mermaid ausente ou invalido');
    // Preserve viewBox e nomes XML: o parser HTML do plugin os converte para minusculas.
    const xml = new XMLSerializer().serializeToString(svg);
    const imagem = document.createElement('img');
    imagem.src = 'data:image/svg+xml;base64,' + btoa(String.fromCharCode(...new TextEncoder().encode(xml)));
    imagem.alt = 'Diagrama de processamento; equivalente textual na secao adjacente.';
    imagem.style.cssText = 'display:block; width:100%; height:auto; max-height:195mm; object-fit:contain;';
    diagrama.replaceChildren(imagem);
  }
}).catch(erro => {
  document.body.dataset.frausMermaidErro = erro.message || erro.str || JSON.stringify(erro);
});
"""
    soup.body.append(executar)
    logger.info('Renderizando %s diagramas Mermaid para o PDF.', len(diagramas))
    return soup


def pre_pdf_render(soup, logger):
    for diagrama in soup.select('.fraus-pdf-mermaid'):
        imagem = diagrama.find('img')
        if imagem is None or not imagem.get('src', '').startswith('data:image/svg+xml;base64,'):
            motivo = soup.body.get('data-fraus-mermaid-erro', diagrama.get_text()[:100])
            raise RuntimeError(f'Mermaid do PDF nao renderizado: {motivo}')
        diagrama.replace_with(imagem)
    return soup
