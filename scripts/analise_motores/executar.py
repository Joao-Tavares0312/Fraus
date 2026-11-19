"""Entrada única dos oito instrumentos; nenhum comando faz deploy ou treino."""
import importlib
import sys

COMANDOS = ('inventario', 'ouro', 'paridade', 'desempenho', 'qualidade', 'laya', 'candidatas', 'relatorio')


def main(argv: list[str] | None = None) -> int:
    argumentos = list(sys.argv[1:] if argv is None else argv)
    if not argumentos or argumentos[0] in ('-h', '--help'):
        print('Uso: python -m scripts.analise_motores.executar {' + ','.join(COMANDOS) + '} [opcoes]')
        return 0 if argumentos else 2
    nome = argumentos.pop(0)
    if nome not in COMANDOS:
        print('Subcomando desconhecido')
        return 2
    try:
        return importlib.import_module(f'scripts.analise_motores.{nome}').main(argumentos)
    except (ValueError, OSError) as erro:
        import errno
        import json
        from .comum import parser_base, preparar_workspace, resultado, salvar_resultado
        categoria = errno.errorcode.get(erro.errno, 'OSERROR') if isinstance(erro, OSError) else 'DESTINO_OU_CONFIGURACAO_RECUSADO'
        dados = resultado(nome, 'nao_verificado', categoria)
        try:
            opcoes, _ = parser_base('Isolamento').parse_known_args(argumentos)
            salvar_resultado(preparar_workspace(opcoes.workspace), dados)
        except (ValueError, OSError):
            print(json.dumps(dados, ensure_ascii=False, allow_nan=False))
        return 2
    except Exception as erro:
        print('Erro inesperado: ' + type(erro).__name__)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
