"""Registro de entrega de webhook: o antidoto para a falha silenciosa.

Sem esta tabela, um webhook recusado nao deixa rastro em lugar nenhum -- e
falha silenciosa e o modo de falha numero um dessa integracao.
"""

from datetime import datetime, timedelta, timezone

from fraus.db import VEREDITOS, Banco


def _banco(tmp_path) -> Banco:
    banco = Banco(tmp_path / "fraus.db")
    banco.migrar()
    return banco


def _fonte(banco: Banco) -> int:
    return banco.criar_fonte(
        nome="Zendesk", canal="webchat", tipo="webhook",
        variavel_segredo="FRAUS_WEBHOOK_ZEN", criada_em="2026-08-27T10:00:00+00:00",
    )["id"]


def test_entrega_aceita_e_registrada_com_a_conversa_que_gerou(tmp_path):
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    banco.registrar_entrega(
        fonte_id=fonte_id, webhook_id="msg_1", veredito="aceita",
        recebida_em="2026-08-27T10:01:00+00:00", conversa_id="atendimento-1",
    )
    (entrega,) = banco.listar_entregas(fonte_id)
    assert entrega["veredito"] == "aceita"
    assert entrega["conversa_id"] == "atendimento-1"
    assert entrega["motivo"] is None


def test_entrega_recusada_carrega_o_motivo_e_nao_tem_conversa(tmp_path):
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    banco.registrar_entrega(
        fonte_id=fonte_id, webhook_id="msg_1", veredito="assinatura",
        recebida_em="2026-08-27T10:01:00+00:00", motivo="assinatura nao confere",
    )
    (entrega,) = banco.listar_entregas(fonte_id)
    assert entrega["motivo"] == "assinatura nao confere"
    # None, nunca "" nem 0: nao houve conversa, e isso e diferente de uma
    # conversa de id vazio (invariante 2).
    assert entrega["conversa_id"] is None


def test_entregas_saem_mais_recente_primeiro(tmp_path):
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    for minuto in ("01", "03", "02"):
        banco.registrar_entrega(
            fonte_id=fonte_id, webhook_id=f"msg_{minuto}", veredito="aceita",
            recebida_em=f"2026-08-27T10:{minuto}:00+00:00",
        )
    assert [e["webhook_id"] for e in banco.listar_entregas(fonte_id)] == [
        "msg_03", "msg_02", "msg_01",
    ]


def test_entregas_de_uma_fonte_nao_vazam_para_outra(tmp_path):
    banco = _banco(tmp_path)
    uma, outra = _fonte(banco), _fonte(banco)
    banco.registrar_entrega(
        fonte_id=uma, webhook_id="msg_1", veredito="aceita",
        recebida_em="2026-08-27T10:01:00+00:00",
    )
    assert banco.listar_entregas(outra) == []


def test_webhook_id_ja_visto_e_reconhecido_por_fonte(tmp_path):
    """O dedupe e POR FONTE: duas plataformas podem numerar eventos igual, e
    tratar o `msg_1` de uma como reentrega da outra descartaria atendimento."""
    banco = _banco(tmp_path)
    uma, outra = _fonte(banco), _fonte(banco)
    banco.registrar_entrega(
        fonte_id=uma, webhook_id="msg_1", veredito="aceita",
        recebida_em="2026-08-27T10:01:00+00:00",
    )
    assert banco.entrega_ja_vista(uma, "msg_1") is True
    assert banco.entrega_ja_vista(outra, "msg_1") is False
    assert banco.entrega_ja_vista(uma, "msg_2") is False


def test_recusa_registrada_nao_conta_como_entrega_ja_vista(tmp_path):
    """So veredito "aceita" conta para o dedupe. Uma recusa (assinatura errada,
    variavel de ambiente ausente, fonte desativada, corpo invalido) registra a
    tentativa -- mas nao e uma entrega ja processada. Contar qualquer veredito
    abriria duas portas: um anonimo "queimando" um webhook-id alheio com
    assinatura lixo antes da entrega legitima chegar, e um operador que
    corrige o proprio ambiente vendo a retentativa cair como duplicada."""
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    for veredito in VEREDITOS:
        if veredito == "aceita":
            continue
        banco.registrar_entrega(
            fonte_id=fonte_id, webhook_id=f"msg_{veredito}", veredito=veredito,
            recebida_em="2026-08-27T10:00:00+00:00",
        )
        assert banco.entrega_ja_vista(fonte_id, f"msg_{veredito}") is False

    banco.registrar_entrega(
        fonte_id=fonte_id, webhook_id="msg_ok", veredito="aceita",
        recebida_em="2026-08-27T10:01:00+00:00",
    )
    assert banco.entrega_ja_vista(fonte_id, "msg_ok") is True


