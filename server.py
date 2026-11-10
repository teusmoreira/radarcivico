"""
Radar Cívico - Servidor de API REST e Backend com Integração MongoDB
Fornece rotas para busca de candidatos, municípios, propostas categorizadas em Saúde,
Segurança Pública e Educação, e acionamento de novo web scraping.
Possui fallback transparente para 'mongodb_seed.json' quando o MongoDB estiver offline.
"""

import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timezone
from typing import Dict, List, Any

# Tenta carregar pymongo
try:
    from pymongo import MongoClient
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False

PORT = int(os.environ.get("PORT", 8000))
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
SEED_FILE = "mongodb_seed.json"
CANDIDATES_FILE = "candidates.json"


class DataManager:
    """Gerencia acesso híbrido aos dados: tenta MongoDB primeiro; se indisponível, usa JSON local."""

    def __init__(self, mongo_uri: str = MONGO_URI):
        self.mongo_uri = mongo_uri
        self.mongo_client = None
        self.db = None
        self.is_connected = False
        self._check_mongo()

    def _check_mongo(self) -> bool:
        if not HAS_PYMONGO:
            self.is_connected = False
            return False
        try:
            self.mongo_client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=1500)
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client['radar_civico']
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False

    def get_seed_data(self) -> Dict[str, Any]:
        """Carrega dados locais da semente JSON."""
        if os.path.exists(SEED_FILE):
            try:
                with open(SEED_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Erro leitura {SEED_FILE}] {e}")
        return {'collections': {'candidates': [], 'cities': [], 'states': []}}

    def get_candidates(self, city: str = None, uf: str = None, cargo: str = None, tag: str = None) -> List[Dict[str, Any]]:
        """Busca candidatos no MongoDB ou no arquivo JSON com filtros."""
        if self._check_mongo():
            try:
                query = {}
                if cargo:
                    query['cargo'] = cargo.lower()
                if cargo and cargo.lower() == 'presidente':
                    # Presidente possui abrangência nacional; não restringe por UF ou município
                    pass
                else:
                    if uf:
                        query['uf'] = uf.upper()
                    if city and cargo in ['prefeito', 'vereador']:
                        query['cidade'] = {'$regex': f"^{city}$", '$options': 'i'}
                if tag:
                    query['tags'] = tag

                cursor = self.db['candidates'].find(query, {'_id': 0})
                results = list(cursor)
                if results:
                    return results
            except Exception as e:
                print(f"[Aviso MongoDB Fallback] {e}")

        # Fallback para JSON local
        data = self.get_seed_data()
        cands = data.get('collections', {}).get('candidates', [])

        filtered = []
        for c in cands:
            if cargo and c.get('cargo', '').lower() != cargo.lower():
                continue
            if cargo and cargo.lower() == 'presidente':
                # Presidente possui abrangência nacional
                pass
            else:
                if uf and c.get('uf', '').upper() != uf.upper():
                    continue
                if city and cargo in ['prefeito', 'vereador']:
                    cand_city = c.get('cidade', '').lower()
                    if city.lower() not in cand_city and cand_city not in city.lower():
                        continue
            if tag and tag not in c.get('tags', []):
                continue
            # Remove _id para compatibilidade JSON pura se necessário
            c_clean = dict(c)
            filtered.append(c_clean)

        return filtered

    def get_cities(self) -> List[Dict[str, Any]]:
        if self._check_mongo():
            try:
                cities = list(self.db['cities'].find({}, {'_id': 0}))
                if cities:
                    return cities
            except Exception:
                pass
        return self.get_seed_data().get('collections', {}).get('cities', [])

    def get_states(self) -> Dict[str, Any]:
        if self._check_mongo():
            try:
                states_list = list(self.db['states'].find({}, {'_id': 0}))
                if states_list:
                    return {s['uf']: s for s in states_list}
            except Exception:
                pass
        raw_states = self.get_seed_data().get('collections', {}).get('states', [])
        return {s['uf']: s for s in raw_states}

    def get_status(self) -> Dict[str, Any]:
        mongo_ok = self._check_mongo()
        cands = self.get_candidates()
        cities = self.get_cities()
        return {
            'status': 'online',
            'mongodb': {
                'conectado': mongo_ok,
                'uri': self.mongo_uri if mongo_ok else None,
                'modo': 'MongoDB Nativo' if mongo_ok else 'Arquivo JSON / Sincronizador'
            },
            'estatisticas': {
                'total_candidatos': len(cands),
                'total_municipios': len(cities),
                'eixos_prioritarios': ['Saúde', 'Segurança Pública', 'Educação']
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


dm = DataManager()


class RadarCivicoHandler(SimpleHTTPRequestHandler):
    """Manipulador de requisições HTTP para API e Frontend do Radar Cívico."""

    def end_headers(self):
        # Habilita CORS para integração facilitada
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Rota de Status do Sistema e MongoDB
        if path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            resp = dm.get_status()
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            return

        # Rota de Busca de Candidatos
        if path == '/api/candidates':
            city = query.get('city', [None])[0]
            uf = query.get('uf', [None])[0]
            cargo = query.get('cargo', [None])[0]
            tag = query.get('tag', [None])[0]

            results = dm.get_candidates(city=city, uf=uf, cargo=cargo, tag=tag)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({
                'total': len(results),
                'filtros': {'city': city, 'uf': uf, 'cargo': cargo, 'tag': tag},
                'fonte_dados': 'MongoDB' if dm.is_connected else 'Arquivo Local (mongodb_seed.json)',
                'candidatos': results
            }, ensure_ascii=False).encode('utf-8'))
            return

        # Rota de Cidades
        if path == '/api/cities':
            cities = dm.get_cities()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(cities, ensure_ascii=False).encode('utf-8'))
            return

        # Rota de Estados
        if path == '/api/states':
            states = dm.get_states()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(states, ensure_ascii=False).encode('utf-8'))
            return

        # Rota padrão: redireciona raiz para Radar Cívico.html
        if path == '/' or path == '':
            self.path = '/Radar Cívico.html'

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Rota para acionar web scraping e NLP sob demanda
        if path == '/api/scrape':
            try:
                import scraper
                print("[API] Iniciando rotina de scraping e NLP...")
                sc = scraper.CandidateScraper()
                candidates = sc.build_candidate_dataset()
                cities = sc.get_cities_dataset()
                states = sc.get_states_dataset()
                scraper.save_mongodb_seed_file(candidates, cities, states)
                mongo_synced = scraper.sync_to_mongodb(candidates, cities, states)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'sucesso',
                    'candidatos_coletados': len(candidates),
                    'mongodb_sincronizado': mongo_synced,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'erro',
                    'mensagem': str(e)
                }, ensure_ascii=False).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()


def run_server(port: int = PORT):
    server_address = ('', port)
    httpd = HTTPServer(server_address, RadarCivicoHandler)
    print("=" * 70)
    print(f"Radar Cívico - Servidor Ativo em http://localhost:{port}")
    print(f"Status MongoDB: {'CONECTADO' if dm.is_connected else 'OFFLINE (utilizando mongodb_seed.json)'}")
    print("Rotas disponíveis:")
    print(f"  - Interface Web:    http://localhost:{port}/Radar%20C%C3%ADvico.html")
    print(f"  - Status API:       http://localhost:{port}/api/status")
    print(f"  - Candidatos:       http://localhost:{port}/api/candidates?cargo=prefeito&city=Campinas")
    print(f"  - Executar Scraper: POST http://localhost:{port}/api/scrape")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")


if __name__ == '__main__':
    run_server()
