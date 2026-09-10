"""Deriva de distribuicao: a invariante 10 como alarme de runtime.

A invariante 10 diz que o corpus de treino nao pode entregar o rotulo, e o
criterio de `docs/treinamento.md` e explicito: "se as features que lideram
forem as circunstanciais (tempo, contagem de turnos), procure o vazamento".
Essa guarda roda no NOTEBOOK, sobre o corpus.

O que ela nao alcanca: o corpus do sinal de tempo nunca passou de minutos
(medianas de 5/30/200 s no simulador), e em producao aparece conversa com tres
horas de espera. Medido em 08/09/2026 contra a API real, uma conversa assim
recebe `latencia_primeira_resposta_s -85,4` contra `texto_prob_satisfeito_media
+4,6` -- o tempo pesa 20x o texto e o score sai em 4,4e-24. O peso POR UNIDADE
continua pequeno (0,12-0,16); o que explode e o z-score que entra no scaler.

Este modulo nao corrige nada disso. O conserto de verdade -- `log1p` ou
winsorizacao antes do scaler -- exige RETREINO, e retreino esta fora de
escopo. O que ele faz e tornar o caso VISIVEL: dizer quais features da amostra
recente estao fora da faixa em que o modelo aprendeu, com o nome de cada uma.

Por que da para fazer sem retreinar: o `StandardScaler` treinado ja carrega
`mean_` e `scale_` por feature dentro de `modelos/fusor.joblib`. Ler nao e
treinar.

A parte PURA mora aqui, separada da rota, porque ela nao precisa de BERTimbau
nenhum -- e o que permite a regra falhar em milissegundos de pytest.
"""

# |z| acima disto marca a feature como fora da faixa de treino.
#
# De onde vem o 4: sob distribuicao aproximadamente normal, |z| > 4 e um evento
# de ~1 em 16 mil, entao ele nao dispara por cauda comum -- ele dispara quando
# o valor observado nao pertence a distribuicao do treino. E deliberadamente
# FROUXO: o caso que motivou a rota tem z na casa das centenas, e um limiar
# apertado transformaria o alarme em ruido diario, que e o mesmo que nao ter
# alarme. Se um dia ele parar de disparar para um caso real, o numero e que
# esta errado, e mover um limiar declarado e uma decisao; herdar um numero sem
# procedencia nao e.
LIMIAR_Z = 4.0


def resumo_de_deriva(
    zs_por_conversa: list[dict[str, float]],
    distribuicao: dict[str, dict[str, float]],
    limiar: float = LIMIAR_Z,
) -> dict | None:
    """Quais features da amostra recente sairam da faixa de treino, e quanto.

    `zs_por_conversa` e uma lista de `{feature: z}` -- o valor JA padronizado
    pelo scaler do fusor, que e literalmente o numero que multiplica o
    coeficiente na predicao.

    O z reportado por feature e o **pior modulo da amostra**, nunca a media:
    uma conversa fora da faixa entre cem dentro ainda e o caso a investigar, e
    a media a diluiria ate virar ruido de arredondamento -- apagando
    exatamente o evento que esta rota existe para achar.

    Amostra vazia devolve `z_absoluto_observado: None` e
    `dentro_da_faixa: None`, nunca `0.0`/`True`: zero ali se leria como
    "exatamente na media do treino", que e a afirmacao mais tranquilizadora
    possivel a respeito de uma amostra que nao existe.

    `None` quando o fusor nao tem retrato de treino (nao treinado): ausencia
    de diagnostico, diferente de um relatorio vazio com cara de saudavel.

    NAO ALTERA PREDICAO NENHUMA. E diagnostico.
    """
    if not distribuicao:
        return None

    features = []
    fora = []
    for nome, retrato in distribuicao.items():
        observados = [
            abs(z[nome]) for z in zs_por_conversa if nome in z
        ]
        pior = max(observados) if observados else None
        dentro = None if pior is None else pior <= limiar
        if dentro is False:
            fora.append(nome)
        features.append(
            {
                "nome": nome,
                "media_treino": retrato["media"],
                "desvio_treino": retrato["desvio"],
                "z_absoluto_observado": pior,
                "dentro_da_faixa": dentro,
            }
        )

    # Pior primeiro: quem abre a rota quer o caso a investigar, nao a ordem
    # alfabetica das 39. As sem observacao vao para o fim, porque "nao medi"
    # nao compete por atencao com "medi e esta fora".
    features.sort(key=lambda f: (f["z_absoluto_observado"] is None,
                                 -(f["z_absoluto_observado"] or 0.0)))

    return {
        "limiar_z": limiar,
        "conversas_na_amostra": len(zs_por_conversa),
        "features": features,
        "fora_da_faixa": fora,
    }