def test_poda_mantem_as_ultimas_e_descarta_as_mais_antigas(tmp_path):
    """Registrar recusa de assinatura e o que o operador precisa ver -- e e
    tambem como um atacante enche o SQLite. A poda e o que permite manter a
    primeira propriedade sem pagar a segunda."""
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    for numero in range(banco.ENTREGAS_POR_FONTE + 20):
        banco.registrar_entrega(
            fonte_id=fonte_id, webhook_id=f"msg_{numero:04d}", veredito="assinatura",
            recebida_em=f"2026-08-27T10:00:00+00:00",
        )
    entregas = banco.listar_entregas(fonte_id)
    assert len(entregas) == banco.ENTREGAS_POR_FONTE
    # As 20 primeiras cairam; a mais nova continua.
    assert entregas[0]["webhook_id"] == "msg_0219"
    assert banco.entrega_ja_vista(fonte_id, "msg_0000") is False


def test_poda_descarta_pelo_mesmo_criterio_que_a_listagem_usa(tmp_path):
    """A poda corta por `recebida_em DESC, id DESC` -- o MESMO criterio de
    `listar_entregas`. Sem isto, sob entrega fora de ordem (`recebida_em` nao
    acompanhando a ordem de insercao), a poda por `id` poderia manter uma
    entrega velha pelo relogio enquanto descarta uma nova pelo relogio que so
    chegou depois na ordem de insercao -- inconsistencia entre o que fica no
    banco e o que a tela mostra como "mais recente"."""
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    # A primeira entrega registrada carimba o horario MAIS NOVO de todas: se a
    # poda cortasse por `id`, ela sairia primeiro por ser a mais antiga na
    # ordem de insercao -- mas e a mais nova por `recebida_em`, entao tem que
    # sobreviver.
    banco.registrar_entrega(
        fonte_id=fonte_id, webhook_id="mais_nova_por_recebida_em",
        veredito="aceita", recebida_em="2026-08-27T23:59:59+00:00",
    )
    inicio = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)
    for numero in range(banco.ENTREGAS_POR_FONTE + 20):
        recebida_em = (inicio + timedelta(seconds=numero)).isoformat()
        banco.registrar_entrega(
            fonte_id=fonte_id, webhook_id=f"msg_{numero:04d}", veredito="assinatura",
            recebida_em=recebida_em,
        )
    webhook_ids = {e["webhook_id"] for e in banco.listar_entregas(fonte_id)}
    assert "mais_nova_por_recebida_em" in webhook_ids
    assert banco.entrega_ja_vista(fonte_id, "mais_nova_por_recebida_em") is True


def test_a_poda_nao_toca_nas_entregas_de_outra_fonte(tmp_path):
    banco = _banco(tmp_path)
    barulhenta, quieta = _fonte(banco), _fonte(banco)
    banco.registrar_entrega(
        fonte_id=quieta, webhook_id="importante", veredito="aceita",
        recebida_em="2026-08-27T09:00:00+00:00",
    )
    for numero in range(banco.ENTREGAS_POR_FONTE + 20):
        banco.registrar_entrega(
            fonte_id=barulhenta, webhook_id=f"msg_{numero}", veredito="assinatura",
            recebida_em="2026-08-27T10:00:00+00:00",
        )
    assert len(banco.listar_entregas(quieta)) == 1


def test_apagar_a_fonte_leva_as_entregas_dela(tmp_path):
    """Ao contrario das CONVERSAS, que sobrevivem: entrega e registro
    operacional DA fonte, nao dado de atendimento medido. Sem isto, as linhas
    ficariam orfas apontando para um id que ninguem mais consegue consultar."""
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    banco.registrar_entrega(
        fonte_id=fonte_id, webhook_id="msg_1", veredito="aceita",
        recebida_em="2026-08-27T10:01:00+00:00",
    )
    banco.apagar_fonte(fonte_id)
    assert banco.listar_entregas(fonte_id) == []


def test_os_vereditos_possiveis_estao_declarados_num_lugar_so(tmp_path):
    """A tela pinta cada veredito de um jeito e a rota escolhe um deles. Uma
    segunda lista digitada em outro arquivo so ficaria errada no dia em que um
    veredito novo entrasse -- sem erro nenhum, so sumindo da vista."""
    assert VEREDITOS == (
        "aceita", "assinatura", "fora_da_janela", "duplicada",
        "corpo_invalido", "fonte_inativa", "sem_segredo", "tipo_incompativel",
        "vazao", "erro",
    )


