import time, json, statistics as S
import numpy as np, pandas as pd
from kanon import *

def tempo(f, reps=5):
    f()                                   # aquecimento
    ts = []
    for _ in range(reps):
        t = time.perf_counter(); r = f(); ts.append(time.perf_counter() - t)
    return r, S.mean(ts), (S.stdev(ts) if len(ts) > 1 else 0.0)

d = carregar(); niv = construir_niveis(d); n = len(d)
av = Avaliador(niv, n)
linhas, trajetoria = [], None
for K in (2, 5, 11):
    for supr in (0.0, 0.01, 0.05):
        (lg, vg, passos), tg, sg = tempo(lambda: guloso(av, K, supr))
        chamadas_g = len(passos) and None
        av.chamadas = 0; guloso(av, K, supr); cg = av.chamadas
        (le, ve), te, se = tempo(lambda: exaustivo(av, K, supr))
        av.chamadas = 0; exaustivo(av, K, supr); ce = av.chamadas
        linhas.append({"K": K, "supressao_max_pct": 100 * supr,
            "guloso_niveis": str(dict(zip(ATTRS, lg))), "guloso_perda": round(perda(lg), 4), "guloso_violadores_pct": round(100 * vg / n, 3),
            "guloso_avaliacoes": cg, "guloso_tempo_s": round(tg, 4), "guloso_sd": round(sg, 4),
            "otimo_niveis": str(dict(zip(ATTRS, le))), "otimo_perda": round(perda(le), 4), "otimo_violadores_pct": round(100 * ve / n, 3),
            "exaustivo_avaliacoes": ce, "exaustivo_tempo_s": round(te, 3), "exaustivo_sd": round(se, 3),
            "diferenca_de_perda": round(perda(lg) - perda(le), 4), "guloso_achou_otimo": bool(abs(perda(lg) - perda(le)) < 1e-12)})
        print(linhas[-1]["K"], linhas[-1]["supressao_max_pct"], linhas[-1]["guloso_niveis"], linhas[-1]["otimo_niveis"], linhas[-1]["guloso_tempo_s"], linhas[-1]["exaustivo_tempo_s"], flush=True)
        if K == 5 and supr == 0.01: trajetoria = passos
pd.DataFrame(linhas).to_csv("resultados/item1_guloso_vs_exaustivo.csv", index=False)
pd.DataFrame([dict(zip(["passo"] + ATTRS, [i, *p])) | {"perda": round(perda(p), 4), "violadores_pct": round(100 * av.violadores(p, 5) / n, 3)} for i, p in enumerate(trajetoria)]).to_csv("resultados/item1_trajetoria_K5_s1.csv", index=False)
# descrição da solução escolhida (K=5, 1% de supressão) e escala
lv = tuple(int(x) for x in pd.read_csv("resultados/item1_trajetoria_K5_s1.csv")[ATTRS].iloc[-1])
json.dump(descrever(av, lv), open("resultados/item1_solucao_K5_s1.json", "w"), ensure_ascii=False)
esc = []
rng = np.random.default_rng(2026)
for m in (25000, 50000, 100000, 200000, n):
    idx = np.sort(rng.choice(n, m, replace=False))
    sub = {k: (v[0][idx], v[1]) for k, v in niv.items()}
    a2 = Avaliador(sub, m)
    (_, _, _), tg, sg = tempo(lambda: guloso(a2, 5, 0.01)); (_, _), te, se = tempo(lambda: exaustivo(a2, 5, 0.01))
    esc.append({"registros": m, "guloso_s": round(tg, 4), "guloso_sd": round(sg, 4), "exaustivo_s": round(te, 3), "exaustivo_sd": round(se, 3), "razao": round(te / tg, 1)})
    print(esc[-1], flush=True)
pd.DataFrame(esc).to_csv("resultados/item1_escala.csv", index=False)
print("fim")
