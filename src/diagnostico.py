"""Cruza evidências individuais e alertas relacionais, sem alterar o BKT."""
import pandas as pd
from analise_relacional import primeiras_tentativas


def classificar_dominio(p):
    if pd.isna(p): return 'Nao estimado'
    if p<.40: return 'Dominio baixo'
    if p<.60: return 'Em desenvolvimento'
    if p<.80: return 'Bom dominio estimado'
    return 'Dominio elevado estimado'


def diagnosticar_habilidade(p,taxa,n):
    if n<4 or pd.isna(p) or pd.isna(taxa): return 'Evidencia insuficiente'
    if p<.40 and taxa<.50: return 'Possivel dificuldade individual'
    if (p>=.80 and taxa<.50) or (p<.40 and taxa>=.70): return 'Divergencia entre BKT e desempenho'
    if p>=.80 and taxa>=.70: return 'Indicadores favoraveis'
    return 'Acompanhar evolucao'


def gerar_diagnostico(estimativas,respostas,questoes,relacoes):
    dados=primeiras_tentativas(respostas,questoes)
    ind=dados[dados.habilidade_secundaria.eq('')]
    evidencias=ind.groupby(['aluno_id','habilidade_principal']).agg(
        questoes_distintas_individuais=('questao_id','nunique'),
        acertos_individuais=('acertou','sum'),taxa_individual=('acertou','mean')).reset_index().rename(columns={'habilidade_principal':'habilidade_id'})
    saida=estimativas.merge(evidencias,on=['aluno_id','habilidade_id'],how='left',validate='one_to_one')
    for c in ['questoes_distintas_individuais','acertos_individuais']:
        saida[c]=saida[c].fillna(0).astype(int)
    saida['classificacao_dominio']=[classificar_dominio(p) if n else 'Prior sem evidencias' for p,n in zip(saida.dominio_bkt,saida.qtd_respostas_bkt)]
    saida['diagnostico_individual']=[diagnosticar_habilidade(p,t,n) for p,t,n in zip(saida.dominio_bkt,saida.taxa_individual,saida.questoes_distintas_individuais)]
    alertas=[]
    for r in saida.itertuples():
        pares=relacoes[(relacoes.aluno_id==r.aluno_id)&((relacoes.habilidade_a==r.habilidade_id)|(relacoes.habilidade_b==r.habilidade_id))]
        textos=[]
        for par in pares.itertuples():
            s=par.diagnostico
            if s in ('Evidencia insuficiente','Resultado inconclusivo','Bom desempenho individual e conjunto'): continue
            if s=='Possivel dificuldade na habilidade A': s=f'Possivel dificuldade em {par.habilidade_a}'
            if s=='Possivel dificuldade na habilidade B': s=f'Possivel dificuldade em {par.habilidade_b}'
            textos.append(f'{par.habilidade_a}+{par.habilidade_b}: {s} (preliminar)')
        alertas.append(' | '.join(textos) or 'Nenhum alerta identificado; nao significa dominio')
    saida['alertas_relacionais']=alertas
    return saida