# --- a poda nao pode apagar o historico legitimo ----------------------------
#
# ATE 03/09/2026 A PODA NAO DISTINGUIA VEREDITO, e recusa anonima disputava as
# mesmas vagas que entrega aceita. A rota de webhook e ISENTA de chave de acesso
# por desenho (a plataforma externa nao tem como carregar uma `fra_`), entao
# qualquer um que descobrisse a URL mandava 210 requisicoes com assinatura lixo
# e zerava as aceitas da fonte. Reproduzido em 02/09/2026.
#
# E o dano nao era so o historico: esta tabela e TAMBEM a memoria do dedupe
# (`entrega_ja_vista`). Apagar as aceitas faz reentrega legitima voltar a ser
# processada como nova.
#
# A poda agora e por BALDE -- aceitas de um lado, o resto do outro -- e nao por
# veredito individual, para que a tabela siga com teto fixo por fonte mesmo que
# `VEREDITOS` cresca.


def _encher(banco, fonte_id, veredito, quantas, inicio=0):
    base = datetime(2026, 8, 27, 10, 0, tzinfo=timezone.utc)
    for n in range(inicio, inicio + quantas):
        banco.registrar_entrega(
            fonte_id=fonte_id, webhook_id=f"{veredito}_{n}", veredito=veredito,
            recebida_em=(base + timedelta(seconds=n)).isoformat(),
        )


def test_enxurrada_de_recusas_nao_apaga_as_aceitas(tmp_path):
    """O ataque em si. Este e o teste que impede a regressao."""
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    _encher(banco, fonte_id, "aceita", 5)

    _encher(banco, fonte_id, "assinatura", banco.ENTREGAS_POR_FONTE + 10, inicio=1000)

    entregas = banco.listar_entregas(fonte_id)
    assert sum(1 for e in entregas if e["veredito"] == "aceita") == 5


def test_a_enxurrada_nao_apaga_a_memoria_do_dedupe(tmp_path):
    """O dano menos visivel: sem as aceitas, uma reentrega legitima volta a ser
    processada como se fosse nova."""
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    banco.registrar_entrega(
        fonte_id=fonte_id, webhook_id="msg_importante", veredito="aceita",
        recebida_em="2026-08-27T10:00:00+00:00", conversa_id="c1",
    )
    assert banco.entrega_ja_vista(fonte_id, "msg_importante") is True

    _encher(banco, fonte_id, "assinatura", banco.ENTREGAS_POR_FONTE + 10, inicio=1000)

    assert banco.entrega_ja_vista(fonte_id, "msg_importante") is True


def test_as_aceitas_tambem_tem_teto(tmp_path):
    """Separar os baldes nao pode virar crescimento sem limite do outro lado --
    uma fonte movimentada e legitima nao pode encher o banco."""
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    _encher(banco, fonte_id, "aceita", banco.ENTREGAS_POR_FONTE + 25)

    entregas = banco.listar_entregas(fonte_id)
    assert len(entregas) == banco.ENTREGAS_POR_FONTE
    # As que ficam sao as MAIS RECENTES, o mesmo criterio da listagem.
    assert entregas[0]["webhook_id"] == f"aceita_{banco.ENTREGAS_POR_FONTE + 24}"


def test_o_balde_de_recusas_tambem_tem_teto(tmp_path):
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    _encher(banco, fonte_id, "assinatura", banco.ENTREGAS_POR_FONTE + 25)
    assert len(banco.listar_entregas(fonte_id)) == banco.ENTREGAS_POR_FONTE


def test_o_teto_por_fonte_nao_depende_de_quantos_vereditos_existem(tmp_path):
    """Podar por veredito INDIVIDUAL faria o teto virar 200 x len(VEREDITOS), e
    crescer sozinho toda vez que alguem acrescentasse um motivo de recusa. Sao
    dois baldes, e continuam dois."""
    banco = _banco(tmp_path)
    fonte_id = _fonte(banco)
    for indice, veredito in enumerate(VEREDITOS):
        if veredito == "aceita":
            continue
        _encher(banco, fonte_id, veredito, 60, inicio=indice * 1000)

    assert len(banco.listar_entregas(fonte_id)) == banco.ENTREGAS_POR_FONTE


def test_a_poda_e_por_fonte_e_nao_alcanca_a_vizinha(tmp_path):
    banco = _banco(tmp_path)
    primeira = _fonte(banco)
    segunda = banco.criar_fonte(
        nome="Intercom", canal="webchat", tipo="webhook",
        variavel_segredo="FRAUS_WEBHOOK_INT", criada_em="2026-08-27T10:00:00+00:00",
    )["id"]
    _encher(banco, segunda, "aceita", 3)

    _encher(banco, primeira, "assinatura", banco.ENTREGAS_POR_FONTE + 10, inicio=1000)

    assert len(banco.listar_entregas(segunda)) == 3
