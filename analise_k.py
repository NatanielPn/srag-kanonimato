#!/usr/bin/env python3
"""Risco de reidentificação por k-anonimato em microdados abertos do SRAG (SIVEP-Gripe/OpenDataSUS).

Uso:  python analise_k.py ARQUIVO.csv [--saida pasta]
Só conta combinações de atributos. Não grava nenhum registro individual.
"""
import argparse, json, os, sys
import numpy as np, pandas as pd

ENC = ("utf-8", "latin-1")
CANDIDATAS = {  # nome canônico -> nomes possíveis no arquivo
    "sexo": ["CS_SEXO"], "idade": ["NU_IDADE_N"], "tp_idade": ["TP_IDADE"],
    "nasc": ["DT_NASC"], "mun_res": ["CO_MUN_RES", "ID_MN_RESI"],
    "uf_res": ["SG_UF", "CO_UF_RES"], "raca": ["CS_RACA"],
    "sintomas": ["DT_SIN_PRI"], "notific": ["DT_NOTIFIC"],
}

def ler(caminho):
    for enc in ENC:
        try:
            cab = pd.read_csv(caminho, sep=";", dtype=str, encoding=enc, nrows=0)
            if cab.shape[1] <= 5: continue
            usar = [c for nomes in CANDIDATAS.values() for c in nomes if c in cab.columns]
            return pd.read_csv(caminho, sep=";", dtype=str, encoding=enc, usecols=usar, low_memory=False)
        except Exception:
            pass
    sys.exit("Não consegui ler o CSV (tentei separador ';' e UTF-8/Latin-1).")

def achar(df):
    m = {}
    for k, nomes in CANDIDATAS.items():
        for n in nomes:
            if n in df.columns: m[k] = n; break
    return m

def data(s):
    s = s.astype(str).str.strip()
    iso = s.str.match(r"^\d{4}-\d{2}-\d{2}")
    d = pd.to_datetime(s.where(iso).str[:10], errors="coerce", format="%Y-%m-%d")
    return d.fillna(pd.to_datetime(s.where(~iso), errors="coerce", dayfirst=True, format="mixed"))

def preparar(df, m):
    o = pd.DataFrame(index=df.index)
    o["sexo"] = df[m["sexo"]].fillna("NA")
    idade = pd.to_numeric(df[m["idade"]], errors="coerce")
    if "tp_idade" in m:  # 1 dia, 2 mês, 3 ano
        tp = pd.to_numeric(df[m["tp_idade"]], errors="coerce")
        idade = idade.where(tp == 3, 0)
    o["idade"] = idade
    if "mun_res" in m:
        mun = df[m["mun_res"]].fillna("NA").astype(str).str.strip()
        o["mun"] = mun.str[:6]; o["uf"] = mun.str[:2]
    else:
        o["mun"] = "NA"; o["uf"] = df[m.get("uf_res")].fillna("NA") if "uf_res" in m else "NA"
    if "nasc" in m:
        d = data(df[m["nasc"]])
        o["nasc_dia"] = d.dt.strftime("%Y-%m-%d").fillna("NA")
        o["nasc_mes"] = d.dt.strftime("%Y-%m").fillna("NA")
        o["nasc_ano"] = d.dt.strftime("%Y").fillna("NA")
    if "raca" in m: o["raca"] = df[m["raca"]].fillna("NA")
    if "sintomas" in m:
        d = data(df[m["sintomas"]])
        o["dia"] = d.dt.strftime("%Y-%m-%d").fillna("NA")
        o["semana"] = d.dt.strftime("%G-%V").fillna("NA")
        o["mes"] = d.dt.strftime("%Y-%m").fillna("NA")
    return o.dropna(subset=["idade"])

