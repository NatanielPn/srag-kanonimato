# Diário de processo: privacidade e algoritmos no SRAG

Formato: data/hora, o que foi feito, por quê, e resultado. Nada é apagado; correções entram como novas entradas.

## 17/11/2026 – Etapa 0: dados e ambiente
- Dados: INFLUD24-23-03-2026.csv (OpenDataSUS, SRAG 2024, "banco vivo" de 23/03/2026), baixado em 17/11/2026 pelo autor. 267.986 registros, 194 colunas, UTF-8, separador ";".
- Dicionário de dados 2019-2025 baixado na mesma pasta (não lido por mim: o conteúdo não pôde ser aberto no ambiente de trabalho).
- Colunas usadas: CS_SEXO, DT_NASC, NU_IDADE_N, TP_IDADE, CS_RACA, CO_MUN_RES, SG_UF, DT_SIN_PRI.
- Análise 1 (analise_k.py, 8 s): percentual de registros únicos por cenário. Achado principal: sexo + data de nascimento + município = 78,67% únicos. Conferido por um segundo cálculo independente (78,62%; a diferença vem de 78 registros sem município, que o script conta como categoria própria).
- Decisão (15:04): reforçar o núcleo algorítmico por causa da regra do barema ("somente serão avaliadas as atividades na área do concurso"). Itens: (1) algoritmo guloso de generalização com busca exaustiva de referência; (2) comparação de implementações do cálculo de classes de equivalência.
- Ambiente (VM do Claude no computador do autor): Python 3.10.12, numpy 2.2.6, pandas 2.3.3, SQLite 3.37.2, Linux x86_64, 2 núcleos, 3,9 GB de RAM. SHA-256 do CSV (16 primeiros caracteres): b516f6eae61203da.

## 17/11/2026 – Etapa 1: algoritmo guloso de generalização (kanon.py, run_item1.py)
- Modelo: 4 quase-identificadores com hierarquias de generalização: data de nascimento (dia, mês, ano, faixa de 5, 10 e 20 anos, suprimido; altura 6), município (município, UF, região, suprimido; altura 3), data dos primeiros sintomas (dia, semana ISO, mês, suprimido; altura 3) e sexo (original, suprimido; altura 1). Reticulado com 7 x 4 x 4 x 2 = 224 combinações.
- Perda de informação: 1 - Prec de Sweeney = média de (nível / altura) dos 4 atributos. Restrição: no máximo uma fração s de registros em classes com tamanho menor que K (supressão).
- Guloso: parte do nível 0 e, a cada passo, sobe o atributo que reduz mais registros violadores por unidade de perda adicional, até ser viável. Referência: busca exaustiva nos 224 nós (solução ótima para a mesma perda).
- Cada avaliação de um nó = ordenar uma chave inteira de 267.986 registros e contar (np.unique). Tempos: 1 aquecimento + 5 repetições, média ± desvio.
- Resultado (K = 2, 5, 11; supressão 0, 1 e 5%): o guloso usou de 21 a 44 avaliações contra 224 da busca exaustiva, e levou cerca de 0,14 s contra 0,89 s (6,3 vezes mais rápido). Achou a mesma perda do ótimo em 6 dos 9 cenários; nos outros 3, ficou 0,042 a 0,083 acima (de 0 a 1 em escala de perda).
- Observação: em empates de perda, o ótimo da busca exaustiva tem menos registros violadores que o guloso (ex.: K = 5, s = 1%: 0,048% contra 0,675%).
- Escala (K = 5, s = 1%): o tempo cresce de forma linear de 25 mil a 268 mil registros para os dois (guloso 0,013 s a 0,141 s; exaustivo 0,079 s a 0,888 s), e a razão fica em torno de 6.
- Solução do guloso para K = 5 e s = 1%: data de nascimento em faixas de 10 anos, município generalizado para região, sintomas por semana e sexo mantido; 5.976 classes, tamanho médio 44,8. Isto é uma perda grande de detalhe geográfico, o que ilustra o custo de privacidade.
- Arquivos: resultados/item1_guloso_vs_exaustivo.csv, item1_trajetoria_K5_s1.csv, item1_solucao_K5_s1.json, item1_escala.csv.

## 17/11/2026 – Etapa 2: comparação de implementações (run_item2.py)
- Operação: calcular o tamanho de todas as classes de equivalência de sexo + data de nascimento + município. Entrada comum: DataFrame com 3 colunas de texto na memória; o tempo inclui a conversão necessária em cada implementação.
- Implementações: (a) pandas groupby (hash); (b) numpy (códigos inteiros + ordenação); (c) Python puro com dicionário (Counter); (d) Python puro com sorted + groupby; (e) SQLite (inserção + GROUP BY).
- Conferência: o histograma de tamanhos de classe foi idêntico nas 5 implementações em todos os tamanhos (verificado por assert). Com 267.986 registros: 233.954 classes, 210.825 delas únicas (78,67%), o que bate com a Análise 1.
- Tamanhos: 10 mil, 50 mil, 100 mil e 267.986 registros; 1 aquecimento + 5 repetições, média ± desvio.
- Resultado com 267.986 registros (média em s): numpy 0,034; pandas 0,042; dicionário em Python puro 0,053; sorted + groupby 0,29; SQLite 0,42. O dicionário em Python puro ficou na mesma ordem de grandeza do pandas (1,3 vez mais lento), e a versão por ordenação ficou 7 vezes mais lenta que o pandas.
- Observação: dos 10 mil aos 268 mil registros (26,8 vezes mais dados), os tempos cresceram de 18 a 35 vezes (numpy e pandas 18; dicionário 33; sorted 35; SQLite 29).

## 17/11/2026 – Etapa 3: verificação independente
- Refiz o cálculo das soluções do guloso (K = 5, s = 1%) e do ótimo por um caminho diferente (pandas groupby sobre colunas de texto, sem usar kanon.py). Guloso: 0,675% de registros violadores (1.808); ótimo: 0,048% (129). Igual ao resultado do algoritmo.
- Pendente: reescrever o rascunho do artigo com foco algorítmico; conferir referências marcadas [CONFERIR].

## 17/11/2026 – Etapa 4: rascunho v0.2
- Reescrito o rascunho com foco algorítmico (título, Resumo de 203 palavras, Introdução, Métodos, Resultados com as Tabelas 1 a 3). Discussão, Limitações e Conclusão ficaram como esqueleto.
- Revisão de afirmações: tirei uma frase que dizia "99% dos registros únicos ou raros" (não era sustentada) e troquei por "no máximo 1% dos registros em classes com menos de 5"; a razão de tempo guloso/exaustivo passou a ser descrita como de 5 a 8 vezes (6,3 vezes no tamanho completo com k = 5 e s = 1%).
- Referências a conferir: Sweeney (2002a e 2002b), Meyerson e Williams (2004), LeFevre et al. (2005), estudo de Portugal (PMC8171945), PeNSE (UFMG), Alvim et al. (periódico, ano), LGPD.
- Pendente: escolher a chamada e o modelo; criar o repositório; figuras (trajetória do guloso; tempo por implementação); escrever Discussão, Limitações e Conclusão; busca mais ampla sobre ineditismo.
