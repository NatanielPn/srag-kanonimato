"""Generalização guiada por k-anonimato: algoritmo guloso e busca exaustiva no reticulado.

Quase-identificadores e hierarquias (nível 0 = valor original; último nível = '*', suprimido):
  nasc : dia -> mês -> ano -> faixa de 5 anos -> faixa de 10 -> faixa de 20 -> *   (altura 6)
  mun  : município (6 díg.) -> UF -> região -> *                                   (altura 3)
  sint : dia dos sintomas -> semana ISO -> mês -> *                                (altura 3)
  sexo : sexo -> *                                                                 (altura 1)
"""
import time, itertools
import numpy as np, pandas as pd

ATTRS = ["nasc", "mun", "sint", "sexo"]
ALTURA = {"nasc": 6, "mun": 3, "sint": 3, "sexo": 1}
ARQ = "INFLUD24-23-03-2026.csv"
COLS = ["CS_SEXO", "DT_NASC", "CO_MUN_RES", "DT_SIN_PRI"]


def carregar(caminho=ARQ):
    d = pd.read_csv(caminho, sep=";", usecols=COLS, dtype=str)
    d = d.fillna("NA")
    return d


def construir_niveis(d):
    """Para cada atributo e nível, um vetor int32 de códigos (factorize). Retorna dict[(attr,nivel)] -> (codes, cardinalidade)."""
    nasc = pd.to_datetime(d["DT_NASC"].str[:10], errors="coerce")
    ano = nasc.dt.year.fillna(0).astype(int)
    sint = pd.to_datetime(d["DT_SIN_PRI"].str[:10], errors="coerce")
    mun = d["CO_MUN_RES"].astype(str).str[:6]
    vis = {
        ("nasc", 0): nasc.dt.strftime("%Y-%m-%d").fillna("NA"),
        ("nasc", 1): nasc.dt.strftime("%Y-%m").fillna("NA"),
        ("nasc", 2): ano.astype(str),
        ("nasc", 3): (ano // 5 * 5).astype(str),
        ("nasc", 4): (ano // 10 * 10).astype(str),
        ("nasc", 5): (ano // 20 * 20).astype(str),
        ("nasc", 6): pd.Series("*", index=d.index),
        ("mun", 0): mun,
        ("mun", 1): mun.str[:2],
        ("mun", 2): mun.str[:1],
        ("mun", 3): pd.Series("*", index=d.index),
        ("sint", 0): sint.dt.strftime("%Y-%m-%d").fillna("NA"),
        ("sint", 1): sint.dt.strftime("%G-%V").fillna("NA"),
        ("sint", 2): sint.dt.strftime("%Y-%m").fillna("NA"),
        ("sint", 3): pd.Series("*", index=d.index),
        ("sexo", 0): d["CS_SEXO"],
        ("sexo", 1): pd.Series("*", index=d.index),
    }
    out = {}
    for k, s in vis.items():
        codes, uniq = pd.factorize(s, sort=False)
        out[k] = (codes.astype(np.int64), len(uniq))
    return out


class Avaliador:
    """Avalia um vetor de níveis: conta classes de equivalência (ordenação + contagem em numpy)."""
    def __init__(self, niveis, n):
        self.niveis, self.n, self.chamadas = niveis, n, 0

    def contagens(self, lv):
        self.chamadas += 1
        chave = np.zeros(self.n, dtype=np.int64)
        for a, l in zip(ATTRS, lv):
            cod, card = self.niveis[(a, l)]
            chave = chave * card + cod
        _, cont = np.unique(chave, return_counts=True)
        return cont

    def violadores(self, lv, K):
        c = self.contagens(lv)
        return int(c[c < K].sum())


def perda(lv):
    """Perda de generalização (precisão de Sweeney, 1 - Prec): média de nível/altura."""
    return float(np.mean([l / ALTURA[a] for a, l in zip(ATTRS, lv)]))


def viavel(viol, n, supr):
    return viol / n <= supr


def guloso(av, K, supr):
    """Sobe, a cada passo, o atributo que mais reduz registros violadores por unidade de perda adicional."""
    lv = [0] * len(ATTRS)
    passos = [tuple(lv)]
    viol = av.violadores(lv, K)
    while not viavel(viol, av.n, supr):
        melhor, mscore, mviol = None, -1.0, None
        for i, a in enumerate(ATTRS):
            if lv[i] >= ALTURA[a]:
                continue
            cand = lv.copy(); cand[i] += 1
            v = av.violadores(cand, K)
            score = (viol - v) * ALTURA[a]          # reduz violadores / (1/altura)
            if score > mscore or (score == mscore and v < mviol):
                melhor, mscore, mviol = i, score, v
        lv[melhor] += 1; viol = mviol; passos.append(tuple(lv))
    return tuple(lv), viol, passos


def exaustivo(av, K, supr):
    """Percorre todo o reticulado de generalizações e devolve a solução de menor perda (desempate: menos violadores)."""
    melhor = None
    for lv in itertools.product(*[range(ALTURA[a] + 1) for a in ATTRS]):
        v = av.violadores(lv, K)
        if viavel(v, av.n, supr):
            chave = (perda(lv), v)
            if melhor is None or chave < melhor[0]:
                melhor = (chave, lv, v)
    return melhor[1], melhor[2]


def descrever(av, lv):
    c = av.contagens(lv)
    return {"niveis": dict(zip(ATTRS, lv)), "perda": round(perda(lv), 4),
            "classes": int(len(c)), "k_minimo": int(c.min()), "tamanho_medio_classe": round(float(av.n / len(c)), 1)}
