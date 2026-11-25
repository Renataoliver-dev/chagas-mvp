"""Executa o pipeline completo com os três CSVs originais."""
from pathlib import Path
import argparse
import pandas as pd
from bkt import estimar_todos
from grafo import construir_arestas, calcular_prioridade, salvar_imagem_grafo
from analise_relacional import analisar_relacoes
from diagnostico import gerar_diagnostico
from recomendacao import gerar_recomendacoes
from feedback_formativo import gerar_feedback, salvar_feedback_texto
from validacao import gerar_previsoes, avaliar

ROOT=Path(__file__).resolve().parents[1]


def carregar_dados(pasta):
    h,q,r=[pd.read_csv(pasta/f'{nome}.csv') for nome in ('habilidades','questoes','respostas')]
    campos=[(h,{'habilidade_id','habilidade'}),(q,{'questao_id','habilidade_principal','habilidade_secundaria','alternativas'}),(r,{'aluno_id','questao_id','respondida_em','acertou'})]
    for df,cols in campos:
        if not cols.issubset(df.columns): raise ValueError(f'Colunas ausentes: {cols-set(df.columns)}')
        if df[list(cols-{'habilidade_secundaria'})].isna().any().any(): raise ValueError('Campos obrigatorios ausentes')
    if h.habilidade_id.duplicated().any() or q.questao_id.duplicated().any(): raise ValueError('IDs duplicados em catalogos')
    q['habilidade_secundaria']=q.habilidade_secundaria.fillna('').str.strip()
    if not set(q.habilidade_principal).union(set(q.habilidade_secundaria)-{''}).issubset(set(h.habilidade_id)): raise ValueError('Habilidade desconhecida')
    if q.habilidade_principal.eq(q.habilidade_secundaria).any(): raise ValueError('Habilidade secundaria igual a principal')
    if not set(r.questao_id).issubset(set(q.questao_id)): raise ValueError('Questao desconhecida')
    if not r.acertou.isin([0,1]).all(): raise ValueError('acertou deve ser 0 ou 1')
    if not ((q.alternativas>=2)&(q.alternativas%1==0)).all(): raise ValueError('Numero de alternativas invalido')
    r['respondida_em']=pd.to_datetime(r.respondida_em,errors='raise')
    return h,q,r


def executar(pasta_dados,pasta_saida):
    h,q,r=carregar_dados(pasta_dados)
    pasta_saida.mkdir(parents=True,exist_ok=True)
    estimativas=estimar_todos(r,q,h)
    arestas=construir_arestas(q.replace({'habilidade_secundaria':{'':None}}))
    estimativas=calcular_prioridade(estimativas,arestas)
    relacoes=analisar_relacoes(r,q)
    diagnosticos=gerar_diagnostico(estimativas,r,q,relacoes)
    recomendacoes=gerar_recomendacoes(diagnosticos,relacoes)
    for nome,df in [('estimativas_bkt_grafo',estimativas),('arestas_grafo',arestas),('desempenho_relacional',relacoes),('diagnostico_alunos',diagnosticos),('recomendacoes',recomendacoes)]:
        df.to_csv(pasta_saida/f'{nome}.csv',index=False,encoding='utf-8-sig')
    salvar_imagem_grafo(h,arestas,pasta_saida/'grafo_habilidades.png')
    feedback=gerar_feedback(diagnosticos,relacoes,recomendacoes,r,q)
    previsoes=gerar_previsoes(r,q)
    metricas,calibracao=avaliar(previsoes)
    for nome,df in [('feedback_formativo',feedback),('previsoes_validacao',previsoes),('metricas_validacao',metricas),('calibracao_validacao',calibracao)]:
        df.to_csv(pasta_saida/f'{nome}.csv',index=False,encoding='utf-8-sig')
    salvar_feedback_texto(feedback,pasta_saida/'feedback_alunos')
    return estimativas,arestas,relacoes,diagnosticos,recomendacoes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aluno',default='A03',help='Aluno exibido no terminal')
    parser.add_argument('--data',type=Path,default=ROOT/'data')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs')
    args=parser.parse_args()
    e,g,r,d,rec=executar(args.data,args.output)
    print(f'Pipeline concluido: {len(e)} estimativas, {len(g)} arestas, {len(r)} analises relacionais, {len(d)} diagnosticos, {len(rec)} recomendacoes.')
    print(f'\nDiagnostico de {args.aluno}:')
    print(d[d.aluno_id.eq(args.aluno)][['habilidade_id','dominio_bkt','taxa_individual','diagnostico_individual']].to_string(index=False))
    print('\nPlano de estudo:')
    print(rec[rec.aluno_id.eq(args.aluno)][['ordem','alvo','acao']].to_string(index=False))
    print('\nValidação preditiva (menor Brier e log loss é melhor):')
    print(pd.read_csv(args.output/'metricas_validacao.csv').to_string(index=False))
    print(f'\nArquivos salvos em {args.output}')

if __name__=='__main__': main()
