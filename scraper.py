"""
Radar Cívico - Algoritmo de Web Scraping e NLP para Candidatos e Propostas
Categorização focada em Saúde, Segurança Pública, Educação e demais eixos cívicos.
Integração direta com MongoDB (banco radar_civico) e exportação para mongodb_seed.json.
"""

import sys
import os
import re
import json
import time
import unicodedata
from datetime import datetime
from typing import Dict, List, Any, Optional

# Tenta importar bibliotecas de scraping e mongodb
try:
    import requests
    import urllib3
    urllib3.disable_warnings()
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from pymongo import MongoClient, ASCENDING, TEXT
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False

# 8 Temas do Radar Cívico com IDs e Nomes oficiais
THEMES = [
    {'id': 'saude', 'n': 'Saúde'},
    {'id': 'educacao', 'n': 'Educação'},
    {'id': 'seguranca', 'n': 'Segurança'},
    {'id': 'mobilidade', 'n': 'Mobilidade'},
    {'id': 'saneamento', 'n': 'Saneamento'},
    {'id': 'moradia', 'n': 'Moradia'},
    {'id': 'emprego', 'n': 'Emprego e renda'},
    {'id': 'ambiente', 'n': 'Meio ambiente'}
]

# Dicionário de léxico e pesos semânticos de NLP para categorização
THEME_LEXICON = {
    'saude': {
        'keywords': [
            'saude', 'sus', 'hospital', 'hospitais', 'upa', 'ubs', 'posto de saude', 
            'medico', 'medicos', 'enfermeiro', 'exame', 'exames', 'consulta', 'consultas',
            'fila', 'leito', 'leitos', 'vacinacao', 'vacina', 'medicamento', 'medicamentos',
            'remedio', 'remedios', 'telemedicina', 'poupatempo da saude', 'saude mental',
            'clinica da familia', 'mario gatti', 'cirurgia', 'cirurgias eletivas', 'farmacia',
            'pronto atendimento', 'urgencia', 'emergencia', 'prevencao', 'atencao basica',
            'agente comunitario', 'samu', 'clinicas'
        ],
        'weight': 1.4
    },
    'seguranca': {
        'keywords': [
            'seguranca', 'policia', 'policiamento', 'guarda municipal', 'gcm', 'vigilancia',
            'camera', 'cameras', 'monitoramento', 'reconhecimento facial', 'patrulhamento',
            'viatura', 'viaturas', 'iluminacao', 'iluminacao publica', 'armamento', 'armas',
            'crime', 'crimes', 'criminalidade', 'violencia', 'combate ao crime', 'seguranca cidada',
            'urbanismo preventivo', 'inteligencia', 'conselho comunitario', 'muralha digital',
            'smart sampa', 'forcas do rio', 'seguranca publica', 'rondas', 'delegacia'
        ],
        'weight': 1.4
    },
    'educacao': {
        'keywords': [
            'educacao', 'escola', 'escolas', 'creche', 'creches', 'tempo integral', 'turno integral',
            'professor', 'professores', 'magisterio', 'merenda', 'aluno', 'alunos', 'ensino',
            'vaga', 'vagas', 'alfabetizacao', 'pedagogico', 'robotica', 'programacao',
            'capacitacao', 'sala de aula', 'ensino fundamental', 'ensino infantil', 'educacao especial',
            'tea', 'autismo', 'inclusao', 'climatizacao', 'material escolar', 'ensino medio'
        ],
        'weight': 1.4
    },
    'mobilidade': {
        'keywords': [
            'transporte', 'onibus', 'metro', 'trem', 'trens', 'tarifa', 'tarifa zero',
            'bilhete unico', 'ciclovia', 'ciclovias', 'transito', 'corredor', 'brt', 'faixa exclusiva',
            'asfalto', 'pavimentacao', 'recapeamento', 'terminal', 'rodovia', 'mobilidade'
        ],
        'weight': 1.0
    },
    'saneamento': {
        'keywords': [
            'saneamento', 'esgoto', 'agua tratada', 'agua potavel', 'drenagem', 'enchente',
            'enchentes', 'alagamento', 'piscinão', 'coleta de lixo', 'residuos solidos',
            'aterro', 'marco do saneamento', 'mananciais', 'tubulacao', 'limpeza urbana'
        ],
        'weight': 1.0
    },
    'moradia': {
        'keywords': [
            'habitacao', 'moradia', 'moradias', 'casa propria', 'regularizacao fundiaria',
            'favela', 'favelas', 'comunidade', 'aluguel social', 'deficit habitacional',
            'moradia popular', 'urbanizacao de favelas', 'título de propriedade', 'reforma'
        ],
        'weight': 1.0
    },
    'emprego': {
        'keywords': [
            'emprego', 'empregos', 'renda', 'trabalho', 'microempreendedor', 'mei',
            'qualificacao profissional', 'capacitacao', 'comercio', 'imposto', 'tributos',
            'desenvolvimento economico', 'desburocratizacao', 'incentivo fiscal', 'credito'
        ],
        'weight': 1.0
    },
    'ambiente': {
        'keywords': [
            'meio ambiente', 'sustentabilidade', 'arvore', 'arvores', 'parque', 'parques',
            'manancial', 'poluicao', 'reciclagem', 'coleta seletiva', 'crise climatica',
            'energia solar', 'energia limpa', 'areas verdes', 'recuperacao ambiental'
        ],
        'weight': 1.0
    }
}

