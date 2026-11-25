"""Comparação exploratória de primeiras tentativas isoladas e conjuntas."""
import pandas as pd

LIMIAR_ALTO, LIMIAR_BAIXO, LIMIAR_INTEGRACAO = .70, .50, .25
MIN_INDIVIDUAIS, MIN_CONJUNTAS = 4, 2


def primeiras_tentativas(respostas, questoes):
    dados = respostas.merge(questoes, on='questao_id', validate='many_to_one')
    dados['habilidade_secundaria'] = dados.habilidade_secundaria.fillna('')
    dados['respondida_em'] = pd.to_datetime(dados.respondida_em)
    return dados.sort_values('respondida_em', kind='stable').drop_duplicates(['aluno_id','questao_id'])


def classificar_relacao(a,b,conjunto,n_a,n_b,n_ab):
    if min(n_a,n_b) < MIN_INDIVIDUAIS or n_ab < MIN_CONJUNTAS or any(pd.isna(x) for x in (a,b,conjunto)):
        return 'Evidencia insuficiente'
    diferenca = (a+b)/2-conjunto
    if conjunto < LIMIAR_BAIXO:
        if a>=LIMIAR_ALTO and b>=LIMIAR_ALTO and diferenca>=LIMIAR_INTEGRACAO:
            return 'Possivel dificuldade de integracao'
        if a>=LIMIAR_ALTO and b<LIMIAR_BAIXO:
            return 'Possivel dificuldade na habilidade B'
        if b>=LIMIAR_ALTO and a<LIMIAR_BAIXO:
            return 'Possivel dificuldade na habilidade A'
        if a<LIMIAR_BAIXO and b<LIMIAR_BAIXO:
            return 'Possivel dificuldade nas duas habilidades'
    if min(a,b,conjunto)>=LIMIAR_ALTO:
        return 'Bom desempenho individual e conjunto'
    if conjunto>=LIMIAR_ALTO and min(a,b)<LIMIAR_BAIXO:
        return 'Desempenho atipico'
    return 'Resultado inconclusivo'


def analisar_relacoes(respostas, questoes):
    dados = primeiras_tentativas(respostas,questoes)
    individuais = dados[dados.habilidade_secundaria.eq('')]
    conjuntas = dados[dados.habilidade_secundaria.ne('')]
    pares = sorted({tuple(sorted((r.habilidade_principal,r.habilidade_secundaria)))
        for r in questoes.fillna('').itertuples() if r.habilidade_secundaria})
    linhas=[]
    for aluno in sorted(respostas.aluno_id.unique()):
        ind=individuais[individuais.aluno_id.eq(aluno)]
        con=conjuntas[conjuntas.aluno_id.eq(aluno)]
        for a,b in pares:
            sa=ind[ind.habilidade_principal.eq(a)]
            sb=ind[ind.habilidade_principal.eq(b)]
            sab=con[(con.habilidade_principal.eq(a)&con.habilidade_secundaria.eq(b)) |
                    (con.habilidade_principal.eq(b)&con.habilidade_secundaria.eq(a))]
            x,y,z=(s.acertou.mean() for s in (sa,sb,sab))
            na,nb,nab=map(len,(sa,sb,sab))
            status=classificar_relacao(x,y,z,na,nb,nab)
            linhas.append(dict(aluno_id=aluno,habilidade_a=a,habilidade_b=b,
                questoes_distintas_a=na,questoes_distintas_b=nb,questoes_distintas_ab=nab,
                acertos_a=int(sa.acertou.sum()),acertos_b=int(sb.acertou.sum()),acertos_ab=int(sab.acertou.sum()),
                desempenho_a=x,desempenho_b=y,desempenho_conjunto=z,
                diferenca_integracao=(x+y)/2-z,diagnostico=status,
                nivel_evidencia='insuficiente' if status=='Evidencia insuficiente' else 'preliminar'))
    colunas='aluno_id habilidade_a habilidade_b questoes_distintas_a questoes_distintas_b questoes_distintas_ab acertos_a acertos_b acertos_ab desempenho_a desempenho_b desempenho_conjunto diferenca_integracao diagnostico nivel_evidencia'.split()
    return pd.DataFrame(linhas,columns=colunas)


if __name__ == '__main__':
    from pathlib import Path
    raiz=Path(__file__).resolve().parents[1]
    resultado=analisar_relacoes(pd.read_csv(raiz/'data/respostas.csv'),pd.read_csv(raiz/'data/questoes.csv'))
    (raiz/'outputs').mkdir(exist_ok=True)
    resultado.to_csv(raiz/'outputs/desempenho_relacional.csv',index=False,encoding='utf-8-sig')
    print(f'Analises relacionais: {len(resultado)}')
