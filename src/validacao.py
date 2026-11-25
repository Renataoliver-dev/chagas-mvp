"""Avaliação preditiva sequencial em questões individuais inéditas para o aluno."""
import math
import pandas as pd
from bkt import atualizar_bkt, P_L0, P_S

MIN_HISTORICO = 3
JANELA = 3
MODELOS = ('taxa_acumulada', 'media_movel', 'bkt')


def prever_bkt(historico, alternativas):
    """Probabilidade de acertar o próximo item, não de dominar a habilidade."""
    p = atualizar_bkt(historico)
    return p * (1 - P_S) + (1 - p) / alternativas


def gerar_previsoes(respostas, questoes):
    dados = respostas.merge(questoes, on='questao_id', validate='many_to_one')
    dados = dados[dados.habilidade_secundaria.fillna('').eq('')].copy()
    dados['respondida_em'] = pd.to_datetime(dados.respondida_em)
    linhas = []
    for (aluno, hab), grupo in dados.groupby(['aluno_id', 'habilidade_principal']):
        historico, vistas = [], set()
        # Itens com o mesmo horário não podem informar a previsão uns dos outros.
        for instante, lote in grupo.groupby('respondida_em', sort=True):
            previstos = set()
            for item in lote.itertuples():
                if len(vistas) < MIN_HISTORICO or item.questao_id in vistas or item.questao_id in previstos:
                    continue
                previstos.add(item.questao_id)
                ultimas = historico[-JANELA:]
                # Suavização de Laplace evita certezas artificiais de 0% ou 100%.
                acumulada = (1 + sum(x['acertou'] for x in historico)) / (2 + len(historico))
                movel = (1 + sum(x['acertou'] for x in ultimas)) / (2 + len(ultimas))
                linhas.append(dict(aluno_id=aluno, habilidade_id=hab,
                    questao_id=item.questao_id, respondida_em=instante,
                    historico_tentativas=len(historico), historico_distintas=len(vistas),
                    acertou=int(item.acertou), taxa_acumulada=acumulada,
                    media_movel=movel, bkt=prever_bkt(historico, item.alternativas)))
            # Só após prever o lote é permitido observar as respostas.
            for item in lote.itertuples():
                historico.append(dict(acertou=int(item.acertou), alternativas=int(item.alternativas)))
                vistas.add(item.questao_id)
    return pd.DataFrame(linhas, columns=['aluno_id','habilidade_id','questao_id','respondida_em',
        'historico_tentativas','historico_distintas','acertou',*MODELOS])


def avaliar(previsoes):
    """Brier e log loss: menor é melhor. Acurácia: maior é melhor."""
    linhas, calibracao = [], []
    y = previsoes.acertou
    for modelo in MODELOS:
        p = previsoes[modelo].astype(float)
        seguro = p.clip(1e-12, 1-1e-12)
        perdas = [-a*math.log(b)-(1-a)*math.log(1-b) for a,b in zip(y,seguro)]
        linhas.append(dict(modelo=modelo,n_previsoes=len(y),
            brier_score=((p-y)**2).mean(),log_loss=sum(perdas)/len(y) if len(y) else float('nan'),
            acuracia=((p>=.5)==y).mean(),probabilidade_media=p.mean(),taxa_real=y.mean()))
        for i in range(5):
            inferior, superior = i/5, (i+1)/5
            mascara=(p>=inferior)&((p<superior) if i<4 else (p<=superior))
            calibracao.append(dict(modelo=modelo,limite_inferior=inferior,limite_superior=superior,
                n_previsoes=int(mascara.sum()),probabilidade_media=p[mascara].mean(),taxa_real=y[mascara].mean()))
    return pd.DataFrame(linhas),pd.DataFrame(calibracao)
