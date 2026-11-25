"""Feedback explicável: observações, interpretação, ação e limites separados."""
import pandas as pd
from analise_relacional import primeiras_tentativas


def _taxa(acertos, n):
    return f'{acertos}/{n} ({acertos/n:.1%})' if n else 'sem questões respondidas'


def gerar_feedback(diagnosticos, relacoes, recomendacoes, respostas, questoes):
    dados = primeiras_tentativas(respostas, questoes)
    catalogo = questoes.copy()
    catalogo["habilidade_secundaria"] = catalogo.habilidade_secundaria.fillna("")
    linhas = []
    for rec in recomendacoes.itertuples(index=False):
        aluno = dados[dados.aluno_id.eq(rec.aluno_id)]
        if rec.tipo == 'individual':
            d = diagnosticos[(diagnosticos.aluno_id==rec.aluno_id)&(diagnosticos.habilidade_id==rec.alvo)].iloc[0]
            itens = aluno[aluno.habilidade_principal.eq(rec.alvo)&aluno.habilidade_secundaria.eq('')]
            candidatos = catalogo[catalogo.habilidade_principal.eq(rec.alvo)&catalogo.habilidade_secundaria.eq('')]
            n, a = len(itens), int(itens.acertou.sum())
            evidencia = f'Primeiras tentativas isoladas: {_taxa(a,n)}. '
            if d.qtd_respostas_bkt:
                evidencia += f'Domínio estimado pelo BKT: {d.dominio_bkt:.1%}, com {d.qtd_respostas_bkt} tentativas individuais.'
            else:
                evidencia += 'BKT sem evidências individuais; apenas probabilidade inicial.'
            status=d.diagnostico_individual
            if status=='Evidencia insuficiente':
                interpretacao='Ainda não há dados suficientes para concluir sobre seu domínio.'
            elif status=='Divergencia entre BKT e desempenho':
                interpretacao='O histórico sequencial e os acertos iniciais divergem. É necessário reavaliar antes de concluir.'
            elif status=='Possivel dificuldade individual' or (n>=4 and a/n<.5):
                interpretacao='Há sinais de dificuldade nesta habilidade; o histórico não identifica o erro conceitual específico.'
            elif status=='Indicadores favoraveis':
                interpretacao='Os indicadores são favoráveis, mas não garantem domínio em outros contextos.'
            else:
                interpretacao='Os indicadores ainda não permitem uma conclusão forte; acompanhe sua evolução.'
            proximo=f'{rec.acao}: {rec.descricao}. Depois, confira o desempenho em questões inéditas da mesma habilidade.'
            limite='Não temos enunciado, alternativa escolhida ou raciocínio; não é possível afirmar a causa exata do erro.'
        else:
            a_id,b_id=rec.alvo.split('+')
            d=relacoes[(relacoes.aluno_id==rec.aluno_id)&(relacoes.habilidade_a==a_id)&(relacoes.habilidade_b==b_id)].iloc[0]
            itens=aluno[((aluno.habilidade_principal==a_id)&(aluno.habilidade_secundaria==b_id))|((aluno.habilidade_principal==b_id)&(aluno.habilidade_secundaria==a_id))]
            candidatos = catalogo[((catalogo.habilidade_principal==a_id)&(catalogo.habilidade_secundaria==b_id))|((catalogo.habilidade_principal==b_id)&(catalogo.habilidade_secundaria==a_id))]
            evidencia=(f'{a_id} isolada: {_taxa(d.acertos_a,d.questoes_distintas_a)}; '
                f'{b_id} isolada: {_taxa(d.acertos_b,d.questoes_distintas_b)}; '
                f'conjuntas: {_taxa(d.acertos_ab,d.questoes_distintas_ab)}.')
            interpretacao=(d.diagnostico.replace('habilidade A',a_id).replace('habilidade B',b_id)+'. '
                + ('Evidências insuficientes.' if d.nivel_evidencia=='insuficiente' else 'Sinal preliminar, não diagnóstico causal.'))
            proximo=f'{rec.acao}: {rec.descricao}. Compare o resultado isolado e conjunto em novas questões.'
            limite='Poucas questões conjuntas e dificuldade não calibrada; não é possível atribuir o erro a uma habilidade com certeza.'
        novas = sorted(set(candidatos.questao_id) - set(aluno.questao_id))
        disponibilidade = ', '.join(novas) if novas else 'Nenhuma questão inédita deste tipo no banco; ampliar o banco.'
        linhas.append(dict(aluno_id=rec.aluno_id,ordem=rec.ordem,alvo=rec.alvo,tipo=rec.tipo,
            habilidade=rec.descricao,evidencia=evidencia,interpretacao=interpretacao,
            questoes_erradas_primeira_tentativa=', '.join(sorted(itens.loc[itens.acertou.eq(0),'questao_id'])),
            proxima_acao=proximo,questoes_ineditas_disponiveis=disponibilidade,limite=limite))
    return pd.DataFrame(linhas)


def salvar_feedback_texto(feedback, pasta):
    """Um relatório legível por estudante, além do CSV estruturado."""
    pasta.mkdir(parents=True,exist_ok=True)
    for i,(aluno, grupo) in enumerate(feedback.groupby('aluno_id'),1):
        partes=[f'# Plano de estudo — {aluno}', 'Estimativas experimentais. Os motivos abaixo descrevem evidências, não causas confirmadas de erros.']
        for r in grupo.itertuples(index=False):
            partes.extend([f'## {r.ordem}. {r.alvo} — {r.habilidade}',
                f'**Evidências:** {r.evidencia}', f'**Interpretação:** {r.interpretacao}',
                f'**Questões erradas (primeira tentativa):** {r.questoes_erradas_primeira_tentativa or "Nenhuma registrada"}.',
                f'**Próxima ação:** {r.proxima_acao}', f'**Questões inéditas disponíveis:** {r.questoes_ineditas_disponiveis}', f'**Limite:** {r.limite}'])
        # IDs arbitrários não devem ser usados diretamente como caminhos.
        (pasta/f'aluno_{i:02d}.md').write_text('\n\n'.join(partes)+'\n',encoding='utf-8')