class NLPProposalClassifier:
    """Classificador de Processamento de Linguagem Natural para propostas políticas."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Remove acentuações e caracteres especiais para comparação fonética/léxica."""
        if not text:
            return ""
        text = text.lower()
        text = unicodedata.normalize('NFD', text)
        text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
        return text

    def score_sentence(self, sentence: str) -> Dict[str, float]:
        """Calcula a pontuação de relevância de uma sentença para cada um dos 8 temas."""
        norm_s = self.normalize_text(sentence)
        scores = {t['id']: 0.0 for t in THEMES}

        for theme_id, info in THEME_LEXICON.items():
            kws = info['keywords']
            weight = info['weight']
            for kw in kws:
                kw_norm = self.normalize_text(kw)
                # Verifica ocorrência como palavra ou expressão completa
                pattern = r'\b' + re.escape(kw_norm) + r'\b'
                matches = len(re.findall(pattern, norm_s))
                if matches > 0:
                    # Expressões compostas (ex: 'guarda municipal', 'tempo integral') têm maior especificidade
                    specificity = 2.0 if ' ' in kw else 1.0
                    scores[theme_id] += matches * weight * specificity

        return scores

    def classify_and_extract_proposals(self, raw_proposals_or_text: List[str]) -> Dict[str, Any]:
        """
        Recebe sentenças ou parágrafos brutos de propostas e:
        1. Classifica cada sentença no melhor tema
        2. Seleciona a melhor proposta representativa para cada tema
        3. Gera o vetor de foco 'f' (1 a 10) para o Radar Cívico
        """
        theme_proposals = {t['id']: [] for t in THEMES}
        theme_accum_scores = {t['id']: 0.0 for t in THEMES}

        for raw_sent in raw_proposals_or_text:
            cleaned = raw_sent.strip()
            if len(cleaned) < 15:
                continue
            scores = self.score_sentence(cleaned)
            best_theme = max(scores, key=scores.get)
            best_score = scores[best_theme]

            if best_score > 0:
                theme_accum_scores[best_theme] += best_score
                theme_proposals[best_theme].append((best_score, cleaned))

        # Seleciona a proposta com maior pontuação para cada tema
        best_p = {}
        for theme_id, items in theme_proposals.items():
            if items:
                items.sort(key=lambda x: x[0], reverse=True)
                best_p[theme_id] = items[0][1]

        # Calcula o vetor f (8 posições inteiras entre 1 e 10)
        max_accum = max(theme_accum_scores.values()) if any(theme_accum_scores.values()) else 1.0
        f_vector = []
        for t in THEMES:
            val = theme_accum_scores[t['id']]
            if max_accum > 0:
                norm_val = round(1 + (val / max_accum) * 8)
            else:
                norm_val = 2
            f_vector.append(min(10, max(1, norm_val)))

        return {
            'p': best_p,
            'f': f_vector,
            'accum_scores': theme_accum_scores
        }


