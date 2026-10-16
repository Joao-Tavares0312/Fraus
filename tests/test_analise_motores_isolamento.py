"""Fronteiras dos instrumentos locais, sem importar o runtime."""
import json
from pathlib import Path

import pytest

from scripts.analise_motores import comum


def test_workspace_interno_e_symlink_recusados(tmp_path):
    with pytest.raises(ValueError):
        comum.preparar_workspace(comum.RAIZ / 'experimento-proibido')
    link = tmp_path / 'atalho'
    link.symlink_to(comum.RAIZ, target_is_directory=True)
    with pytest.raises(ValueError):
        comum.preparar_workspace(link / 'experimento-proibido')
    externo = comum.preparar_workspace(tmp_path / 'seguro')
    assert (externo / '.gitignore').read_text() == '*\n'


def test_ambiente_nao_herda_segredos(tmp_path, monkeypatch):
    monkeypatch.setenv('FRAUS_CHAVE_ACESSO', 'SEGREDO-NAO-VAZAR')
    monkeypatch.setenv('HTTPS_PROXY', 'https://nao-usar.invalid')
    ambiente = comum.ambiente_isolado(comum.preparar_workspace(tmp_path / 'lab'))
    assert not any(k.startswith('FRAUS_') or 'PROXY' in k for k in ambiente)
    assert 'SEGREDO-NAO-VAZAR' not in json.dumps(ambiente)
    assert ambiente['HF_HUB_OFFLINE'] == '1'
    assert Path(ambiente['HOME']).is_relative_to(tmp_path)


def test_json_estrito_e_ausencia_explicita(tmp_path):
    ws = comum.preparar_workspace(tmp_path / 'lab')
    registro = comum.resultado('prova', 'nao_verificado', 'modelo ausente', medicoes={'score': None})
    caminho = comum.salvar_resultado(ws, registro)
    assert json.loads(caminho.read_text())['medicoes']['score'] is None
    registro['medicoes']['score'] = float('nan')
    with pytest.raises(ValueError):
        comum.salvar_resultado(ws, registro)


def test_http_recusa_host_remoto_e_redirects():
    for url in ('https://example.com', 'http://localhost:8000', 'http://127.0.0.1.evil:3', 'http://user:pw@127.0.0.1:8'):
        with pytest.raises(ValueError):
            comum.cliente_loopback(url)
    with comum.cliente_loopback('http://127.0.0.1:12345') as cliente:
        assert cliente.follow_redirects is False
        assert cliente.trust_env is False


def test_copia_nao_altera_original(tmp_path):
    origem = tmp_path / 'origem'
    origem.mkdir()
    arquivo = origem / 'modelo'
    arquivo.write_bytes(b'original')
    comum.copiar_arvore(origem, tmp_path / 'copia')
    (tmp_path / 'copia' / 'modelo').write_bytes(b'mudou')
    assert arquivo.read_bytes() == b'original'
    (origem / 'link').symlink_to(arquivo)
    with pytest.raises(ValueError):
        comum.copiar_arvore(origem, tmp_path / 'outra')
