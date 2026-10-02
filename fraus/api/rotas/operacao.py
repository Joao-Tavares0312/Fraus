"""Operacao: radar, escala, jornada, problemas, replay, laboratorio e acesso."""
import csv
import hashlib
import io
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator

from fraus.api.contexto import Contexto, obter_contexto
from fraus.api.motor_preguicoso import motor_e_real
from fraus.fusor import Fusor
from fraus.indicadores import nps_com_intervalo, nota_0_10
from fraus.operacao import descobrir_temas, limitar_esperas, simular_escala
from fraus.seguranca.pii import censurar_pii

router = APIRouter(prefix="/operacao")


class Turno(BaseModel):
    inicio: int = Field(ge=0, le=23)
    fim: int = Field(ge=1, le=24)
    pessoas: int = Field(ge=0, le=100)
    canais: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def valido(self):
        if self.fim <= self.inicio:
            raise ValueError("fim do turno precisa ser depois do inicio")
        return self


class CenarioEscala(BaseModel):
    turnos: list[Turno] = Field(min_length=1, max_length=24)
    duracao_s: float = Field(gt=0, le=14400)
    custo_hora: float = Field(ge=0, le=10000)


class Equipe(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    membros: list[int] = Field(default_factory=list, max_length=100)
    competencias: list[str] = Field(default_factory=list, max_length=20)
    canais: list[str] = Field(default_factory=list, max_length=20)


class VinculoJornada(BaseModel):
    referencia: str = Field(min_length=6, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    conversa_ids: list[str] = Field(min_length=1, max_length=50)


class Problema(BaseModel):
    titulo: str = Field(min_length=3, max_length=150)
    conversa_ids: list[str] = Field(min_length=1, max_length=50)
    equipe_id: str | None = None
    responsavel_id: int | None = None
    prazo: date
    termos: list[str] = Field(default_factory=list, max_length=8)


class AcaoProblema(BaseModel):
    estado: str = Field(pattern=r"^(aberto|em_andamento|resolvido)$")
    acao: str = Field(min_length=3, max_length=1000)


class Politica(BaseModel):
    canais: list[str] = Field(max_length=30)
    equipe_id: str | None = None
    exportar_minutos: int = Field(default=0, ge=0, le=480)


class CenarioLaboratorio(BaseModel):
    conversa_id: str
    espera_maxima_s: float | None = Field(default=None, gt=0, le=14400)
    ocultar_mensagem: int | None = Field(default=None, ge=0)


class ComparacaoModelos(BaseModel):
    conversa_ids: list[str] = Field(min_length=1, max_length=30)


class ConviteEquipe(BaseModel):
    papel: Literal["gestor", "membro"] = "membro"
    validade_horas: int = Field(default=24, ge=1, le=168)
    limite: int = Field(default=1, ge=1, le=100)


class PapelEquipe(BaseModel):
    papel: Literal["proprietario", "gestor", "membro"] | None = None


def exigir_gestao(ctx, equipe, proprietario=False):
    if ctx.papel in (None, "dev"):
        return
    papel = equipe.get("papeis", {}).get(str(ctx.usuario_id), "membro")
    if ctx.usuario_id not in equipe["membros"] or papel not in (["proprietario"] if proprietario else ["proprietario", "gestor"]):
        raise HTTPException(403, "seu papel na equipe nao permite esta acao")


def ator(ctx):
    return str(ctx.usuario_id) if ctx.usuario_id is not None else "credencial-tecnica-ou-local"


def buscar_conversa(ctx, identificador):
    achado = ctx.banco.buscar(identificador)
    if achado is None:
        raise HTTPException(404, "conversa nao encontrada no seu escopo")
    return achado[0]


def exigir_real(ctx):
    if not motor_e_real(ctx.motor):
        raise HTTPException(503, "esta leitura exige o motor real, nao o motor de demonstracao")


def exigir_orcamento(conversas):
    if sum(len(c.mensagens_cliente) for c in conversas) > 40:
        raise HTTPException(400, "a leitura aceita ate 40 mensagens do cliente por requisicao")


def ficha(ctx, conversa, score):
    return {"id": conversa.id, "canal": conversa.canal, "iniciada_em": conversa.iniciada_em.isoformat(),
        "score": score, "nota": nota_0_10(score) if score is not None else None,
        "categoria": ctx.categoria_de(score, ctx.faixas_vigentes()), "feedback": conversa.feedback_declarado}


@router.get("/radar")
def radar(de: str | None = None, ate: str | None = None, ctx: Contexto = Depends(obter_contexto)):
    return descobrir_temas(ctx.registros_do_recorte(de, ate), ctx.faixas_vigentes())


@router.post("/escala/simular")
def escala(pedido: CenarioEscala, de: str | None = None, ate: str | None = None, ctx: Contexto = Depends(obter_contexto)):
    return simular_escala(ctx.registros_do_recorte(de, ate), [t.model_dump() for t in pedido.turnos], pedido.duracao_s, pedido.custo_hora)


def apresentar_equipe(ctx, equipe):
    """O mesmo contrato de hierarquia na listagem e nas mutacoes."""
    return {**equipe,
        "meu_papel": "proprietario" if ctx.papel in (None, "dev") else equipe.get("papeis", {}).get(str(ctx.usuario_id), "membro"),
        "integrantes": [{"id": i, "nome": (ctx.banco.buscar_usuario(i) or {"nome": "Conta removida"})["nome"],
            "papel": equipe.get("papeis", {}).get(str(i), "membro")} for i in equipe["membros"]]}


@router.get("/equipes")
def equipes(ctx: Contexto = Depends(obter_contexto)):
    registros = ctx.banco.documentos("equipe")
    if ctx.papel == "usuario":
        registros = [e for e in registros if ctx.usuario_id in e["membros"]]
    return {"equipes": [apresentar_equipe(ctx, e) for e in registros]}


@router.post("/equipes")
def criar_equipe(pedido: Equipe, ctx: Contexto = Depends(obter_contexto)):
    if any(ctx.banco.buscar_usuario(i) is None for i in pedido.membros):
        raise HTTPException(400, "um dos membros nao existe")
    identificador = uuid4().hex
    valor = pedido.model_dump()
    valor["nome"] = censurar_pii(pedido.nome.strip())
    valor["competencias"] = [censurar_pii(t[:80]) for t in pedido.competencias]
    valor["papeis"] = {str(i): "membro" for i in pedido.membros}
    if ctx.usuario_id is not None:
        valor["membros"] = sorted(set(valor["membros"]) | {ctx.usuario_id})
        valor["papeis"][str(ctx.usuario_id)] = "proprietario"
    ctx.banco.guardar_documento("equipe", identificador, valor)
    ctx.banco.auditar(ator(ctx), "criar_equipe", identificador)
    return apresentar_equipe(ctx, {"id": identificador, **valor})


@router.put("/equipes/{identificador}")
def editar_equipe(identificador: str, pedido: Equipe, ctx: Contexto = Depends(obter_contexto)):
    if any(ctx.banco.buscar_usuario(i) is None for i in pedido.membros):
        raise HTTPException(400, "um dos membros nao existe")
    valor = pedido.model_dump()
    valor["nome"] = censurar_pii(pedido.nome.strip())
    valor["competencias"] = [censurar_pii(t[:80]) for t in pedido.competencias]
    def transformar(anterior):
        exigir_gestao(ctx, anterior)
        if ctx.papel == "usuario" and (set(valor["membros"]) != set(anterior["membros"]) or set(valor["canais"]) != set(anterior["canais"])):
            raise HTTPException(403, "membros usam convites e hierarquia; canais exigem administrador")
        proprietarios = {int(i) for i, p in anterior.get("papeis", {}).items() if p == "proprietario"}
        if not proprietarios.issubset(set(valor["membros"])):
            raise HTTPException(409, "preserve os proprietarios; altere a hierarquia antes de remover")
        return {**valor, "papeis": {str(i): anterior.get("papeis", {}).get(str(i), "membro") for i in valor["membros"]}}
    atualizado = ctx.banco.alterar_documento("equipe", identificador, transformar)
    if atualizado is None:
        raise HTTPException(404, "equipe inexistente")
    ctx.banco.auditar(ator(ctx), "editar_equipe", identificador)
    return apresentar_equipe(ctx, {"id": identificador, **atualizado})


@router.patch("/equipes/{identificador}/membros/{usuario_id}")
def definir_papel(identificador: str, usuario_id: int, pedido: PapelEquipe, ctx: Contexto = Depends(obter_contexto)):
    def transformar(equipe):
        atual = equipe.get("papeis", {}).get(str(usuario_id), "membro")
        exigir_gestao(ctx, equipe, proprietario=atual != "membro" or pedido.papel in ("proprietario", "gestor"))
        if usuario_id not in equipe["membros"]:
            raise HTTPException(404, "membro inexistente")
        papeis = equipe.setdefault("papeis", {})
        if atual == "proprietario" and pedido.papel != "proprietario" and sum(p == "proprietario" for p in papeis.values()) <= 1:
            raise HTTPException(409, "a equipe precisa preservar pelo menos um proprietario")
        if pedido.papel is None:
            equipe["membros"].remove(usuario_id)
            papeis.pop(str(usuario_id), None)
        else:
            papeis[str(usuario_id)] = pedido.papel
        return equipe
    equipe = ctx.banco.alterar_documento("equipe", identificador, transformar)
    if equipe is None:
        raise HTTPException(404, "equipe inexistente")
    ctx.banco.auditar(ator(ctx), "alterar_hierarquia", identificador)
    return apresentar_equipe(ctx, {"id": identificador, **equipe})


@router.post("/equipes/{identificador}/convites")
def gerar_convite(identificador: str, pedido: ConviteEquipe, ctx: Contexto = Depends(obter_contexto)):
    equipe = ctx.banco.documento("equipe", identificador)
    if equipe is None:
        raise HTTPException(404, "equipe inexistente")
    exigir_gestao(ctx, equipe, proprietario=pedido.papel == "gestor")
    if ctx.jwt_segredo is None:
        raise HTTPException(503, "configure o login para convidar pessoas")
    token = secrets.token_urlsafe(32)
    chave = hashlib.sha256(token.encode()).hexdigest()
    convite = {"equipe_id": identificador, "papel": pedido.papel, "expira_em": (datetime.now(timezone.utc) + timedelta(hours=pedido.validade_horas)).isoformat(), "limite": pedido.limite, "aceitos": [], "revogado": False}
    ctx.banco.guardar_documento("convite", chave, convite)
    ctx.banco.auditar(ator(ctx), "gerar_convite", identificador)
    return {"id": chave, "token": token, **{k: convite[k] for k in ("papel", "expira_em", "limite")}}


@router.get("/equipes/{identificador}/convites")
def listar_convites(identificador: str, ctx: Contexto = Depends(obter_contexto)):
    equipe = ctx.banco.documento("equipe", identificador)
    if equipe is None:
        raise HTTPException(404, "equipe inexistente")
    exigir_gestao(ctx, equipe)
    return {"convites": [{"id": c["id"], "papel": c["papel"], "expira_em": c["expira_em"], "limite": c["limite"], "usos": len(set(c["aceitos"]) | set(c.get("reservas", []))), "revogado": c["revogado"]} for c in ctx.banco.documentos("convite") if c["equipe_id"] == identificador]}


@router.post("/equipes/{identificador}/convites/{chave}/revogar")
def revogar_convite(identificador: str, chave: str, ctx: Contexto = Depends(obter_contexto)):
    def transformar(convite):
        equipe = ctx.banco.documento("equipe", identificador)
        if not equipe or convite["equipe_id"] != identificador:
            raise HTTPException(404, "convite inexistente")
        exigir_gestao(ctx, equipe)
        convite["revogado"] = True
        return convite
    if ctx.banco.alterar_documento("convite", chave, transformar) is None:
        raise HTTPException(404, "convite inexistente")
    ctx.banco.auditar(ator(ctx), "revogar_convite", identificador)
    return {"revogado": True}


@router.get("/convites/{token}")
def ver_convite(token: str, ctx: Contexto = Depends(obter_contexto)):
    # Com sessao, quem criou a conta por este link ainda ve o convite: a vaga
    # que ele ocupa e a dela, e a tela de aceite comeca por esta leitura.
    convite = ctx.banco.convite_valido(token, ctx.usuario_id)
    equipe = ctx.banco.documento("equipe", convite["equipe_id"]) if convite else None
    if not equipe:
        raise HTTPException(410, "convite invalido, expirado ou esgotado")
    return {"nome": equipe["nome"], "papel": convite["papel"], "expira_em": convite["expira_em"], "canais": equipe["canais"]}


@router.post("/convites/{token}/aceitar")
def aceitar_convite(token: str, ctx: Contexto = Depends(obter_contexto)):
    if ctx.usuario_id is None:
        raise HTTPException(401, "entre na sua conta antes de aceitar o convite")
    resultado = ctx.banco.aceitar_convite(token, ctx.usuario_id)
    if resultado is None:
        raise HTTPException(410, "convite invalido, expirado ou esgotado")
    ctx.banco.auditar(ator(ctx), "aceitar_convite", resultado["equipe_id"])
    return resultado


@router.get("/jornadas")
def jornadas(de: str | None = None, ate: str | None = None, ctx: Contexto = Depends(obter_contexto)):
    vinculos = {v["id"]: v["referencia"] for v in ctx.banco.documentos("jornada")}
    grupos = {}
    for c, s in ctx.registros_do_recorte(de, ate):
        if c.id in vinculos:
            grupos.setdefault(vinculos[c.id], []).append(ficha(ctx, c, s))
    saida = []
    for referencia, contatos in grupos.items():
        contatos.sort(key=lambda c: (c["iniciada_em"], c["id"]))
        saida.append({"referencia": referencia, "contatos": contatos,
            "recontatos": max(0, len(contatos) - 1), "canais": sorted({c["canal"] for c in contatos}),
            "resolucao_declarada": contatos[-1]["feedback"] == 1 if contatos[-1]["feedback"] is not None else None})
    return {"jornadas": sorted(saida, key=lambda j: (-j["recontatos"], j["referencia"]))}


@router.post("/jornadas")
def vincular_jornada(pedido: VinculoJornada, ctx: Contexto = Depends(obter_contexto)):
    for i in pedido.conversa_ids:
        buscar_conversa(ctx, i)
    referencia = hashlib.sha256(pedido.referencia.encode()).hexdigest()[:24]
    ctx.banco.guardar_documentos([("jornada", i, {"referencia": referencia}) for i in set(pedido.conversa_ids)])
    ctx.banco.auditar(ator(ctx), "vincular_jornada", referencia)
    return {"referencia": referencia, "vinculadas": len(set(pedido.conversa_ids))}


def visivel(ctx, problema):
    return all(ctx.banco.buscar(i) is not None for i in problema["conversa_ids"])


def medir_problema(ctx, problema):
    resolvido_em = problema.get("resolvido_em")
    limite = datetime.fromisoformat(resolvido_em) if resolvido_em else None
    canais = set(problema["canais"])
    termos = problema["termos"]
    antes, depois = [], []
    for c, s in ctx.banco.todas():
        texto = " ".join(m.texto for m in c.mensagens_cliente).casefold()
        corresponde = c.canal in canais and (any(t.casefold() in texto for t in termos) if termos else c.id in problema["conversa_ids"])
        if corresponde and s is not None:
            (depois if limite and c.iniciada_em >= limite else antes).append(s)
    a = nps_com_intervalo(antes, ctx.faixas_vigentes())
    d = nps_com_intervalo(depois, ctx.faixas_vigentes())
    delta = d["nps"] - a["nps"] if a and d and a["nps"] is not None and d["nps"] is not None else None
    return {"antes": a, "depois": d, "delta_nps": round(delta, 2) if delta is not None else None,
        "criterio": "mesmos canais e pelo menos um termo; sem termos, so evidencias vinculadas. Comparacao descritiva, nao prova de causalidade"}


@router.get("/problemas")
def problemas(ctx: Contexto = Depends(obter_contexto)):
    return {"problemas": [{**p, "medicao": medir_problema(ctx, p)} for p in ctx.banco.documentos("problema") if visivel(ctx, p)]}


@router.post("/problemas")
def criar_problema(pedido: Problema, ctx: Contexto = Depends(obter_contexto)):
    conversas = [buscar_conversa(ctx, i) for i in set(pedido.conversa_ids)]
    if pedido.equipe_id and ctx.banco.documento("equipe", pedido.equipe_id) is None:
        raise HTTPException(400, "equipe inexistente")
    if pedido.responsavel_id and ctx.banco.buscar_usuario(pedido.responsavel_id) is None:
        raise HTTPException(400, "responsavel inexistente")
    identificador = uuid4().hex
    valor = {**pedido.model_dump(mode="json"), "titulo": censurar_pii(pedido.titulo.strip()),
        "termos": [censurar_pii(t.strip())[:80] for t in pedido.termos if t.strip()],
        "canais": sorted({c.canal for c in conversas}), "estado": "aberto", "acoes": [],
        "criado_em": datetime.now(timezone.utc).isoformat(), "resolvido_em": None}
    ctx.banco.guardar_documento("problema", identificador, valor)
    ctx.banco.auditar(ator(ctx), "criar_problema", identificador)
    return {"id": identificador, **valor}


@router.patch("/problemas/{identificador}")
def agir_problema(identificador: str, pedido: AcaoProblema, ctx: Contexto = Depends(obter_contexto)):
    agora = datetime.now(timezone.utc).isoformat()
    def transformar(problema):
        if not visivel(ctx, problema):
            raise HTTPException(404, "problema nao encontrado no seu escopo")
        problema["estado"] = pedido.estado
        problema["resolvido_em"] = (problema.get("resolvido_em") or agora) if pedido.estado == "resolvido" else None
        problema["acoes"].append({"em": agora, "ator": ator(ctx), "acao": censurar_pii(pedido.acao), "estado": pedido.estado})
        return problema
    problema = ctx.banco.alterar_documento("problema", identificador, transformar)
    if problema is None:
        raise HTTPException(404, "problema nao encontrado no seu escopo")
    ctx.banco.auditar(ator(ctx), "agir_problema", identificador)
    return {"id": identificador, **problema, "medicao": medir_problema(ctx, problema)}


@router.get("/replay/{identificador}")
def replay(identificador: str, ctx: Contexto = Depends(obter_contexto)):
    exigir_real(ctx)
    conversa = buscar_conversa(ctx, identificador)
    exigir_orcamento([conversa])
    curadoria, faixas = ctx.curadoria_vigente(), ctx.faixas_vigentes()
    if len(conversa.mensagens) > 80:
        raise HTTPException(400, "replay aceita ate 80 mensagens")
    scores = ctx.motor.scores_do_replay(conversa, curadoria)
    pontos = []
    anterior = None
    for indice, mensagem in enumerate(conversa.mensagens):
        score = scores[indice]
        delta = score - anterior if score is not None and anterior is not None else None
        pontos.append({"indice": indice, "autor": mensagem.autor, "texto": mensagem.texto,
            "enviada_em": mensagem.enviada_em.isoformat(), "score": score,
            "nota": nota_0_10(score) if score is not None else None,
            "categoria": ctx.categoria_de(score, faixas), "delta": round(delta, 2) if delta is not None else None,
            "virada": bool(delta is not None and abs(delta) >= 10)})
        anterior = score
    return {"conversa_id": identificador, "pontos": pontos, "criterio_virada": 10,
        "metodo": "estimativa por prefixo; cada fala e lida isoladamente uma vez, sem falas futuras. Virada = variacao de pelo menos 10 pontos; nao e explicacao causal"}


@router.post("/laboratorio/cenario")
def cenario(pedido: CenarioLaboratorio, ctx: Contexto = Depends(obter_contexto)):
    exigir_real(ctx)
    original = buscar_conversa(ctx, pedido.conversa_id)
    exigir_orcamento([original])
    alterada = original.model_copy(deep=True)
    if pedido.ocultar_mensagem is not None:
        i = pedido.ocultar_mensagem
        if i >= len(alterada.mensagens) or alterada.mensagens[i].autor != "cliente":
            raise HTTPException(400, "escolha o indice de uma mensagem do cliente")
        if len(alterada.mensagens) == 1:
            raise HTTPException(400, "o cenario precisa preservar ao menos uma mensagem")
        alterada.mensagens = alterada.mensagens[:i] + alterada.mensagens[i + 1:]
    if pedido.espera_maxima_s is not None:
        alterada = limitar_esperas(alterada, pedido.espera_maxima_s)
    curadoria = ctx.curadoria_vigente()
    antes = ctx.motor.pontuar_conversa(original, curadoria)
    depois = ctx.motor.pontuar_conversa(alterada, curadoria)
    return {"original": ficha(ctx, original, antes), "cenario": ficha(ctx, alterada, depois),
        "delta_score": depois - antes if depois is not None and antes is not None else None,
        "hipoteses": pedido.model_dump(), "mensagens_cenario": [m.model_dump(mode="json") for m in alterada.mensagens],
        "metodo": "sensibilidade da previsao a uma alteracao controlada; nao mede efeito real no cliente. Nenhum score do banco e alterado"}


@router.post("/laboratorio/comparar")
def comparar(pedido: ComparacaoModelos, ctx: Contexto = Depends(obter_contexto)):
    exigir_real(ctx)
    conversas = [buscar_conversa(ctx, i) for i in dict.fromkeys(pedido.conversa_ids)]
    exigir_orcamento(conversas)
    caminho = os.environ.get("FRAUS_FUSOR_CANDIDATO")
    if not caminho:
        raise HTTPException(503, "configure FRAUS_FUSOR_CANDIDATO no servidor com o arquivo de um fusor compativel")
    try:
        candidato = Fusor.carregar(Path(caminho))
    except (FileNotFoundError, ValueError) as erro:
        raise HTTPException(503, "o fusor candidato nao esta disponivel ou e incompativel com o contrato vigente") from erro
    curadoria = ctx.curadoria_vigente()
    resultados = []
    for c in conversas:
        scores = ctx.motor.comparar_fusor(c, candidato, curadoria)
        atual, proximo = ficha(ctx, c, scores["atual"]), ficha(ctx, c, scores["candidato"])
        resultados.append({"atual": atual, "candidato": proximo, "mudou_categoria": atual["categoria"] != proximo["categoria"]})
    fatias = []
    for canal in sorted({c.canal for c in conversas}):
        linhas = [r for r in resultados if r["atual"]["canal"] == canal]
        fatias.append({"canal": canal, "n": len(linhas), "mudaram": sum(r["mudou_categoria"] for r in linhas)})
    return {"resultados": resultados, "fatias": fatias, "metodo": "mesmas features e mesmos atendimentos para dois fusores. Mudanca nao significa melhora sem rotulos independentes; nenhum artefato e promovido"}


@router.get("/acesso")
def mapa_acesso(ctx: Contexto = Depends(obter_contexto)):
    canais = sorted({c.canal for c, _ in ctx.banco.todas()})
    usuarios = []
    agora = datetime.now(timezone.utc)
    for u in ctx.banco.listar_usuarios():
        p = ctx.banco.documento("permissao", str(u["id"]))
        permitidos = canais if u["papel"] == "dev" or p is None else p["canais"]
        expira = p.get("exporta_ate") if p else None
        usuarios.append({"id": u["id"], "nome": u["nome"], "papel": u["papel"], "ativo": u["ativo"],
            "canais": permitidos if u["ativo"] else [], "configurado": p is not None,
            "equipe_id": p.get("equipe_id") if p else None,
            "exporta_ate": expira, "exportacao_liberada": u["ativo"] and (u["papel"] == "dev" or bool(expira and datetime.fromisoformat(expira) > agora))})
    return {"usuarios": usuarios, "canais": canais, "equipes": ctx.banco.documentos("equipe"),
        "auditoria": ctx.banco.auditoria(), "modo": "autenticado" if ctx.autenticacao_ligada() else "aberto-local",
        "aviso": "dev e credenciais tecnicas conservam acesso administrativo. Sem politica, usuarios conservam o acesso anterior. O mapa simula alcance, nao detecta ataques"}


@router.put("/acesso/{usuario_id}")
def configurar_acesso(usuario_id: int, pedido: Politica, ctx: Contexto = Depends(obter_contexto)):
    usuario = ctx.banco.buscar_usuario(usuario_id)
    if usuario is None:
        raise HTTPException(404, "usuario inexistente")
    if usuario["papel"] == "dev":
        raise HTTPException(409, "dev tem acesso administrativo; a politica por canal vale para o papel usuario")
    if pedido.equipe_id and ctx.banco.documento("equipe", pedido.equipe_id) is None:
        raise HTTPException(400, "equipe inexistente")
    expira = (datetime.now(timezone.utc) + timedelta(minutes=pedido.exportar_minutos)).isoformat() if pedido.exportar_minutos else None
    valor = {"canais": sorted(set(pedido.canais)), "equipe_id": pedido.equipe_id, "exporta_ate": expira}
    ctx.banco.guardar_documento("permissao", str(usuario_id), valor)
    ctx.banco.auditar(ator(ctx), "alterar_permissao", str(usuario_id))
    return valor


@router.post("/acesso/{usuario_id}/revogar-sessoes")
def revogar_sessoes(usuario_id: int, ctx: Contexto = Depends(obter_contexto)):
    if ctx.banco.buscar_usuario(usuario_id) is None:
        raise HTTPException(404, "usuario inexistente")
    versao = ctx.banco.revogar_sessoes(usuario_id)
    ctx.banco.auditar(ator(ctx), "revogar_sessoes", str(usuario_id))
    return {"revogadas": True, "versao": versao}


def exigir_exportacao(ctx):
    if ctx.papel == "usuario":
        p = ctx.banco.documento("permissao", str(ctx.usuario_id))
        if not p or not p.get("exporta_ate") or datetime.fromisoformat(p["exporta_ate"]) <= datetime.now(timezone.utc):
            raise HTTPException(403, "a exportacao exige autorizacao temporaria de um administrador")


@router.post("/exportacao/autorizar")
def autorizar_exportacao(de: str | None = None, ate: str | None = None, ctx: Contexto = Depends(obter_contexto)):
    exigir_exportacao(ctx)
    ctx.banco.auditar(ator(ctx), "exportar_tabela", f"{de or '*'}:{ate or '*'}")
    return {"autorizada": True}


@router.get("/exportar")
def exportar(de: str | None = None, ate: str | None = None, ctx: Contexto = Depends(obter_contexto)):
    exigir_exportacao(ctx)
    registros = ctx.registros_do_recorte(de, ate)
    arquivo = io.StringIO()
    escritor = csv.writer(arquivo)
    escritor.writerow(["id", "canal", "iniciada_em", "score_inferido_estimativa", "nota_inferida_estimativa", "categoria"])
    for c, s in registros:
        f = ficha(ctx, c, s)
        # Neutraliza formulas de planilha em campos de origem externa.
        valores = [f[k] if f[k] is not None else "" for k in ("id", "canal", "iniciada_em", "score", "nota", "categoria")]
        escritor.writerow(["'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v for v in valores])
    ctx.banco.auditar(ator(ctx), "exportar_recorte", f"{de or '*'}:{ate or '*'}")
    return Response(arquivo.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="fraus-operacao.csv"'})
