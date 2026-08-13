"""Configuracao vigente do Fraus: padrao de fabrica no codigo, delta no banco.

Duas decisoes que governam este modulo:

1. **O valor de fabrica mora aqui, nao no banco.** A tabela `configuracoes`
   guarda somente o que alguem mudou de fato. Banco vazio -- ou banco antigo,
   anterior a esta tabela -- se comporta exatamente como antes.
2. **So entra o que muda o comportamento na leitura.** Nao ha interruptor por
   sinal (texto/emoji/tempo): os tres estao fundidos nos coeficientes de um
   modelo ja treinado, desligar um exigiria retreinar, e um controle que nao
   faz o que diz e pior que a ausencia dele.

Sobre a faixa de NPS: ela continua tendo UMA fonte. O padrao vive em
`fraus.indicadores.FAIXAS_NPS`; a faixa vigente sai daqui e e passada por
PARAMETRO para `categoria_nps`/`calcular_nps`. Nao existe estado global mutavel.

CONSEQUENCIA ASSUMIDA -- mudar a faixa muda a categoria de atendimento JA
pontuado. A decisao deste projeto e: **categoria e DERIVADA NA LEITURA**, a
partir do `score` gravado e da faixa vigente. Nao ha recalculo em massa na
escrita da configuracao, porque recalcular deixaria uma janela em que
`/indicadores` (que agrega scores) e `/conversas` (que leria a coluna
`categoria`) discordariam se a escrita falhasse no meio. Derivando na leitura,
as duas rotas respondem sempre pela mesma faixa, no mesmo instante. O `score`
-- esse sim resultado do modelo -- nunca e recalculado: so a fatia muda.
"""

from fraus.db import Banco
from fraus.indicadores import Categoria, FAIXAS_NPS, validar_faixas_nps

# Limiares (em segundos) da faixa de referencia de latencia exibida na
# interface. Sao de EXIBICAO: mudam onde a leitura corta "rapido/aceitavel/
# lento", nao mudam nenhuma feature do modelo -- `fraus.sinais.tempo` continua
# lendo os timestamps crus, e latencia segue nao sendo persistida.
LIMIARES_LATENCIA_PADRAO = [10, 60, 180]

PADROES: dict = {
    "faixas_nps": {categoria: list(faixa) for categoria, faixa in FAIXAS_NPS.items()},
    "limiares_latencia_s": list(LIMIARES_LATENCIA_PADRAO),
}


def validar_configuracao(valores: dict) -> None:
    """Recusa configuracao invalida nomeando o problema. Levanta ValueError.

    Valida so as chaves presentes: `PUT /configuracoes` pode mandar uma so.
    """
    desconhecidas = [chave for chave in valores if chave not in PADROES]
    if desconhecidas:
        raise ValueError(
            f"chave de configuracao desconhecida: {', '.join(sorted(desconhecidas))}"
        )

    if "faixas_nps" in valores:
        faixas = valores["faixas_nps"]
        if not isinstance(faixas, dict):
            raise ValueError("faixas_nps precisa ser um objeto categoria -> [minima, maxima]")
        normalizadas = {}
        for categoria, faixa in faixas.items():
            if not isinstance(faixa, (list, tuple)) or len(faixa) != 2:
                raise ValueError(f"faixa de {categoria} precisa ser [minima, maxima]")
            if not all(isinstance(v, int) and not isinstance(v, bool) for v in faixa):
                raise ValueError(f"faixa de {categoria} precisa ser de numeros inteiros")
            normalizadas[categoria] = (faixa[0], faixa[1])
        validar_faixas_nps(normalizadas)

    if "limiares_latencia_s" in valores:
        limiares = valores["limiares_latencia_s"]
        if not isinstance(limiares, (list, tuple)) or len(limiares) != 3:
            raise ValueError("limiares_latencia_s precisa ter exatamente tres valores")
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in limiares):
            raise ValueError("limiares_latencia_s precisa ser de numeros inteiros")
        if any(v <= 0 for v in limiares):
            raise ValueError("cada limiar de latencia precisa ser positivo, em segundos")
        if not (limiares[0] < limiares[1] < limiares[2]):
            raise ValueError(
                f"limiares de latencia precisam ser crescentes: {limiares}"
            )


def carregar(banco: Banco) -> dict:
    """Padrao de fabrica sobrescrito pelo que estiver gravado."""
    vigente = {chave: _copiar(valor) for chave, valor in PADROES.items()}
    for chave, valor in banco.ler_configuracoes().items():
        if chave in PADROES:  # chave orfa de versao antiga nao derruba a leitura
            vigente[chave] = valor
    return vigente


def salvar(banco: Banco, valores: dict) -> dict:
    """Valida ANTES de tocar no banco e devolve a configuracao vigente resultante."""
    validar_configuracao(valores)
    if valores:
        banco.escrever_configuracoes(valores)
    return carregar(banco)


def faixas_de(configuracao: dict) -> dict[Categoria, tuple[int, int]]:
    """Faixas no formato que `categoria_nps` espera (tupla, nao lista do JSON)."""
    return {
        categoria: (faixa[0], faixa[1])
        for categoria, faixa in configuracao["faixas_nps"].items()
    }


def _copiar(valor):
    if isinstance(valor, dict):
        return {chave: _copiar(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_copiar(item) for item in valor]
    return valor