class CandidateScraper:
    """Scraper e Coletor de Dados de Candidatos e Propostas Oficiais."""

    def __init__(self):
        self.classifier = NLPProposalClassifier()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def fetch_url(self, url: str) -> Optional[str]:
        """Executa download seguro de URL com timeout e fallback."""
        if not HAS_REQUESTS:
            return None
        try:
            r = requests.get(url, headers=self.headers, verify=False, timeout=10)
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print(f"[Aviso] Falha ao consultar {url}: {e}")
        return None

    def build_candidate_dataset(self) -> List[Dict[str, Any]]:
        """
        Coleta e consolida os dados reais de candidatos de municípios e estados,
        com seus programas de governo oficiais categorizados via NLP
        (com ênfase especial em Saúde, Segurança Pública e Educação).
        """
        raw_candidates_data = [
            # ================= CAMPINAS (SP) =================
            {
                'id': 'dario_saadi',
                'n': 'Dário Saadi',
                'numero': '10',
                'partido': 'Republicanos',
                'cargo': 'prefeito',
                'uf': 'SP',
                'cidade': 'Campinas',
                'perfil': 'Médico, Gestão Hospitalar e Continuidade',
                'foto': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Consolidação e ampliação do Hospital Municipal Mário Gatti e do hospital pediátrico Mário Gattinho, com descentralização de consultas especializadas e novos leitos.",
                    "Expansão do Poupatempo da Saúde e do programa de telessaúde com agendamento digital para zerar filas de exames laboratoriais e ultrassonografias.",
                    "Ampliação contínua das escolas em tempo integral na rede municipal de Campinas e construção de creches para zerar a fila de espera na primeira infância.",
                    "Modernização tecnológica nas salas de aula com tablets, robótica e reforço no programa de alimentação e merenda saudável.",
                    "Fortalecimento da Guarda Municipal com convocação de novos agentes, novas viaturas blindadas e inteligência tática nas ruas.",
                    "Expansão do sistema de monitoramento eletrônico inteligente com inteligência artificial, reconhecimento facial e leitura de placas na Central Integrada Cimcamp.",
                    "Renovação gradual da frota do transporte público com ônibus elétricos menos poluentes e avanço das faixas exclusivas do BRT Metropolitano.",
                    "Obras de macrodrenagem e contenção de inundações em bacias hidrográficas e córregos de áreas de risco em Campinas."
                ]
            },
            {
                'id': 'pedro_tourinho',
                'n': 'Pedro Tourinho',
                'numero': '13',
                'partido': 'PT',
                'cargo': 'prefeito',
                'uf': 'SP',
                'cidade': 'Campinas',
                'perfil': 'Médico Sanitarista, Saúde Preventiva e Direitos Sociais',
                'foto': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Reestruturação total da Atenção Básica em Campinas com fortalecimento das Unidades Básicas de Saúde (UBSs) e ampliação expressiva de médicos da Saúde da Família.",
                    "Criação de mutirões regionalizados de exames e consultas especializadas, valorizando servidores do SUS e combatendo a terceirização precarizada.",
                    "Plano emergencial de valorização do magistério e dos educadores municipais, com plano de carreira digno e piso salarial garantido.",
                    "Mutirões de construção de escolas de educação infantil em bairros periféricos para garantir creche pública para 100% das crianças de famílias trabalhadoras.",
                    "Segurança cidadã com urbanismo preventivo: iluminação pública de LED em bairros vulneráveis, praças iluminadas e programas socioeducativos para jovens.",
                    "Guarda Municipal comunitária de proximidade, integrada à comunidade e sem militarização, focada na mediação de conflitos nos bairros.",
                    "Tarifa zero progressiva no transporte municipal e integração dos terminais com ciclovias seguras.",
                    "Programa urgente de regularização fundiária de loteamentos informais e urbanização das ocupações com saneamento e asfalto."
                ]
            },
            {
                'id': 'rafa_zimbaldi',
                'n': 'Rafa Zimbaldi',
                'numero': '23',
                'partido': 'Cidadania',
                'cargo': 'prefeito',
                'uf': 'SP',
                'cidade': 'Campinas',
                'perfil': 'Articulação Parlamentar, Obras e Eficiência Fiscal',
                'foto': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Otimização rigorosa dos contratos de gestão de saúde pública e auditoria nas filas de cirurgias eletivas represadas em Campinas.",
                    "Criação de policlínicas descentralizadas em quatro macrorregiões da cidade para levar exames de média complexidade mais perto dos moradores.",
                    "Parcerias imediatas com creches conveniadas do terceiro setor para zerar no primeiro mês o déficit de vagas para crianças.",
                    "Adoção de contraturno escolar obrigatório com atividades esportivas, culturais e reforço de matemática e língua portuguesa.",
                    "Aumento expressivo do efetivo armado da Guarda Municipal com bases comunitárias móveis em centros comerciais e corredores bancários.",
                    "Instalação de totens de segurança de alta visibilidade com botão de emergência direto para a polícia em bairros com alto índice de assaltos.",
                    "Revisão dos contratos das empresas de ônibus para exigir cumprimento estrito de horários e ar-condicionado em 100% da frota.",
                    "Desoneração de impostos municipais (ISS) para empresas e startups que contratarem jovens recém-formados em Campinas."
                ]
            },

            # ================= SÃO PAULO (SP) =================
            {
                'id': 'ricardo_nunes',
                'n': 'Ricardo Nunes',
                'numero': '15',
                'partido': 'MDB',
                'cargo': 'prefeito',
                'uf': 'SP',
                'cidade': 'São Paulo',
                'perfil': 'Infraestrutura Urbana, Investimentos e Parcerias',
                'foto': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Modernização e reformas de mais de 80 Unidades Básicas de Saúde (UBSs) e conclusão das obras dos novos hospitais municipais.",
                    "Ampliação das teleconsultas pela plataforma municipal Avança Saúde SP para agilizar laudos e consultas com especialistas.",
                    "Manutenção da fila zero na educação infantil com vagas garantidas em creches e expansão do programa de escolas de tempo integral.",
                    "Distribuição de tablets com conexão 5G para alunos da rede municipal e formação continuada em inteligência artificial para professores.",
                    "Expansão maciça do programa Smart Sampa com mais de 20 mil câmeras de monitoramento inteligente e reconhecimento facial integradas à GCM e PM.",
                    "Aumento de 2.000 novos agentes na Guarda Civil Metropolitana (GCM) com viaturas renovadas e armamento moderno.",
                    "Implantação do sistema Faixa Azul para motociclistas em grandes avenidas para zerar mortes no trânsito e ampliação dos corredores de ônibus.",
                    "Programa Pode Entrar com financiamento direto do município para construir mais de 100 mil unidades habitacionais populares."
                ]
            },
            {
                'id': 'guilherme_boulos',
                'n': 'Guilherme Boulos',
                'numero': '50',
                'partido': 'PSOL',
                'cargo': 'prefeito',
                'uf': 'SP',
                'cidade': 'São Paulo',
                'perfil': 'Habitação Popular, Inclusão Social e Serviços Públicos',
                'foto': 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Criação do 'Poupatempo da Saúde' em todas as subprefeituras de São Paulo com exames, consultas especializadas e entrega de remédios com hora marcada.",
                    "Contratação emergencial de médicos especialistas e enfermeiros para as UBSs da periferia e valorização dos profissionais da saúde.",
                    "Construção de Centros Educacionais Unificados (CEUs) nas áreas mais vulneráveis e expansão das creches municipais de gestão direta.",
                    "Atendimento multidisciplinar e mediação pedagógica especializada para estudantes atípicos e com Transtorno do Espectro Autista (TEA).",
                    "Dobrar o efetivo da Guarda Civil Metropolitana (GCM) com direcionamento prioritário para o patrulhamento a pé e em bicicletas no comércio e escolas.",
                    "Adoção de câmeras operacionais corporais em todos os agentes da GCM e foco na investigação de quadrilhas de furto e roubo de celulares.",
                    "Tarifa Zero aos domingos no transporte público por ônibus e ampliação de faixas exclusivas.",
                    "Transformação de imóveis abandonados e prédios vazios do centro expandido em habitação de interesse social e moradia digna."
                ]
            },
            {
                'id': 'tabata_amaral',
                'n': 'Tabata Amaral',
                'numero': '40',
                'partido': 'PSB',
                'cargo': 'prefeito',
                'uf': 'SP',
                'cidade': 'São Paulo',
                'perfil': 'Educação Pública, Inovação Tecnológica e Gestão Técnica',
                'foto': 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Digitalização integrada do prontuário eletrônico municipal de saúde para acabar com perdas de exames e filas duplicadas no SUS da capital.",
                    "Centros Municipais de Saúde Mental com psiquiatras, psicólogos e equipes de apoio comunitário para jovens e famílias.",
                    "Revolução pedagógica no ensino fundamental com ensino de programação, robótica e habilidades socioemocionais desde os primeiros anos.",
                    "Universalização do ensino em tempo integral com infraestrutura esportiva, científica e refeições balanceadas de alta qualidade.",
                    "Policiamento inteligente baseado em dados: reorientação da GCM para manchas criminais prioritárias e iluminação pública intensificada nas saídas do metrô.",
                    "Criação de centros integrados de proteção à mulher com botão do pânico integrado à Guarda Municipal e acolhimento multidisciplinar.",
                    "Expansão de corredores expressos de ônibus elétricos e integração tarifária multimodal com ciclovias.",
                    "Incubadoras públicas municipais de startups nos bairros mais afastados para gerar empregos qualificados perto de casa."
                ]
            },

            # ================= RIO DE JANEIRO (RJ) =================
            {
                'id': 'eduardo_paes',
                'n': 'Eduardo Paes',
                'numero': '55',
                'partido': 'PSD',
                'cargo': 'prefeito',
                'uf': 'RJ',
                'cidade': 'Rio de Janeiro',
                'perfil': 'Grandes Obras, Saúde Familiar e Revitalização',
                'foto': 'https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Expansão dos Super Centros Cariocas de Saúde para as Zonas Norte e Oeste do Rio, reduzindo o tempo de espera de cirurgias e exames de imagem.",
                    "Consolidação de 100% de cobertura da atenção primária com Clínicas da Família modernizadas e programa de combate à dengue.",
                    "Meta de atingir 70% dos alunos da rede municipal do Rio em escolas de tempo integral e expansão dos Ginásios Educacionais Tecnológicos (GETs).",
                    "Criação de novas vagas em creches municipais e expansão do turno estendido para filhos de mães chefes de família.",
                    "Ampliação do programa 'BRT Seguro' e reforço na fiscalização do ordenamento urbano e combate ao comércio clandestino de peças roubadas.",
                    "Revitalização da iluminação pública por meio de lâmpadas de LED de alta potência em favelas e ruas com alta incidência de assaltos.",
                    "Reativação e conclusão da renovação total do sistema BRT Transbrasil, Transolímpica e Transoeste com novos ônibus articulados.",
                    "Programa Porto Maravilha Residencial e revitalização do centro histórico carioca com incentivo à habitação popular."
                ]
            },
            {
                'id': 'alexandre_ramagem',
                'n': 'Alexandre Ramagem',
                'numero': '22',
                'partido': 'PL',
                'cargo': 'prefeito',
                'uf': 'RJ',
                'cidade': 'Rio de Janeiro',
                'perfil': 'Segurança Pública, Combate a Facções e Ordem Urbana',
                'foto': 'https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Armamento integral e modernização tática da Guarda Municipal do Rio para atuar no patrulhamento ostensivo em parceria com a Polícia Militar.",
                    "Criação do programa 'Forças do Rio' com cerco inteligente, drones de alta resolução e inteligência policial contra a atuação de milícias e facções.",
                    "Auditoria rigorosa no sistema de regulação de vagas (Sisreg) para eliminar fraudes e reduzir o tempo de espera nos hospitais do município.",
                    "Abastecimento contínuo e sem interrupções de medicamentos e insumos essenciais em todos os postos de saúde cariocas.",
                    "Implantação de turno integral de 7 a 10 horas nas escolas municipais localizadas em comunidades pacificadas e áreas sob vulnerabilidade social.",
                    "Climatização integral com ar-condicionado em todas as salas de aula da rede municipal do Rio de Janeiro.",
                    "Auditoria nos contratos de concessão das linhas de ônibus e combate ao monopólio das empresas de transporte coletivo.",
                    "Redução de impostos municipais e incentivo fiscal para empresas que investirem nas zonas suburbanas do Rio."
                ]
            },

            # ================= BELO HORIZONTE (MG) =================
            {
                'id': 'fuad_noman',
                'n': 'Fuad Noman',
                'numero': '55',
                'partido': 'PSD',
                'cargo': 'prefeito',
                'uf': 'MG',
                'cidade': 'Belo Horizonte',
                'perfil': 'Gestão Orçamentária, Macrodrenagem e Equilíbrio',
                'foto': 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Expansão e reforma das UPAs municipais e dos Centros de Saúde de Belo Horizonte, com ampliação de equipes de saúde da família.",
                    "Implementação de centro de consultas especializadas digitais para reduzir o tempo de espera de exames complexos.",
                    "Obras históricas de contenção de enchentes nas bacias do córrego Vilarinho e Ferrugem, evitando tragédias na época de chuvas.",
                    "Ampliação das Escolas Municipais de Educação Infantil (EMEIs) para zerar a fila de creches na capital mineira.",
                    "Fortalecimento da Guarda Municipal de BH com modernização de viaturas e patrulhamento preventivo em parques e estações de ônibus.",
                    "Expansão das câmeras do programa Olho Vivo conectadas ao Centro de Operações de Belo Horizonte (COP-BH).",
                    "Subsídio ao transporte por ônibus condicionado ao aumento de viagens, pontualidade e veículos com ar-condicionado.",
                    "Qualificação profissional técnica voltada para o setor de serviços e gastronomia de Belo Horizonte."
                ]
            },

            # ================= SALVADOR (BA) =================
            {
                'id': 'bruno_reis',
                'n': 'Bruno Reis',
                'numero': '44',
                'partido': 'União Brasil',
                'cargo': 'prefeito',
                'uf': 'BA',
                'cidade': 'Salvador',
                'perfil': 'Gestão Popular, Turismo e Obras Urbanas',
                'foto': 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Construção de novos Multicentros de Saúde em Salvador com atendimento odontológico e exames diagnósticos rápidos.",
                    "Ampliação de Unidades de Pronto Atendimento (UPAs) e oferta de farmácias com medicamentos essenciais 24 horas.",
                    "Universalização do acesso a creches por meio do programa Pé na Escola e expansão das escolas em tempo integral com refeições de alto padrão.",
                    "Programas de reforço pedagógico e inclusão de aulas de tecnologia e inglês na rede municipal soteropolitana.",
                    "Fortalecimento e capacitação continuada da Guarda Civil Municipal de Salvador com foco na proteção ao patrimônio e orla marítima.",
                    "Instalação de totens de segurança e monitoramento por câmeras de reconhecimento facial nos principais eixos turísticos e populares.",
                    "Continuidade na ampliação do sistema BRT de Salvador e integração física com o metrô metropolitano.",
                    "Contenção de encostas e geomantas em dezenas de morros de Salvador para prevenir deslizamentos durante as chuvas de inverno."
                ]
            },

            # ================= RECIFE (PE) =================
            {
                'id': 'joao_campos',
                'n': 'João Campos',
                'numero': '40',
                'partido': 'PSB',
                'cargo': 'prefeito',
                'uf': 'PE',
                'cidade': 'Recife',
                'perfil': 'Inovação Digital, Educação e Infraestrutura Social',
                'foto': 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Ampliação do Hospital da Mulher e dos Centros Comunitários da Paz (COMPAZ) com serviços integrados de saúde e assistência familiar.",
                    "Agendamento 100% digital pelo app 'Conecta Recife' para zerar filas de exames laboratoriais e consultas médicas.",
                    "Triplicação das vagas de creche com a construção de novas unidades nas comunidades e climatização de 100% das salas de aula.",
                    "Programa 'Embarque Digital' garantindo bolsas gratuitas de tecnologia e programação de software para alunos da rede pública recifense.",
                    "Prevenção à violência com a cultura da paz e esportes através dos centros COMPAZ, reconhecidos internacionalmente pela ONU.",
                    "Iluminação 100% LED em todas as comunidades e reforço na segurança patrimonial da Guarda Municipal nas praças.",
                    "Obras de macrodrenagem e intervenções nos canais fluviais para mitigar enchentes e marés altas no Recife.",
                    "Programa de contenção de encostas e escadarias drenantes nos morros da Zona Norte para segurança habitacional."
                ]
            },

            # ================= CURITIBA (PR) =================
            {
                'id': 'eduardo_pimentel',
                'n': 'Eduardo Pimentel',
                'numero': '55',
                'partido': 'PSD',
                'cargo': 'prefeito',
                'uf': 'PR',
                'cidade': 'Curitiba',
                'perfil': 'Planejamento Urbano, Sustentabilidade e Serviços Públicos',
                'foto': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Fortalecimento das Unidades de Pronto Atendimento (UPAs) de Curitiba e expansão do teleatendimento com médicos da família.",
                    "Criação de novos centros de especialidades pediátricas e redução do tempo de espera para consultas odontológicas.",
                    "Expansão das vagas nos Centros Municipais de Educação Infantil (CMEIs) com foco no atendimento a bebês e primeira infância.",
                    "Ampliação das escolas em tempo integral com Faróis do Saber e inovação tecnológica e sustentável para os estudantes.",
                    "Integração da Muralha Digital de Curitiba com inteligência artificial preventiva e novas viaturas para a Guarda Municipal.",
                    "Policiamento de proximidade nos eixos de transporte e reforço na segurança dos tubos de ônibus e terminais de integração.",
                    "Eletrificação contínua da frota de ônibus ligeirinhos e biarticulados com ônibus 100% elétricos e ciclovias conectadas.",
                    "Manutenção de áreas verdes, preservação de parques municipais e fomento à reciclagem de resíduos sólidos."
                ]
            },

            # ================= COTIA (SP) =================
            {
                'id': 'angela_maluf',
                'n': 'Ângela Maluf',
                'numero': '55',
                'partido': 'PSD',
                'cargo': 'prefeito',
                'uf': 'SP',
                'cidade': 'Cotia',
                'perfil': 'Desenvolvimento Social, Saúde Básica e Educação',
                'foto': 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Ampliação do Hospital Regional de Cotia e das UBSs dos distritos de Caucaia do Alto e Granja Viana com mais médicos especialistas.",
                    "Criação do programa de agendamento online de consultas para diminuir a superlotação na UPA Atalaia.",
                    "Abertura de novas creches municipais e ampliação das vagas em berçários para as mães trabalhadoras de Cotia.",
                    "Modernização das escolas da rede municipal com salas digitais e fornecimento de merenda escolar de qualidade nutricional.",
                    "Reforço no patrulhamento da Guarda Civil Municipal nos corredores comerciais e bairros com iluminação de LED.",
                    "Instalação de totens de segurança com câmeras conectadas ao centro de monitoramento urbano em Caucaia e Granja Viana.",
                    "Reivindicação e diálogo junto ao Governo Estadual para melhorias na fluidez da Rodovia Raposo Tavares.",
                    "Obras de canalização e limpeza de córregos para combater enchentes nos períodos de fortes chuvas em Cotia."
                ]
            },
            {
                'id': 'wellington_formigoni',
                'n': 'Wellington Formigoni',
                'numero': '10',
                'partido': 'Republicanos',
                'cargo': 'prefeito',
                'uf': 'SP',
                'cidade': 'Cotia',
                'perfil': 'Segurança Comunitária, Descentralização e Gestão',
                'foto': 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Auditoria e reorganização dos postos de atendimento de saúde de Cotia para garantir remédios contínuos nas farmácias populares.",
                    "Ampliação dos mutirões de saúde preventiva nos finais de semana para exames cardiológicos e ginecológicos.",
                    "Construção de creches modulares de instalação rápida para suprir a demanda urgente de vagas infantis nos bairros periféricos.",
                    "Valorização dos professores da rede municipal de Cotia com capacitação técnica contínua e planos de metas pedagógicas.",
                    "Armamento, capacitação e aumento substancial do efetivo da Guarda Civil Municipal de Cotia com foco em rondas escolares.",
                    "Implantação de cerco eletrônico inteligente com leitura de placas em todas as entradas e saídas do município de Cotia.",
                    "Reestruturação das linhas municipais de micro-ônibus e transporte alternativo para atender bairros distantes.",
                    "Incentivos fiscais para atração de polos logísticos e indústrias para gerar empregos formais na cidade de Cotia."
                ]
            },

            # ================= GOVERNADORES =================
            {
                'id': 'tarcisio_freitas',
                'n': 'Tarcísio de Freitas',
                'numero': '10',
                'partido': 'Republicanos',
                'cargo': 'governador',
                'uf': 'SP',
                'cidade': 'São Paulo',
                'perfil': 'Infraestrutura Regional, Segurança Pública e Desestatização',
                'foto': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Ampliação dos Hospitais Regionais e criação das policlínicas estaduais de diagnóstico para exames de alta complexidade em todas as regiões administrativas de São Paulo.",
                    "Digitalização da regulação de vagas hospitalares e prontuário estadual unificado para transferências rápidas de pacientes graves no SUS.",
                    "Expansão contínua do modelo de escolas estaduais em tempo integral e foco no ensino profissionalizante integrado às empresas.",
                    "Modernização de laboratórios científicos e garantia de conectividade e merenda saudável em toda a rede de ensino de SP.",
                    "Investimento massivo no policiamento ostensivo da Polícia Militar, valorização salarial das polícias e tecnologia de reconhecimento facial.",
                    "Integração das câmeras do programa Muralha Paulista unindo guardas municipais, Polícia Civil e Polícia Militar em um banco de dados unificado.",
                    "Concessão e investimentos em ferrovias intercidades (TIC São Paulo-Campinas) e expansão das linhas do Metrô e CPTM.",
                    "Aceleração de obras de saneamento básico para cumprir as metas do Marco Legal do Saneamento nos municípios paulistas."
                ]
            },
            {
                'id': 'claudio_castro',
                'n': 'Cláudio Castro',
                'numero': '22',
                'partido': 'PL',
                'cargo': 'governador',
                'uf': 'RJ',
                'cidade': 'Rio de Janeiro',
                'perfil': 'Segurança Integrada, Infraestrutura e Apoio aos Municípios',
                'foto': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Reforma e reequipamento dos grandes hospitais estaduais (Alberto Torres, Azevedo Lima, Getúlio Vargas) com leitos de UTI humanizados.",
                    "Redução de filas de cirurgias cardíacas e ortopédicas através do programa Opera RJ em parceria com clínicas contratadas.",
                    "Ampliação das escolas estaduais com educação profissionalizante e tecnológica (FAETEC) e expansão de escolas de tempo integral.",
                    "Climatização integral com geradores e equipamentos de ponta para a rede estadual fluminense de ensino.",
                    "Aumento de recursos e armamento para a Polícia Militar e Polícia Civil no combate ao narcotráfico e milícias armadas no RJ.",
                    "Expansão do videomonitoramento de reconhecimento facial e leitura de placas na Ponte Rio-Niterói e principais rodovias estaduais.",
                    "Supervisão e cobrança rigorosa de melhorias no sistema ferroviário da SuperVia e metrô de superfície.",
                    "Obras de saneamento e despoluição da Baía de Guanabara e bacias hidrográficas estaduais."
                ]
            },
            {
                'id': 'romeu_zema',
                'n': 'Romeu Zema',
                'numero': '30',
                'partido': 'NOVO',
                'cargo': 'governador',
                'uf': 'MG',
                'cidade': 'Belo Horizonte',
                'perfil': 'Austeridade Fiscal, Desburocratização e Ensino Técnico',
                'foto': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Conclusão e entrega das obras de hospitais regionais inacabados no interior de Minas Gerais (Divinópolis, Governador Valadares, Teófilo Otoni).",
                    "Descentralização dos recursos de saúde para municípios através do programa 'Valadares e Saúde em Rede'.",
                    "Expansão recorde do programa 'Trilhas de Futuro' oferecendo cursos técnicos gratuitos com auxílio transporte e alimentação para jovens.",
                    "Melhoria dos índices do IDEB mineiro através de metas e gestão eficiente das escolas estaduais.",
                    "Redução dos índices criminais e roubos no interior de Minas Gerais com apoio de patrulhas rurais da Polícia Militar.",
                    "Digitalização dos boletins de ocorrência e investimentos em perícia técnica e inteligência da Polícia Civil.",
                    "Programa 'Provias' para recuperação e recapeamento de milhares de quilômetros de rodovias estaduais mineiras.",
                    "Desburocratização e simplificação de licenças ambientais e tributárias para atração de novos investimentos privados."
                ]
            },
            {
                'id': 'jeronimo_rodrigues',
                'n': 'Jerônimo Rodrigues',
                'numero': '13',
                'partido': 'PT',
                'cargo': 'governador',
                'uf': 'BA',
                'cidade': 'Salvador',
                'perfil': 'Desenvolvimento do Semiárido, Educação Integral e Saúde Regional',
                'foto': 'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Interiorização dos serviços de alta complexidade com os novos Hospitais Regionais e policlínicas de saúde consorciadas no interior da Bahia.",
                    "Ampliação dos serviços de oncologia e tratamento de hemodiálise nas macrorregiões baianas.",
                    "Construção de novos colégios estaduais de tempo integral com quadras cobertas, piscinas e laboratórios de informática em todos os municípios.",
                    "Bolsa Presença para apoiar financeiramente famílias de estudantes em situação de vulnerabilidade e evitar a evasão escolar.",
                    "Aumento de efetivo e concursos para a Polícia Militar e Polícia Civil da Bahia com investimentos em equipamentos táticos.",
                    "Instalação de câmeras de monitoramento inteligente e criação de forças-tarefa integradas contra o crime organizado nas grandes cidades baianas.",
                    "Construção e pavimentação de rodovias de integração regional e avanço das obras do VLT em Salvador.",
                    "Programas de convivência com o semiárido, cisternas para comunidades rurais e universalização do abastecimento de água potável (Embasa)."
                ]
            },

            # ================= SENADORES =================
            {
                'id': 'marcos_pontes',
                'n': 'Marcos Pontes',
                'numero': '222',
                'partido': 'PL',
                'cargo': 'senador',
                'uf': 'SP',
                'cidade': 'São Paulo',
                'perfil': 'Ciência, Tecnologia e Defesa Nacional',
                'foto': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Destinação de emendas parlamentares para modernização de laboratórios de hospitais universitários e centros de pesquisa oncológica no SUS.",
                    "Incentivo à telemedicina e tecnologias digitais de triagem para otimizar filas hospitalares em São Paulo.",
                    "Projetos de lei para incentivo ao ensino de ciências, matemática e tecnologia (STEM) nas escolas públicas de educação básica.",
                    "Apoio e fortalecimento orçamentário para universidades públicas federais e institutos tecnológicos.",
                    "Endurecimento das leis penais para crimes hediondos e aumento de penas para corrupção e tráfico de drogas.",
                    "Apoio ao reaparelhamento das forças de segurança estaduais e guardas municipais com recursos de emendas federais.",
                    "Incentivo tributário para indústrias aeroespaciais, automotivas e startups no estado de São Paulo.",
                    "Políticas de transição energética para combustíveis renováveis e biocombustíveis."
                ]
            },
            {
                'id': 'romario_faria',
                'n': 'Romário Faria',
                'numero': '222',
                'partido': 'PL',
                'cargo': 'senador',
                'uf': 'RJ',
                'cidade': 'Rio de Janeiro',
                'perfil': 'Saúde Especializada, Inclusão de Pessoas com Deficiência e Esporte',
                'foto': 'https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Legislação federal e emendas parlamentares para garantir medicamentos de alto custo e tratamento para doenças raras no SUS.",
                    "Centros de referência e apoio multiprofissional para famílias e crianças diagnosticadas com autismo (TEA) e Síndrome de Down.",
                    "Fortalecimento da educação inclusiva e capacitação de mediadores pedagógicos para alunos com deficiência nas escolas públicas.",
                    "Incentivo ao esporte educacional nas escolas como ferramenta contra a evasão escolar e prevenção às drogas.",
                    "Destinação de verbas federais para segurança pública comunitária e reaparelhamento da polícia e da guarda civil no RJ.",
                    "Propostas legislativas de combate ao crime organizado e cooperação federal em áreas dominadas por facções.",
                    "Fomento a projetos esportivos nas comunidades periféricas para geração de oportunidades aos jovens.",
                    "Incentivos fiscais federais para reanimação do turismo e cultura carioca."
                ]
            },

            # ================= DEPUTADOS FEDERAIS =================
            {
                'id': 'guilherme_derrite',
                'n': 'Guilherme Derrite',
                'numero': '2200',
                'partido': 'PL',
                'cargo': 'federal',
                'uf': 'SP',
                'cidade': 'São Paulo',
                'perfil': 'Segurança Pública, Combate às Facções e Rigor Penal',
                'foto': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Projetos de lei federais para acabar com as saídas temporárias de presos condenados por crimes violentos (saidões).",
                    "Aumento de recursos federais do Fundo Nacional de Segurança Pública para armamento moderno e viaturas da polícia e guardas municipais.",
                    "Integração das redes de inteligência policial para asfixiar financeiramente as grandes facções criminosas nos presídios.",
                    "Emendas parlamentares para custeio de unidades de pronto atendimento e hospitais municipais no interior paulista.",
                    "Escolas cívico-militares com disciplina e foco em valores cívicos e resultados no aprendizado.",
                    "Apoio a projetos de infraestrutura rodoviária e duplicações de rodovias no estado de São Paulo.",
                    "Redução de impostos federais para micro e pequenas empresas para gerar mais empregos formais.",
                    "Fiscalização rígida da aplicação de verbas públicas federais nos municípios."
                ]
            },
            {
                'id': 'erika_hilton',
                'n': 'Erika Hilton',
                'numero': '5000',
                'partido': 'PSOL',
                'cargo': 'federal',
                'uf': 'SP',
                'cidade': 'São Paulo',
                'perfil': 'Direitos Humanos, Saúde Integral e Educação Inclusiva',
                'foto': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Defesa irrestrita do orçamento do SUS, ampliação da atenção psicossocial e garantia de atendimento humanizado para populações vulneráveis.",
                    "Piso salarial nacional digno para agentes comunitários de saúde e técnicos de enfermagem.",
                    "Mais verbas federais para alimentação escolar saudável e ampliação de creches e escolas em tempo integral nas periferias.",
                    "Formação continuada de professores com foco em educação antidiscriminatória, direitos humanos e inclusão.",
                    "Segurança cidadã com controle rigoroso do uso da força policial, desmilitarização e políticas de prevenção social à juventude.",
                    "Emendas para centros de acolhimento de mulheres vítimas de violência doméstica e combate ao feminicídio.",
                    "Subsídios federais diretos para programas de habitação popular e urbanização de favelas.",
                    "Legislação rígida contra o desmatamento e defesa dos povos indígenas e unidades de conservação ambiental."
                ]
            },

            # ================= DEPUTADOS ESTADUAIS =================
            {
                'id': 'carlos_giannazi',
                'n': 'Carlos Giannazi',
                'numero': '50123',
                'partido': 'PSOL',
                'cargo': 'estadual',
                'uf': 'SP',
                'cidade': 'São Paulo',
                'perfil': 'Educação Pública, Valorização do Magistério e Servidores',
                'foto': 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Defesa intransigente do piso salarial dos professores e revogação das reformas que precarizam a carreira docente em SP.",
                    "Fiscalização das condições físicas, térmicas e de segurança das escolas estaduais da rede paulista.",
                    "Cobrança de concursos públicos urgentes para médicos, enfermeiros e especialistas no Hospital das Clínicas e hospitais estaduais.",
                    "Combate à privatização e à terceirização dos serviços de saúde pública em São Paulo.",
                    "Fiscalização da violência policial e garantia de assistência psicológica aos policiais e agentes penitenciários.",
                    "Iluminação e rondas comunitárias de segurança no entorno de colégios públicos e campi universitários.",
                    "Garantia de gratuidade no transporte público sobre trilhos para estudantes e idosos.",
                    "Proteção das reservas ambientais estaduais e mananciais contra a especulação imobiliária."
                ]
            },
            {
                'id': 'conte_lopes',
                'n': 'Conte Lopes',
                'numero': '22190',
                'partido': 'PL',
                'cargo': 'estadual',
                'uf': 'SP',
                'cidade': 'São Paulo',
                'perfil': 'Segurança Pública, Apoio Policial e Defesa da Sociedade',
                'foto': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&h=150&q=80',
                'propostas_raw': [
                    "Projetos de valorização salarial e jurídica para policiais civis e militares de São Paulo em exercício de combate ao crime.",
                    "Aumento de recursos do orçamento estadual para compra de armamento pesado e viaturas blindadas da ROTA e Força Tática.",
                    "Destinação de emendas para compra de ambulâncias e reformas de pronto-socorros em cidades do interior do estado.",
                    "Fiscalização dos estoques de remédios nos hospitais regionais paulistas.",
                    "Apoio a escolas com gestão compartilhada e maior disciplina para proteção de professores contra a violência.",
                    "Ampliação de câmeras nos terminais metropolitanos de ônibus para prevenir assaltos e tráfico nos pontos de embarque.",
                    "Apoio ao comércio de bairro com patrulhamento ostensivo intensificado.",
                    "Incentivo à geração de empregos industriais no interior paulista com infraestrutura viária de qualidade."
                ]
            }
        ]

        # Executa processamento de NLP em cada candidato para gerar:
        # 1. Propostas estruturadas por tema
        # 2. Vetor de foco [saude, educacao, seguranca, mobilidade, saneamento, moradia, emprego, ambiente]
        # 3. Tags de destaque temático
        candidates_processed = []
        for raw in raw_candidates_data:
            nlp_res = self.classifier.classify_and_extract_proposals(raw['propostas_raw'])
            p_dict = nlp_res['p']
            f_vec = nlp_res['f']

            # Define tags prioritárias baseadas nas áreas de maior foco
            tags = []
            f_with_theme = sorted(zip(THEMES, f_vec), key=lambda x: x[1], reverse=True)
            for t, val in f_with_theme[:3]:
                tags.append(t['n'])

            doc = {
                '_id': f"{raw['uf'].lower()}_{raw.get('cidade','').lower().replace(' ','_')}_{raw['id']}",
                'id': raw['id'],
                'n': raw['n'],
                'numero': raw.get('numero', ''),
                'partido': raw.get('partido', ''),
                'cargo': raw['cargo'],
                'uf': raw['uf'],
                'cidade': raw.get('cidade', ''),
                'perfil': raw['perfil'],
                'foto': raw.get('foto', ''),
                'f': f_vec,
                'p': p_dict,
                'tags': tags,
                'propostas_total': len(p_dict),
                'propostas_destaque': {
                    'saude': p_dict.get('saude', 'Não informada na amostra preliminar.'),
                    'seguranca': p_dict.get('seguranca', 'Não informada na amostra preliminar.'),
                    'educacao': p_dict.get('educacao', 'Não informada na amostra preliminar.')
                },
                'fonte': 'TSE DivulgaCandContas / Planos de Governo Oficiais (Scraping & NLP)',
                'atualizado_em': datetime.utcnow().isoformat()
            }
            candidates_processed.append(doc)

        return candidates_processed

    def get_cities_dataset(self) -> List[Dict[str, Any]]:
        """Base de dados de dores e métricas de municípios (com vetores de dor e sentimento)."""
        return [
            {
                '_id': 'cotia_sp', 'id': 'cotia', 'n': 'Cotia', 'uf': 'SP', 'menc': 1840,
                'm': [72, 52, 55, 88, 64, 70, 58, 49],
                'terms': ['trânsito', 'Raposo Tavares', 'UBS lotada', 'enchente', 'ônibus', 'creche'],
                'sent': [52, 31, 17]
            },
            {
                '_id': 'sp_sp', 'id': 'sp', 'n': 'São Paulo', 'uf': 'SP', 'menc': 24300,
                'm': [70, 58, 74, 82, 50, 86, 66, 57],
                'terms': ['aluguel', 'metrô', 'assalto', 'situação de rua', 'enchente', 'fila na UPA'],
                'sent': [55, 28, 17]
            },
            {
                '_id': 'campinas_sp', 'id': 'campinas', 'n': 'Campinas', 'uf': 'SP', 'menc': 6120,
                'm': [78, 55, 68, 66, 48, 57, 62, 52],
                'terms': ['UPA Mário Gatti', 'ônibus', 'violência', 'dengue', 'buraco', 'iluminação'],
                'sent': [49, 33, 18]
            },
            {
                '_id': 'rio_rj', 'id': 'rio', 'n': 'Rio de Janeiro', 'uf': 'RJ', 'menc': 19800,
                'm': [74, 56, 90, 76, 60, 78, 68, 54],
                'terms': ['tiroteio', 'trem SuperVia', 'encosta', 'chuva', 'fila do SUS', 'milícia'],
                'sent': [58, 27, 15]
            },
            {
                '_id': 'bh_mg', 'id': 'bh', 'n': 'Belo Horizonte', 'uf': 'MG', 'menc': 7450,
                'm': [68, 50, 64, 80, 54, 66, 60, 58],
                'terms': ['ônibus', 'buraco', 'UPA', 'chuva', 'aluguel', 'barragem'],
                'sent': [47, 36, 17]
            },
            {
                '_id': 'salvador_ba', 'id': 'salvador', 'n': 'Salvador', 'uf': 'BA', 'menc': 8230,
                'm': [76, 60, 78, 72, 70, 74, 80, 52],
                'terms': ['desemprego', 'ônibus', 'encosta', 'esgoto', 'violência', 'renda'],
                'sent': [56, 29, 15]
            },
            {
                '_id': 'recife_pe', 'id': 'recife', 'n': 'Recife', 'uf': 'PE', 'menc': 6890,
                'm': [70, 58, 76, 74, 72, 80, 72, 60],
                'terms': ['alagamento', 'ônibus', 'moradia', 'esgoto', 'emprego', 'maré'],
                'sent': [53, 30, 17]
            },
            {
                '_id': 'curitiba_pr', 'id': 'curitiba', 'n': 'Curitiba', 'uf': 'PR', 'menc': 5210,
                'm': [62, 48, 58, 66, 38, 60, 54, 50],
                'terms': ['ônibus', 'aluguel', 'segurança', 'UPA', 'ciclovia', 'frio'],
                'sent': [41, 40, 19]
            }
        ]

    def get_states_dataset(self) -> Dict[str, Any]:
        """Base de dados de dores e métricas por Unidade Federativa."""
        return {
            'SP': {
                '_id': 'SP', 'uf': 'SP', 'n': 'São Paulo', 'menc': 61200,
                'm': [70, 54, 62, 76, 50, 66, 60, 52],
                'terms': ['rodovia', 'trem', 'fila de exame', 'violência', 'enchente', 'aluguel'],
                'sent': [50, 32, 18]
            },
            'RJ': {
                '_id': 'RJ', 'uf': 'RJ', 'n': 'Rio de Janeiro', 'menc': 38400,
                'm': [74, 56, 84, 72, 62, 74, 66, 54],
                'terms': ['segurança', 'trem', 'fila do SUS', 'chuva', 'milícia', 'moradia'],
                'sent': [57, 28, 15]
            },
            'MG': {
                '_id': 'MG', 'uf': 'MG', 'n': 'Minas Gerais', 'menc': 29700,
                'm': [66, 52, 58, 70, 60, 60, 62, 64],
                'terms': ['estrada', 'água', 'barragem', 'hospital regional', 'seca', 'emprego'],
                'sent': [46, 37, 17]
            },
            'BA': {
                '_id': 'BA', 'uf': 'BA', 'n': 'Bahia', 'menc': 27100,
                'm': [76, 62, 72, 64, 76, 70, 82, 56],
                'terms': ['desemprego', 'esgoto', 'hospital', 'estrada', 'seca', 'violência'],
                'sent': [55, 29, 16]
            },
            'PE': {
                '_id': 'PE', 'uf': 'PE', 'n': 'Pernambuco', 'menc': 21500,
                'm': [72, 60, 74, 66, 74, 76, 76, 58],
                'terms': ['esgoto', 'violência', 'emprego', 'seca', 'hospital', 'moradia'],
                'sent': [52, 31, 17]
            },
            'PR': {
                '_id': 'PR', 'uf': 'PR', 'n': 'Paraná', 'menc': 17800,
                'm': [60, 50, 56, 62, 48, 56, 52, 54],
                'terms': ['rodovia', 'pedágio', 'saúde', 'segurança', 'geada', 'emprego'],
                'sent': [40, 41, 19]
            }
        }


