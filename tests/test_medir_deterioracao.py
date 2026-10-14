import importlib.util
import inspect
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fraus.ingest.simulador import gerar_conversa
from fraus.modelos import Conversa, Mensagem

RAIZ = Path(__file__).resolve().parent.parent


def _script():
    spec = importlib.util.spec_from_file_location("medir_deterioracao", RAIZ / "scripts" / "medir_deterioracao.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["medir_deterioracao"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


T0 = datetime(2026, 10, 1, 10, tzinfo=timezone.utc)


def _c(n):
    return Conversa(id="c", canal="chat", iniciada_em=T0, mensagens=[
        Mensagem(autor="cliente" if k % 2 == 0 else "bot", texto="x", enviada_em=T0 + timedelta(minutes=k))
        for k in range(n)])


def test_simulador_sorteia_falas_de_um_rotulo_so():
    """Se o simulador ganhar trajetoria, isto quebra e a declaracao de artefato
    tem de ser revista."""
    assert list(inspect.signature(gerar_conversa).parameters) == ["rotulo", "frases_cliente", "semente"]
    assert "artefato do gerador" in _script().conferir_trajetoria()


def test_medir_recall_falso_alarme_e_lead():
    m = _script()
    casos = [([90.0, 40.0, 30.0], _c(3), 0),     # detrator, virada no 1: 1 fala, 60 s
             ([90.0, 90.0, 90.0], _c(3), 0),     # detrator perdido
             ([90.0, 30.0, 30.0], _c(3), 2)]     # falso alarme
    r = m.medir(casos, {"limiar 65": lambda s: s < 65})["limiar 65"]
    assert r["recall_virada"] == 0.5 and r["recall_fim"] == 0.5
    assert r["falso_alarme"] == 1.0
    assert r["lead_falas_mediana"] == 1 and r["lead_segundos_mediana"] == 60.0


def test_denominador_zero_e_none():
    m = _script()
    r = m.medir([([90.0], _c(1), 2)], {"l": lambda s: s < 65})["l"]
    assert r["recall_virada"] is None and r["lead_falas_mediana"] is None


def test_sem_modelos_diz_nao_verificado_e_sai_2(capsys, monkeypatch):
    m = _script()

    def falha():
        raise FileNotFoundError("fusor.joblib ausente")

    monkeypatch.setattr(m, "montar_motor_real", falha)
    assert m.principal([]) == 2
    saida = capsys.readouterr().out
    assert "artefato do gerador" in saida
    assert "não verificado — modelos ausentes" in saida
