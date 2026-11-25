"""Plano de estudo por aluno: revisão, investigação e integração."""
import pandas as pd


def gerar_recomendacoes(diagnosticos,relacoes):
    linhas=[]
    for r in diagnosticos.itertuples():
        d=r.diagnostico_individual
        if d=='Evidencia insuficiente':
            etapa,acao,motivo=1,'Responder novas questoes individuais','Poucas questoes distintas; nao concluir dominio.'
        elif d=='Possivel dificuldade individual' or (r.taxa_individual<.50 and d!='Divergencia entre BKT e desempenho'):
            etapa,acao,motivo=1,'Revisar fundamentos e praticar questoes individuais','Baixo desempenho individual observado.'
        elif d=='Divergencia entre BKT e desempenho':
            etapa,acao,motivo=1,'Reavaliar com questoes novas','Indicadores divergentes; investigar antes de concluir.'
        elif d=='Indicadores favoraveis':
            etapa,acao,motivo=3,'Manter revisao periodica','Indicadores individuais favoraveis, ainda nao validados.'
        else:
            etapa,acao,motivo=2,'Praticar questoes individuais e acompanhar evolucao','Indicadores ainda nao conclusivos.'
        linhas.append(dict(aluno_id=r.aluno_id,alvo=r.habilidade_id,descricao=r.habilidade,
            tipo='individual',etapa=etapa,prioridade_grafo=r.prioridade_grafo,acao=acao,motivo=motivo))
    nomes=diagnosticos.drop_duplicates('habilidade_id').set_index('habilidade_id').habilidade.to_dict()
    for r in relacoes.itertuples():
        s=r.diagnostico
        if s in ('Bom desempenho individual e conjunto','Resultado inconclusivo'): continue
        if s=='Evidencia insuficiente':
            etapa,acao=2,'Coletar mais evidencias individuais e conjuntas com questoes novas'
        elif s=='Possivel dificuldade de integracao':
            etapa,acao=2,'Praticar aplicacao conjunta das duas habilidades'
        elif s=='Desempenho atipico':
            etapa,acao=2,'Reavaliar habilidades isoladas e conjuntas com questoes novas'
        else:
            etapa,acao=2,'Praticar questoes conjuntas depois da revisao dos fundamentos'
        alvo=f'{r.habilidade_a}+{r.habilidade_b}'
        motivo=s.replace('habilidade A',r.habilidade_a).replace('habilidade B',r.habilidade_b)
        linhas.append(dict(aluno_id=r.aluno_id,alvo=alvo,descricao=f'{nomes[r.habilidade_a]} + {nomes[r.habilidade_b]}',
            tipo='relacional',etapa=etapa,prioridade_grafo=float('nan'),acao=acao,
            motivo=f'{motivo}; {r.acertos_ab}/{r.questoes_distintas_ab} acertos conjuntos. Evidencia {r.nivel_evidencia}.'))
    df=pd.DataFrame(linhas).sort_values(['aluno_id','etapa','prioridade_grafo','alvo'],ascending=[True,True,False,True],na_position='last').reset_index(drop=True)
    df.insert(1,'ordem',df.groupby('aluno_id').cumcount()+1)
    return df
