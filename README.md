# Chagas MVP V3 — Quanto este aluno sabe?

Protótipo explicável de estimativa de domínio de micro-habilidades, diagnóstico educacional e recomendação de estudos. Dados fictícios fornecidos no desafio Chagas AI. Não é uma avaliação de competência clínica.

## Executar no Linux

Abra a pasta `chagas_mvp_v3` no VS Code. Python 3.10 ou superior.

Se as três bibliotecas já estiverem instaladas no interpretador escolhido, execute diretamente:

```bash
python3 src/main.py
```

Caso precise instalar dependências, use um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/main.py
```

Por padrão, o terminal exibe A03. Para escolher outro aluno:

```bash
python3 src/main.py --aluno A01
```

Os nove CSVs de resultados, a imagem do grafo e os relatórios Markdown individuais são regenerados a cada execução. Os dados originais não são modificados. `--data` e `--output` permitem indicar outras pastas. Para executar os testes:

```bash
python3 -m unittest discover -s tests -v
```

## Estrutura

| Arquivo | Responsabilidade |
| --- | --- |
| `src/bkt.py` | Estimar domínio por BKT, para todos os pares aluno–habilidade. |
| `src/grafo.py` | Construir o grafo de coocorrências e calcular prioridade experimental. |
| `src/analise_relacional.py` | Comparar questões individuais e conjuntas na primeira tentativa. |
| `src/diagnostico.py` | Combinar evidências sem modificar as probabilidades BKT. |
| `src/recomendacao.py` | Ordenar ações de estudo e explicar seus motivos. |
| `src/feedback_formativo.py` | Explicar observações, interpretação, ação e limites por recomendação. |
| `src/validacao.py` | Comparar previsões sequenciais de acerto com duas linhas de base. |
| `src/main.py` | Validar os dados e executar todos os módulos em memória. |
| `tests/test_algoritmos.py` | Testes unitários e de integração com os CSVs fornecidos. |

## Saídas

- `estimativas_bkt_grafo.csv`: uma linha por aluno e habilidade, incluindo domínio BKT, prioridade, quantidade de tentativas primárias e quantidade de tentativas efetivamente usadas pelo BKT.
- `arestas_grafo.csv`: relações não direcionadas e questões que justificam cada aresta.
- `grafo_habilidades.png`: visualização das relações.
- `desempenho_relacional.csv`: uma linha por aluno e par de habilidades, taxas, acertos, quantidade de questões distintas e classificação preliminar.
- `diagnostico_alunos.csv`: indicadores individuais e alertas relacionais por aluno/habilidade.
- `recomendacoes.csv`: plano ordenado por aluno, com alvo, ação e motivo.

- `feedback_formativo.csv`: evidências, interpretação, IDs dos erros observados, ação e limites por recomendação.
- `feedback_alunos/`: relatórios Markdown numerados por ordem de ID do aluno (por exemplo `aluno_03.md` para A03 neste conjunto).
- `previsoes_validacao.csv`: previsões individuais, histórico disponível e resultado observado.
- `metricas_validacao.csv`: métricas dos três modelos nos mesmos eventos.
- `calibracao_validacao.csv`: cinco faixas de probabilidade por modelo, contagem e taxa observada.

CSV: separador vírgula; codificação UTF-8 com BOM; probabilidades e taxas na escala de 0 a 1. Campo de taxa vazio significa ausência de observações, não zero acertos.

## Método

### 1. Bayesian Knowledge Tracing (BKT)

Parâmetros iniciais: P(L0)=0,20; P(T)=0,05; P(S)=0,10; P(G)=1/número de alternativas. Após cada resposta, aplica-se Bayes para atualizar a crença de domínio e, em seguida, a transição P(L')=P(L|resposta)+(1-P(L|resposta))P(T). A estimativa representa o estado após a oportunidade de aprendizagem. Os parâmetros são hipóteses, não valores calibrados.

**Mudança da V1:** só questões sem habilidade secundária atualizam diretamente o BKT, evitando atribuir erros conjuntos à habilidade principal. Preservam-se todas as tentativas dessas questões na ordem cronológica. Sem observações individuais, retorna-se o prior de 0,20 explicitamente identificado como sem evidências. A coluna `taxa_acerto_observada` ainda considera todas as tentativas em que a habilidade é principal; `taxa_individual` usa só primeiras tentativas isoladas.

### 2. Grafo

Arestas não direcionadas entre habilidades que coocorrem em questões. Peso = quantidade de questões compartilhadas. Prioridade experimental = (1 − domínio próprio) + 0,25 × média ponderada das lacunas dos vizinhos. Escala de 0 a 1,25; não é probabilidade. Não altera o BKT e não indica causalidade ou pré-requisito. A prioridade é usada para ordenar ações individuais dentro da mesma etapa do plano, não para decidir domínio.

### 3. Análise relacional

Utiliza somente a primeira tentativa registrada de cada aluno/questão, tanto individual quanto conjunta. Para cada par A e B: taxas isoladas a e b, taxa conjunta c e diferença D=(a+b)/2−c. D é descritiva, não uma estimativa validada de integração. Classifica dificuldades possíveis, desempenho atípico, desempenho favorável ou resultado inconclusivo. Mínimo inicial: quatro questões distintas isoladas por habilidade e duas conjuntas. Desempenho alto >=70%; baixo <50%; diferença relevante >=25 pontos percentuais. Todas as classificações com dados suficientes continuam preliminares.

### 4. Diagnóstico e recomendação

Faixas BKT: abaixo de 40% baixo; 40–<60% em desenvolvimento; 60–<80% bom estimado; >=80% elevado estimado. Diagnóstico considera também taxa individual e quantidade de itens. Divergências extremas entre BKT e taxa são sinalizadas. Plano prioriza revisão de fundamentos ou coleta de evidências (etapa 1), prática e investigação de relações (etapa 2) e manutenção (etapa 3). As atividades são sugestões gerais por micro-habilidade, não questões novas geradas nem pré-requisitos causais.

### 5. Feedback formativo

Cada recomendação informa o que foi observado (acertos e denominadores, IDs das questões erradas na primeira tentativa), interpretação, próxima ação, IDs de questões ainda não respondidas do mesmo tipo (quando disponíveis) e limites. Não inventa erros conceituais específicos. Um relatório por estudante é exportado em Markdown. O banco não tem enunciados, alternativa selecionada ou raciocínio do aluno; a investigação conceitual adaptativa fica para uma evolução futura com metadados adicionais e revisão de educadores.

### 6. Avaliação preditiva exploratória

Avaliação sequencial (prequential), sem ajuste de parâmetros aos resultados. Para cada aluno e habilidade, ordenamos as questões isoladas por data. Começamos a avaliar depois de pelo menos três questões distintas anteriores; avaliamos somente a primeira tentativa registrada de cada nova questão. O histórico contém todas as tentativas individuais anteriores, inclusive repetições, para os três modelos. Respostas com mesmo timestamp são previstas antes de qualquer atualização daquele lote. O desfecho previsto é o acerto em questão individual inédita para aquele aluno, não a probabilidade latente de domínio. Não testamos questões conjuntas nem alunos novos.

- Taxa acumulada suavizada: `(1 + acertos)/(2 + tentativas)`.
- Média móvel suavizada: mesma fórmula nas últimas três tentativas.
- BKT: `P(acerto) = P(L)*(1-P(S)) + (1-P(L))/alternativas`, com estado de domínio atualizado apenas por respostas anteriores.
- Brier Score: média de `(p-y)^2`; log loss: média de `-y*ln(p)-(1-y)*ln(1-p)`; ambos menores são melhores. Acurácia: classificação `p >= 0,5`. Calibração descritiva por cinco faixas fixas, não teste estatístico.

Resultados (265 previsões comuns, dados fictícios):

| Modelo | Brier | Log loss | Acurácia |
| --- | ---: | ---: | ---: |
| Taxa acumulada | 0,237612 | 0,672364 | 62,26% |
| Média móvel | 0,236981 | 0,670011 | 62,26% |
| BKT | 0,254438 | 0,726509 | 59,62% |

A média móvel teve as menores perdas neste protocolo, por pequena diferença em relação à taxa acumulada. O BKT fixo não superou as referências simples. Não há evidência de superioridade do BKT; mantemos seu domínio latente como hipótese interpretável de pesquisa, não como medida validada. Para previsão de acertos, a média móvel é a referência provisória mais promissora neste teste. A decisão de adotar BKT em produção exigiria calibração em dados separados e nova avaliação fora da amostra. Não ajustar parâmetros e reavaliar nos mesmos eventos como se fossem teste independente. O teste não avalia benefício do grafo, feedback ou recomendações; tampouco demonstra impacto pedagógico.

## Testes e limitações

Com os dados fornecidos, a execução gera 96 estimativas, 6 arestas, 72 análises relacionais, 96 diagnósticos e 136 recomendações. Dez testes verificam cálculo manual do BKT, prior, isolamento de questões conjuntas, primeira tentativa, regras de classificação, execução completa, previsão de acerto, ausência de vazamento em timestamps iguais e métricas. Isso demonstra funcionamento do software, não validade educacional.

- BKT não estima diretamente domínio a partir de questões conjuntas; perde parte da informação em troca de uma atribuição mais transparente.
- BKT assume parâmetros fixos, aprendizagem após oportunidades e não modela esquecimento. Pode produzir probabilidades muito altas ou baixas. Repetições podem refletir memorização. A taxa de primeiras tentativas resume o histórico, enquanto o BKT dá peso à sequência; divergências podem ser legítimas.
- Poucos itens por relação (2–4 no banco), dificuldade não calibrada e chance de chute impedem inferências fortes sobre dificuldades de integração. O grafo representa coocorrência, não dependência pedagógica.
- Limiares e peso 0,25 são heurísticas iniciais. Recomendações não foram validadas em alunos reais; ausência de alerta não significa domínio.
- A avaliação sequencial inicial já compara BKT com referências simples. Uma avaliação futura precisa testar generalização em dados reais independentes, calibrar parâmetros, comparar recomendações com e sem grafo e medir impacto pedagógico com estudantes e educadores (aprendizagem em itens inéditos, retenção e compreensão das próprias lacunas).

## Transparência

Protótipo elaborado com auxílio do ChatGPT para discussão de arquitetura, implementação e testes. Revisão humana e fundamentação bibliográfica ainda necessárias para o relatório final.
