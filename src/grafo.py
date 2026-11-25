import pandas as pd

def construir_arestas(questoes):
    """Cria arestas não direcionadas a partir de principal/secundária.

    O peso é a quantidade de questões em que o par aparece, independente
    da direção principal/secundária.
    """
    pares = []
    for _, row in questoes.dropna(subset=["habilidade_secundaria"]).iterrows():
        a = str(row["habilidade_principal"])
        b = str(row["habilidade_secundaria"])
        if not b.strip():
            continue
        if a == b:
            continue
        par = tuple(sorted((a, b)))
        pares.append({"origem": par[0], "destino": par[1], "questao_id": row["questao_id"]})

    if not pares:
        return pd.DataFrame(columns=["origem", "destino", "peso", "questoes"])

    df = pd.DataFrame(pares)
    return (df.groupby(["origem", "destino"])
              .agg(peso=("questao_id", "count"),
                   questoes=("questao_id", lambda x: ", ".join(sorted(x))))
              .reset_index())


def calcular_prioridade(estimativas, arestas, lam=0.25):
    """Pontuação experimental de prioridade; não altera o BKT.

    prioridade = (1 - domínio próprio) + lambda * média ponderada
                 das lacunas dos vizinhos.
    """
    saida = estimativas.copy()
    saida["prioridade_grafo"] = 1.0 - saida["dominio_bkt"]

    if arestas.empty:
        return saida

    for aluno in saida["aluno_id"].unique():
        idx = saida["aluno_id"] == aluno
        mapa = saida.loc[idx].set_index("habilidade_id")["dominio_bkt"].to_dict()

        for i in saida.loc[idx].index:
            h = saida.at[i, "habilidade_id"]
            vizinhos = []
            for _, e in arestas.iterrows():
                if e["origem"] == h:
                    vizinhos.append((e["destino"], float(e["peso"])))
                elif e["destino"] == h:
                    vizinhos.append((e["origem"], float(e["peso"])))

            if vizinhos:
                soma_pesos = sum(p for _, p in vizinhos)
                lacuna_vizinhos = sum((1.0 - mapa[v]) * p for v, p in vizinhos) / soma_pesos
                saida.at[i, "prioridade_grafo"] = (
                    (1.0 - mapa[h]) + lam * lacuna_vizinhos
                )
    return saida


def salvar_imagem_grafo(habilidades, arestas, caminho):
    try:
        import networkx as nx
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Para gerar a imagem do grafo, instale networkx e matplotlib.")
        return

    G = nx.Graph()
    nomes = habilidades.set_index("habilidade_id")["habilidade"].to_dict()
    for h in habilidades["habilidade_id"]:
        G.add_node(h)
    for _, e in arestas.iterrows():
        G.add_edge(e["origem"], e["destino"], weight=int(e["peso"]))

    pos = nx.spring_layout(G, seed=7, k=1.15)
    plt.figure(figsize=(11, 7))
    nx.draw_networkx_nodes(G, pos, node_size=2600, node_color="#d9ecff",
                           edgecolors="#17365d", linewidths=1.8)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")
    nx.draw_networkx_edges(G, pos, width=1.5, edge_color="#52657a")
    labels = {(u, v): f'{d["weight"]}' for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels, font_size=9)
    plt.title("Grafo de coocorrência entre micro-habilidades\nPeso = número de questões compartilhadas")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(caminho, dpi=180, bbox_inches="tight")
    plt.close()
