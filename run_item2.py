"""Item 2: o mesmo cálculo (tamanho das classes de equivalência de sexo + data de nascimento + município)
em 5 implementações. Entrada comum: DataFrame com 3 colunas de texto já carregadas na memória."""
import time, sqlite3, statistics as S, itertools, collections
import numpy as np, pandas as pd
from kanon import carregar

d = carregar()
d = pd.DataFrame({"sexo": d["CS_SEXO"], "nasc": d["DT_NASC"].str[:10], "mun": d["CO_MUN_RES"]})

def hist(sizes):                       # histograma {tamanho da classe: nº de classes}
    return dict(sorted(collections.Counter(sizes).items()))

def impl_pandas(df):
    return hist(df.groupby(["sexo", "nasc", "mun"], sort=False).size().tolist())

def impl_numpy(df):
    chave = np.zeros(len(df), dtype=np.int64)
    for c in ("sexo", "nasc", "mun"):
        cod, uniq = pd.factorize(df[c], sort=False)
        chave = chave * len(uniq) + cod
    _, cont = np.unique(chave, return_counts=True)
    return hist(cont.tolist())

def impl_dict(df):
    return hist(collections.Counter(zip(df["sexo"].tolist(), df["nasc"].tolist(), df["mun"].tolist())).values())

def impl_sort(df):
    t = sorted(zip(df["sexo"].tolist(), df["nasc"].tolist(), df["mun"].tolist()))
    return hist(sum(1 for _ in g) for _, g in itertools.groupby(t))

def impl_sqlite(df):
    con = sqlite3.connect(":memory:")
    con.execute("create table t(sexo text, nasc text, mun text)")
    con.executemany("insert into t values (?,?,?)", zip(df["sexo"].tolist(), df["nasc"].tolist(), df["mun"].tolist()))
    r = [x[0] for x in con.execute("select count(*) from t group by sexo, nasc, mun")]
    con.close(); return hist(r)

IMPL = [("pandas (groupby, hash)", impl_pandas), ("numpy (ordenação de chave inteira)", impl_numpy),
        ("Python puro (dicionário/Counter)", impl_dict), ("Python puro (sorted + groupby)", impl_sort), ("SQLite (GROUP BY)", impl_sqlite)]
rng = np.random.default_rng(2026); n = len(d); linhas = []
for m in (10000, 50000, 100000, n):
    sub = d.iloc[np.sort(rng.choice(n, m, replace=False))].reset_index(drop=True) if m < n else d
    ref = None
    for nome, f in IMPL:
        r = f(sub)                                   # aquecimento + conferência do resultado
        ref = ref or r
        assert r == ref, f"resultado diferente em {nome} (n={m})"
        ts = []
        for _ in range(5):
            t = time.perf_counter(); f(sub); ts.append(time.perf_counter() - t)
        linhas.append({"registros": m, "implementacao": nome, "media_s": round(S.mean(ts), 4), "dp_s": round(S.stdev(ts), 4),
                       "classes": sum(ref.values()), "classes_unicas": ref.get(1, 0)})
        print(linhas[-1], flush=True)
pd.DataFrame(linhas).to_csv("resultados/item2_implementacoes.csv", index=False)
print("fim")