def faixa(idade, passo):
    return (idade // passo * passo).astype(int).astype(str)

def metricas(o, cols, rotulo):
    n = len(o)
    tam = o.groupby(cols, sort=False, observed=True)[cols[0]].transform("size")
    return {
        "cenario": rotulo, "registros": int(n),
        "classes": int(o.groupby(cols, observed=True).ngroups),
        "unicos_pct": round(float(100 * (tam == 1).mean()), 2),
        "k_menor_5_pct": round(100 * (tam < 5).mean(), 2),
        "k_menor_11_pct": round(100 * (tam < 11).mean(), 2),
        "k_minimo": int(tam.min()), "k_mediana": float(tam.median()),
    }

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("csv"); ap.add_argument("--saida", default="resultados")
    a = ap.parse_args(); os.makedirs(a.saida, exist_ok=True)
    df = ler(a.csv); m = achar(df)
    falta = [k for k in ("sexo", "idade") if k not in m]
    if falta: sys.exit(f"Faltam colunas essenciais: {falta}. Colunas do arquivo: {list(df.columns)[:60]}")
    print("Colunas usadas:", m)
    o = preparar(df, m); del df
    res = []
    for nome, passo in (("idade exata", 1), ("faixa 5 anos", 5), ("faixa 10 anos", 10), ("faixa 20 anos", 20)):
        o["i_" + nome] = faixa(o["idade"], passo)
    niveis_idade = ["i_idade exata", "i_faixa 5 anos", "i_faixa 10 anos", "i_faixa 20 anos"]
    cenarios = []
    for ni in niveis_idade:
        base = ni[2:]
        cenarios.append(([ni, "sexo", "mun"], f"sexo + {base} + município"))
        cenarios.append(([ni, "sexo", "uf"], f"sexo + {base} + UF"))
        if "raca" in o: cenarios.append(([ni, "sexo", "mun", "raca"], f"sexo + {base} + município + raça/cor"))
        if "mes" in o: cenarios.append(([ni, "sexo", "mun", "mes"], f"sexo + {base} + município + mês dos sintomas"))
        if "semana" in o: cenarios.append(([ni, "sexo", "mun", "semana"], f"sexo + {base} + município + semana dos sintomas"))
        if "dia" in o: cenarios.append(([ni, "sexo", "mun", "dia"], f"sexo + {base} + município + dia dos sintomas"))
    if "nasc_dia" in o:
        for col, rot in (("nasc_dia", "data de nascimento completa"), ("nasc_mes", "mês/ano de nascimento"), ("nasc_ano", "ano de nascimento")):
            cenarios.append(([col, "sexo", "mun"], f"sexo + {rot} + município"))
            cenarios.append(([col, "sexo", "uf"], f"sexo + {rot} + UF"))
            if "raca" in o: cenarios.append(([col, "sexo", "mun", "raca"], f"sexo + {rot} + município + raça/cor"))
            if "semana" in o: cenarios.append(([col, "sexo", "mun", "semana"], f"sexo + {rot} + município + semana dos sintomas"))
    for cols, rot in cenarios:
        res.append(metricas(o, cols, rot)); print(res[-1])
    pd.DataFrame(res).to_csv(os.path.join(a.saida, "cenarios.csv"), index=False)
    # efeito do tamanho do município (registros por município, tercis) no cenário básico
    base = ["i_faixa 5 anos", "sexo", "mun"]
    tam = o.groupby(base, observed=True)["sexo"].transform("size")
    por_mun = o.groupby("mun")["sexo"].transform("size")
    q = pd.qcut(por_mun.rank(method="first"), 3, labels=["municípios com poucos casos", "médios", "com muitos casos"])
    tab = pd.DataFrame({"grupo": q, "unico": tam == 1}).groupby("grupo", observed=True)["unico"].agg(["mean", "size"])
    tab["mean"] = (100 * tab["mean"]).round(2); tab.columns = ["unicos_pct", "registros"]
    tab.to_csv(os.path.join(a.saida, "unicos_por_tamanho_municipio.csv"))
    # distribuição de k (cenário básico) para figura
    dist = pd.cut(tam, [0, 1, 4, 10, 50, np.inf], labels=["k=1", "k=2–4", "k=5–10", "k=11–50", "k>50"]).value_counts(normalize=True).sort_index()
    (100 * dist).round(2).to_csv(os.path.join(a.saida, "distribuicao_k.csv"), header=["pct_registros"])
    json.dump({"colunas": m, "n": int(len(o))}, open(os.path.join(a.saida, "meta.json"), "w"), ensure_ascii=False)
    print("Pronto. Veja a pasta", a.saida)

if __name__ == "__main__":
    main()
