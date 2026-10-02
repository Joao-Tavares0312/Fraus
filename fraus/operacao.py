"""Analises operacionais locais. Resultados observados e simulacoes explicitas.

Nao chama LLM, nao pontua atendentes e nao altera o score persistido.
"""
import hashlib
from collections import Counter, defaultdict
from datetime import timedelta
from statistics import median

from fraus.indicadores import calcular_nps, nps_com_intervalo

TETO_RADAR = 1500
PARADAS = "a o as os de da do das dos e em na no nas nos um uma para por com que se me eu voce voces meu minha seu sua foi ser esta estou isso isto esse essa ao aos mas ja muito mais como nao sim bom dia obrigado obrigada favor atendimento cliente bot humano".split()
# As formas ACENTUADAS das de cima. O vetorizador nao tira acento (e nao deve:
# os termos do tema sao mostrados como o cliente escreveu), entao "nao" na
# lista nao barrava "não" -- e "não", "já", "você" e "está" viravam nome de
# tema (auditoria de 02/10/2026).
PARADAS += "à às você vocês está já não é".split()


def descobrir_temas(registros, faixas):
    """Agrupa por vocabulario semelhante; os nomes sao termos observados.

    A janela atual e os sete dias terminados no ultimo dia DO RECORTE.
    Compara taxas por conversa, nao contagens cruas de periodos diferentes.
    """
    if not registros:
        return {"temas": [], "amostra": 0, "truncadas": 0, "janela": None}
    registros = sorted(registros, key=lambda r: (r[0].iniciada_em, r[0].id), reverse=True)
    truncadas = max(0, len(registros) - TETO_RADAR)
    registros = registros[:TETO_RADAR]
    textos = [" ".join(m.texto for m in c.mensagens_cliente) for c, _ in registros]
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import DBSCAN
    import numpy as np
    vetor = TfidfVectorizer(stop_words=PARADAS, ngram_range=(1, 2), max_features=6000)
    try:
        matriz = vetor.fit_transform(textos)
    except ValueError as erro:
        if "empty vocabulary" not in str(erro):
            raise
        return {"temas": [], "amostra": len(registros), "truncadas": truncadas, "janela": None}
    classes = DBSCAN(eps=0.65, min_samples=2, metric="cosine").fit_predict(matriz)
    fim = max(c.iniciada_em.date() for c, _ in registros)
    inicio = fim - timedelta(days=6)
    anterior = inicio - timedelta(days=7)
    n_atual = sum(inicio <= c.iniciada_em.date() <= fim for c, _ in registros)
    n_anterior = sum(anterior <= c.iniciada_em.date() < inicio for c, _ in registros)
    grupos = defaultdict(list)
    for i, classe in enumerate(classes):
        if classe >= 0:
            grupos[int(classe)].append(i)
    nomes = vetor.get_feature_names_out()
    temas = []
    for indices in grupos.values():
        pesos = np.asarray(matriz[indices].mean(axis=0)).ravel()
        termos = [str(nomes[i]) for i in pesos.argsort()[::-1][:4] if pesos[i] > 0]
        recentes = sum(inicio <= registros[i][0].iniciada_em.date() <= fim for i in indices)
        anteriores = sum(anterior <= registros[i][0].iniciada_em.date() < inicio for i in indices)
        taxa_atual = recentes / n_atual if n_atual else None
        taxa_anterior = anteriores / n_anterior if n_anterior else None
        scores = [registros[i][1] for i in indices if registros[i][1] is not None]
        temas.append({"id": hashlib.sha256("|".join(sorted(termos)).encode()).hexdigest()[:16],
            "termos": termos, "conversa_ids": [registros[i][0].id for i in indices],
            "total": len(indices), "recentes": recentes, "anteriores": anteriores,
            "taxa_atual": taxa_atual, "taxa_anterior": taxa_anterior,
            "emergente": bool(recentes >= 3 and n_anterior >= 5 and taxa_atual is not None and taxa_atual > 2 * taxa_anterior),
            "nps": calcular_nps(scores, faixas), "intervalo": nps_com_intervalo(scores, faixas)})
    return {"temas": sorted(temas, key=lambda t: (-t["emergente"], -t["recentes"], -t["total"], t["id"])),
        "amostra": len(registros), "truncadas": truncadas,
        "janela": {"de": inicio.isoformat(), "ate": fim.isoformat(), "base_atual": n_atual, "base_anterior": n_anterior},
        "metodo": "TF-IDF e agrupamento por similaridade de vocabulario; alerta: >=3 recentes, >=5 na base anterior e taxa superior ao dobro"}


