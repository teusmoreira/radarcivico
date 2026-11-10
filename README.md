# 📡 Radar Cívico - Inteligência Pública e Alinhamento Político

Sistema integrado de **Processamento de Linguagem Natural (NLP)**, **Web Scraping** de propostas eleitorais oficiais (TSE/campanhas), **Banco de Dados MongoDB** e **Frontend Interativo** de alta performance.

---

## 🎯 Objetivo da Solução

O **Radar Cívico** analisa o que a população mais demanda em nível municipal e estadual, medindo a intensidade das dores locais e cruzando com propostas reais de candidatos a cargos eletivos, com ênfase especial em:
- 🏥 **Saúde Pública** (SUS, hospitais, UPAs, filas de exames, telessaúde, atenção primária)
- 🛡️ **Segurança Pública** (Guarda Municipal, policiamento ostensivo, câmeras inteligentes, reconhecimento facial, urbanismo preventivo)
- 🎓 **Educação** (Creches integrais, ensino em tempo integral, valorização docente, robótica, merenda)
- 🚌 **Mobilidade, Saneamento, Habitação, Emprego e Meio Ambiente**

---

## 📁 Arquivos do Projeto

| Arquivo | Função / Descrição |
| :--- | :--- |
| [Radar Cívico.html](file:///c:/Users/SY015450/Downloads/Radar%20C%C3%ADvico/Radar%20C%C3%ADvico.html) | **Interface Frontend**: Aplicação web com design responsivo, status do MongoDB, filtros rápidos por eixo, abas de cargos e cálculo de sobreposição matemática. Funciona tanto standalone quanto conectado à API. |
| [scraper.py](file:///c:/Users/SY015450/Downloads/Radar%20C%C3%ADvico/scraper.py) | **Algoritmo de Web Scraping & NLP**: Coleta candidatos e programas de governo oficiais, tokeniza e categoriza compromissos em Saúde, Segurança e Educação, calcula vetores temáticos `f` e grava no MongoDB e em JSON. |
| [server.py](file:///c:/Users/SY015450/Downloads/Radar%20C%C3%ADvico/server.py) | **Servidor Backend REST API**: Conecta ao MongoDB (`mongodb://localhost:27017`), expõe rotas `/api/status`, `/api/candidates`, `/api/cities`, `/api/scrape` e serve o frontend. Possui fallback transparente quando o banco estiver offline. |
| [mongodb_seed.json](file:///c:/Users/SY015450/Downloads/Radar%20C%C3%ADvico/mongodb_seed.json) | **Exportação do Banco de Dados**: Dump estruturado no formato oficial do MongoDB com coleções `candidates`, `cities` e `states`. |
| [candidates.json](file:///c:/Users/SY015450/Downloads/Radar%20C%C3%ADvico/candidates.json) | **Coleção de Candidatos**: Base em formato JSON Array contendo todos os 24 candidatos processados, com fotos, partidos, números, perfis e propostas. |
| [init_mongo.py](file:///c:/Users/SY015450/Downloads/Radar%20C%C3%ADvico/init_mongo.py) | **Script de Inicialização do MongoDB**: Conecta via `pymongo`, cria as coleções, índices de busca textual e grava os documentos no banco `radar_civico`. |
| [mongo_setup.js](file:///c:/Users/SY015450/Downloads/Radar%20C%C3%ADvico/mongo_setup.js) | **Script para Mongosh / Shell**: Configuração de schemas e índices de texto para execução via console do MongoDB. |

---

## 🧠 Como Funciona o Algoritmo de NLP & Scraping (`scraper.py`)

1. **Rastreamento e Coleta**:
   - Mapeia planos de governo registrados no Tribunal Superior Eleitoral (TSE) e bases de dados eleitorais públicas.
   - Abrange candidatos para os cargos de **Prefeito** (Campinas, São Paulo, Rio de Janeiro, Cotia, Belo Horizonte, Salvador, Recife, Curitiba), **Governador**, **Senador**, **Deputado Federal** e **Deputado Estadual**.

2. **Motor de Classificação Semântica (NLP)**:
   - Normalização léxica (`NFD`, remoção de acentos fonéticos e caracteres especiais).
   - Extração de n-gramas e ponderação sintática com foco em termos-chave:
     - **Saúde**: `hospital`, `upa`, `ubs`, `exame`, `consulta`, `poupatempo da saude`, `sus`, `leitos`, `telemedicina`, `cirurgias eletivas`
     - **Segurança**: `guarda municipal`, `gcm`, `cameras inteligentes`, `reconhecimento facial`, `muralha digital`, `policiamento comunitário`, `iluminação led`
     - **Educação**: `creches`, `tempo integral`, `magisterio`, `vagas infantis`, `merenda`, `robotica`, `professores`
   - Cálculo automático do vetor de foco temático $f \in [1, 10]^8$ correspondente aos 8 eixos do Radar Cívico.

3. **Geração de Propostas em Destaque**:
   - Cria o objeto `propostas_destaque` com os compromissos prioritários isolados para exibição em cards visuais no frontend.

---

## 🗄️ Estrutura do Banco de Dados no MongoDB

**Banco de Dados:** `radar_civico`

### Coleção `candidates`:
```json
{
  "_id": "sp_campinas_dario_saadi",
  "id": "dario_saadi",
  "n": "Dário Saadi",
  "numero": "10",
  "partido": "Republicanos",
  "cargo": "prefeito",
  "uf": "SP",
  "cidade": "Campinas",
  "perfil": "Médico, Gestão Hospitalar e Continuidade",
  "foto": "https://...",
  "f": [9, 6, 7, 3, 1, 1, 1, 1],
  "p": {
    "saude": "Consolidação e ampliação do Hospital Municipal Mário Gatti e do hospital pediátrico Mário Gattinho...",
    "seguranca": "Fortalecimento da Guarda Municipal com convocação de novos agentes e viaturas blindadas...",
    "educacao": "Ampliação contínua das escolas em tempo integral na rede municipal de Campinas..."
  },
  "propostas_destaque": {
    "saude": "Consolidação do Hospital Mário Gatti/Mário Gattinho e ampliação do Poupatempo da Saúde...",
    "seguranca": "Câmeras inteligentes de reconhecimento facial e leitura de placas integradas à Guarda Municipal...",
    "educacao": "Expansão contínua das escolas municipais em tempo integral e creches com fila zero..."
  },
  "tags": ["Saúde", "Segurança", "Educação"],
  "fonte": "TSE DivulgaCandContas / Planos de Governo Oficiais (Scraping & NLP)"
}
```

---

## 🚀 Como Executar

### Opção 1: Visualização Direta no Navegador (Zero Configuração)
Basta abrir com dois cliques o arquivo [Radar Cívico.html](file:///c:/Users/SY015450/Downloads/Radar%20C%C3%ADvico/Radar%20C%C3%ADvico.html) em qualquer navegador web. Ele carrega automaticamente todo o banco de candidatos e cidades com processamento NLP embutido.

### Opção 2: Servidor Completo com API REST
Execute no terminal PowerShell:
```powershell
python server.py
```
Acesse no navegador:
👉 **http://localhost:8000**

Endpoints disponíveis:
- `GET http://localhost:8000/api/status`
- `GET http://localhost:8000/api/candidates?cargo=prefeito&city=Campinas`
- `GET http://localhost:8000/api/candidates?cargo=prefeito&city=São Paulo`
- `POST http://localhost:8000/api/scrape`

### Opção 3: Carregar Dados no MongoDB Oficial
1. Certifique-se de que o MongoDB esteja ativo em `mongodb://localhost:27017` (ou configure a variável de ambiente `MONGO_URI`).
2. Execute o importador:
```powershell
python init_mongo.py
```
*Ou via mongoimport:*
```powershell
mongoimport --db radar_civico --collection candidates --file candidates.json --jsonArray --upsertFields=_id
```
