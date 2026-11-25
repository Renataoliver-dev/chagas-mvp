import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bkt import atualizar_bkt, estimar_todos
from analise_relacional import classificar_relacao, primeiras_tentativas
from diagnostico import diagnosticar_habilidade
from main import executar, carregar_dados
from validacao import gerar_previsoes, avaliar, prever_bkt
from feedback_formativo import gerar_feedback


class TestAlgoritmos(unittest.TestCase):
    def test_bkt_calculo_manual(self):
        self.assertAlmostEqual(atualizar_bkt([{'acertou':1,'alternativas':4}]),.50)
        self.assertAlmostEqual(atualizar_bkt([{'acertou':0,'alternativas':4}]),.05+.95*(.02/.62))
    def test_bkt_sem_respostas(self):
        self.assertEqual(atualizar_bkt([]),.20)
    def test_relacional(self):
        self.assertEqual(classificar_relacao(.8,.8,.25,8,8,4),'Possivel dificuldade de integracao')
        self.assertEqual(classificar_relacao(.8,.8,0,8,8,1),'Evidencia insuficiente')
        self.assertEqual(classificar_relacao(.8,.3,0,8,8,2),'Possivel dificuldade na habilidade B')
        self.assertEqual(classificar_relacao(.3,.8,0,8,8,2),'Possivel dificuldade na habilidade A')
    def test_diagnostico(self):
        self.assertEqual(diagnosticar_habilidade(.9,.25,4),'Divergencia entre BKT e desempenho')
        self.assertEqual(diagnosticar_habilidade(.2,.25,4),'Possivel dificuldade individual')
        self.assertEqual(diagnosticar_habilidade(.9,1,1),'Evidencia insuficiente')
    def test_primeira_tentativa(self):
        q=pd.DataFrame([dict(questao_id='Q1',habilidade_principal='H1',habilidade_secundaria='')])
        r=pd.DataFrame([dict(aluno_id='A',questao_id='Q1',respondida_em='2026-01-02',acertou=1),dict(aluno_id='A',questao_id='Q1',respondida_em='2026-01-01',acertou=0)])
        d=primeiras_tentativas(r,q)
        self.assertEqual(len(d),1)
        self.assertEqual(d.iloc[0].acertou,0)
    def test_bkt_nao_atribui_erro_conjunto(self):
        h=pd.DataFrame([dict(habilidade_id='H1',habilidade='A'),dict(habilidade_id='H2',habilidade='B')])
        q=pd.DataFrame([dict(questao_id='Q1',habilidade_principal='H1',habilidade_secundaria='H2',alternativas=4)])
        r=pd.DataFrame([dict(aluno_id='A',questao_id='Q1',respondida_em='2026-01-01',acertou=0)])
        e=estimar_todos(r,q,h)
        self.assertTrue(e.dominio_bkt.eq(.2).all())
        self.assertTrue(e.qtd_respostas_bkt.eq(0).all())
    def test_pipeline_original(self):
        with TemporaryDirectory() as tmp:
            out=Path(tmp)
            e,g,r,d,rec=executar(ROOT/'data',out)
            self.assertEqual((len(e),len(g),len(r),len(d)),(96,6,72,96))
            self.assertTrue(e.dominio_bkt.between(0,1).all())
            self.assertFalse(e.duplicated(['aluno_id','habilidade_id']).any())
            p=r[(r.aluno_id=='A03')&(r.habilidade_a=='H04')&(r.habilidade_b=='H05')].iloc[0]
            self.assertAlmostEqual(p.desempenho_a,2/7)
            self.assertAlmostEqual(p.desempenho_b,3/8)
            self.assertEqual(p.desempenho_conjunto,0)
            self.assertEqual(rec[rec.aluno_id=='A03'].iloc[0].alvo,'H04')
            self.assertEqual(len(list(out.glob('*.csv'))),9)
            f=pd.read_csv(out/'feedback_formativo.csv')
            self.assertEqual(len(f),len(rec))
            a=f[(f.aluno_id=='A03')&(f.alvo=='H04')].iloc[0]
            self.assertIn('2/7',a.evidencia)
            self.assertIn('Q038',a.questoes_erradas_primeira_tentativa)
            self.assertIn('causa exata',a.limite)
            self.assertEqual(a.questoes_ineditas_disponiveis,'Q033')
            self.assertEqual(len(list((out/'feedback_alunos').glob('*.md'))),12)
            m=pd.read_csv(out/'metricas_validacao.csv')
            self.assertEqual(m.n_previsoes.tolist(),[265,265,265])
            self.assertTrue(m.brier_score.between(0,1).all())
            self.assertTrue((out/'grafo_habilidades.png').is_file())

    def test_previsao_bkt_e_acerto_nao_dominio(self):
        self.assertAlmostEqual(prever_bkt([],4),.2*.9+.8*.25)

    def test_validacao_sem_vazamento_e_sem_itens_repetidos(self):
        q=pd.DataFrame([dict(questao_id=f'Q{i}',habilidade_principal='H1',habilidade_secundaria='',alternativas=4) for i in range(1,6)])
        r=pd.DataFrame([dict(aluno_id='A',questao_id=f'Q{i}',respondida_em=f'2026-01-0{i}',acertou=1) for i in range(1,6)])
        # Q4 e Q5 têm o mesmo instante: nenhum pode informar o outro.
        r.loc[4,'respondida_em']='2026-01-04'
        r=pd.concat([r,pd.DataFrame([dict(aluno_id='A',questao_id='Q4',respondida_em='2026-01-05',acertou=0)])],ignore_index=True)
        original=gerar_previsoes(r,q)
        self.assertEqual(original.questao_id.tolist(),['Q4','Q5'])
        self.assertEqual(original.historico_distintas.tolist(),[3,3])
        self.assertAlmostEqual(original.iloc[0].taxa_acumulada,.8)
        r.loc[3:4,'acertou']=0
        alterado=gerar_previsoes(r,q)
        pd.testing.assert_frame_equal(original.drop(columns='acertou'),alterado.drop(columns='acertou'))

    def test_metricas_calculo_manual(self):
        p=pd.DataFrame({'acertou':[1,0],'taxa_acumulada':[.8,.2],'media_movel':[.8,.2],'bkt':[.8,.2]})
        m,c=avaliar(p)
        self.assertAlmostEqual(m.iloc[0].brier_score,.04)
        self.assertAlmostEqual(m.iloc[0].log_loss,-__import__('math').log(.8))
        self.assertEqual(m.iloc[0].acuracia,1)
        self.assertEqual(c.groupby('modelo').n_previsoes.sum().tolist(),[2,2,2])

if __name__=='__main__': unittest.main()