def simular_escala(registros, turnos, duracao_s, custo_hora):
    """Reproduz a demanda observada em filas FCFS, sem alterar atendimentos.

    Cada posto pertence a um turno. Servico nao e interrompido nem pode
    ultrapassar o fim do turno; demanda sem posto disponivel fica pendente.
    Duracao de servico e custo sao hipoteses declaradas pelo operador.
    """
    por_dia = defaultdict(list)
    for c, _ in registros:
        if c.escalou_para_humano or any(m.autor == "humano" for m in c.mensagens):
            por_dia[c.iniciada_em.date()].append(c)
    esperas = []
    dias = []
    pendentes = 0
    for dia, conversas in sorted(por_dia.items()):
        postos = []
        for turno in turnos:
            for _ in range(turno["pessoas"]):
                postos.append({"livre": turno["inicio"] * 3600, "fim": turno["fim"] * 3600,
                    "canais": turno.get("canais", [])})
        esperas_dia = []
        nao_atendidas = 0
        for c in sorted(conversas, key=lambda c: (c.iniciada_em, c.id)):
            chegada = c.iniciada_em.hour * 3600 + c.iniciada_em.minute * 60 + c.iniciada_em.second
            disponiveis = [(max(p["livre"], chegada), i) for i, p in enumerate(postos)
                if (not p["canais"] or c.canal in p["canais"]) and max(p["livre"], chegada) + duracao_s <= p["fim"]]
            if not disponiveis:
                nao_atendidas += 1
                continue
            inicio, indice = min(disponiveis)
            postos[indice]["livre"] = inicio + duracao_s
            esperas_dia.append(inicio - chegada)
        pendentes += nao_atendidas
        esperas.extend(esperas_dia)
        dias.append({"dia": dia.isoformat(), "demanda": len(conversas), "atendidas": len(esperas_dia),
            "pendentes": nao_atendidas, "espera_mediana_s": median(esperas_dia) if esperas_dia else None})
    dias_no_recorte = (max(c.iniciada_em.date() for c, _ in registros) - min(c.iniciada_em.date() for c, _ in registros)).days + 1 if registros else 0
    horas_por_dia = sum((t["fim"] - t["inicio"]) * t["pessoas"] for t in turnos)
    p95 = sorted(esperas)[max(0, __import__("math").ceil(0.95 * len(esperas)) - 1)] if esperas else None
    dias_base = defaultdict(set)
    contatos = Counter()
    for c, _ in registros:
        dias_base[c.iniciada_em.weekday()].add(c.iniciada_em.date())
        if c.escalou_para_humano or any(m.autor == "humano" for m in c.mensagens):
            contatos[c.iniciada_em.weekday()] += 1
    previsao = [{"dia_semana": d, "dias_observados": len(datas), "contatos_medios": contatos[d] / len(datas)} for d, datas in sorted(dias_base.items())]
    return {"demanda": sum(d["demanda"] for d in dias), "atendidas": len(esperas), "pendentes": pendentes,
        "espera_mediana_s": median(esperas) if esperas else None, "espera_p95_s": p95,
        "custo": round(horas_por_dia * dias_no_recorte * custo_hora, 2), "dias": dias, "previsao": previsao,
        "hipoteses": {"duracao_s": duracao_s, "custo_hora": custo_hora, "turnos": turnos},
        "metodo": "simulacao FCFS sobre chegadas historicas; a previsao usa so dias com registros, sem afirmar dias vazios nem prever satisfacao; horarios no fuso registrado"}


def limitar_esperas(conversa, teto_s):
    """Cenario de espera: desloca a resposta e o restante, mantendo a ordem."""
    mensagens = []
    deslocamento = timedelta(0)
    aguardando = None
    for m in conversa.mensagens:
        horario = m.enviada_em - deslocamento
        if m.autor == "cliente":
            if aguardando is None:
                aguardando = horario
        elif aguardando is not None:
            alvo = max(aguardando + timedelta(seconds=teto_s), mensagens[-1].enviada_em)
            excesso = max(0, (horario - alvo).total_seconds())
            deslocamento += timedelta(seconds=excesso)
            horario -= timedelta(seconds=excesso)
            aguardando = None
        mensagens.append(m.model_copy(update={"enviada_em": horario}))
    encerrada = conversa.encerrada_em - deslocamento if conversa.encerrada_em else None
    if encerrada:
        encerrada = max(encerrada, mensagens[-1].enviada_em)
    return conversa.model_copy(update={"mensagens": mensagens, "encerrada_em": encerrada})