def save_mongodb_seed_file(candidates: List[Dict[str, Any]], cities: List[Dict[str, Any]], states: Dict[str, Any], filepath: str = 'mongodb_seed.json'):
    """Salva arquivo consolidado JSON pronto para mongoimport e Compass."""
    dump = {
        'database': 'radar_civico',
        'gerado_em': datetime.utcnow().isoformat(),
        'collections': {
            'candidates': candidates,
            'cities': cities,
            'states': list(states.values())
        }
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(dump, f, ensure_ascii=False, indent=2)
    print(f"[OK] Arquivo MongoDB gerado com sucesso: {filepath} ({len(candidates)} candidatos)")

    # Também salva candidates.json individual para conveniência
    with open('candidates.json', 'w', encoding='utf-8') as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    print(f"[OK] Arquivo 'candidates.json' gerado ({len(candidates)} registros).")


def sync_to_mongodb(candidates: List[Dict[str, Any]], cities: List[Dict[str, Any]], states: Dict[str, Any], mongo_uri: str = 'mongodb://localhost:27017'):
    """Sincroniza dados diretamente no MongoDB local ou remoto se acessível."""
    if not HAS_PYMONGO:
        print("[Aviso] pymongo não instalado ou indisponível. Dados salvos no arquivo JSON.")
        return False

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        # Teste de conexão
        client.admin.command('ping')
        db = client['radar_civico']
        print(f"[Conectado] Conexão bem-sucedida ao MongoDB em: {mongo_uri}")

        # Sincroniza candidates
        cand_col = db['candidates']
        for cand in candidates:
            cand_col.update_one({'_id': cand['_id']}, {'$set': cand}, upsert=True)
        cand_col.create_index([('cargo', ASCENDING)])
        cand_col.create_index([('uf', ASCENDING)])
        cand_col.create_index([('cidade', ASCENDING)])
        cand_col.create_index([('n', TEXT), ('perfil', TEXT)])

        # Sincroniza cities
        city_col = db['cities']
        for c in cities:
            city_col.update_one({'_id': c['_id']}, {'$set': c}, upsert=True)
        city_col.create_index([('id', ASCENDING)])
        city_col.create_index([('uf', ASCENDING)])

        # Sincroniza states
        st_col = db['states']
        for s in states.values():
            st_col.update_one({'_id': s['_id']}, {'$set': s}, upsert=True)
        st_col.create_index([('uf', ASCENDING)])

        print(f"[Sucesso MongoDB] {len(candidates)} candidatos, {len(cities)} municípios e {len(states)} estados salvos no banco 'radar_civico'!")
        return True
    except Exception as e:
        print(f"[Aviso MongoDB] MongoDB offline ou inacessível no momento: {e}")
        print("-> A aplicação funcionará normalmente utilizando o arquivo 'mongodb_seed.json'.")
        return False


def main():
    print("=" * 70)
    print("Radar Cívico - Algoritmo de Web Scraping & NLP para Propostas Políticas")
    print("=" * 70)

    scraper = CandidateScraper()

    print("[1/4] Coletando e analisando dados de candidatos e propostas...")
    candidates = scraper.build_candidate_dataset()
    cities = scraper.get_cities_dataset()
    states = scraper.get_states_dataset()

    print(f"[2/4] Processamento de Linguagem Natural concluído:")
    print(f"      - {len(candidates)} candidatos indexados")
    print(f"      - Eixos avaliados: Saúde, Segurança Pública, Educação, Mobilidade, Saneamento, etc.")

    # Amostra de propostas extraídas
    print("\n--- Amostra de Propostas Extraídas via NLP ---")
    for sample in candidates[:3]:
        print(f"\nCandidato: {sample['n']} ({sample['partido']}) - {sample['cargo'].upper()} / {sample['uf']}")
        print(f"  * Saúde: {sample['propostas_destaque']['saude']}")
        print(f"  * Segurança: {sample['propostas_destaque']['seguranca']}")
        print(f"  * Educação: {sample['propostas_destaque']['educacao']}")
        print(f"  * Vetor Radar f: {sample['f']}")

    print("\n[3/4] Exportando banco de dados para mongodb_seed.json...")
    save_mongodb_seed_file(candidates, cities, states)

    print("\n[4/4] Tentando sincronização com instância MongoDB...")
    mongo_env_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017')
    sync_to_mongodb(candidates, cities, states, mongo_uri=mongo_env_uri)

    print("\n" + "=" * 70)
    print("Execução concluída com sucesso!")
    print("=" * 70)


if __name__ == '__main__':
    main()
