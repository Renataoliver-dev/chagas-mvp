"""BKT básico com parâmetros iniciais, não calibrados."""
import pandas as pd

P_L0, P_T, P_S = 0.20, 0.05, 0.10


def atualizar_bkt(historico, p_l0=P_L0, p_t=P_T, p_s=P_S):
    p_l = p_l0
    for item in historico:
        p_g = 1 / int(item['alternativas'])
        if int(item['acertou']) == 1:
            a, b = p_l * (1-p_s), (1-p_l)*p_g
        else:
            a, b = p_l*p_s, (1-p_l)*(1-p_g)
        posterior = a / (a+b) if a+b else p_l
        p_l = posterior + (1-posterior)*p_t
    return p_l


def estimar_todos(respostas, questoes, habilidades):
    dados = respostas.merge(questoes, on='questao_id', validate='many_to_one')
    dados['respondida_em'] = pd.to_datetime(dados['respondida_em'])
    dados = dados.sort_values('respondida_em', kind='stable')
    linhas = []
    for aluno in sorted(respostas['aluno_id'].unique()):
        for hab in habilidades.itertuples(index=False):
            principal = dados[(dados.aluno_id == aluno) & (dados.habilidade_principal == hab.habilidade_id)]
            isoladas = principal[principal.habilidade_secundaria.fillna('').eq('')]
            historico = isoladas[['acertou','alternativas']].to_dict('records')
            linhas.append(dict(aluno_id=aluno, habilidade_id=hab.habilidade_id,
                habilidade=hab.habilidade, qtd_respostas=len(principal),
                acertos=int(principal.acertou.sum()), taxa_acerto_observada=principal.acertou.mean(),
                qtd_respostas_bkt=len(isoladas), questoes_distintas_bkt=isoladas.questao_id.nunique(),
                dominio_bkt=atualizar_bkt(historico),
                ultima_resposta=isoladas.respondida_em.max(),
                origem_estimativa='historico individual' if historico else 'prior sem evidencias'))
    return pd.DataFrame(linhas)
