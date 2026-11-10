"""
Radar Cívico - Inicializador e Verificador do Banco de Dados MongoDB
Lê mongodb_seed.json e popula as coleções:
  - candidates
  - cities
  - states
Cria índices otimizados para busca de candidatos por município, cargo e propostas (Saúde, Segurança, Educação).
"""

import os
import sys
import json
from datetime import datetime, timezone

try:
    from pymongo import MongoClient, ASCENDING, TEXT
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False


def init_database(mongo_uri: str = "mongodb://localhost:27017", seed_file: str = "mongodb_seed.json"):
    print("=" * 60)
    print("Radar Cívico - Conexão e Inicialização do MongoDB")
    print("=" * 60)

    if not HAS_PYMONGO:
        print("[ERRO] pymongo não está instalado. Execute: pip install pymongo")
        return False

    if not os.path.exists(seed_file):
        print(f"[ERRO] Arquivo de semente '{seed_file}' não encontrado. Execute 'python scraper.py' primeiro.")
        return False

    with open(seed_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    collections_data = data.get("collections", {})
    candidates = collections_data.get("candidates", [])
    cities = collections_data.get("cities", [])
    states = collections_data.get("states", [])

    print(f"Lidos da semente: {len(candidates)} candidatos, {len(cities)} cidades, {len(states)} estados.")
    print(f"Tentando conectar ao MongoDB em: {mongo_uri} ...")

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        # Ping
        client.admin.command("ping")
        db = client["radar_civico"]
        print("[OK] Conexão estabelecida com sucesso!")

        # 1. Popula candidates
        cand_col = db["candidates"]
        cand_upserted = 0
        for cand in candidates:
            cand_col.update_one({"_id": cand["_id"]}, {"$set": cand}, upsert=True)
            cand_upserted += 1
        
        # Cria índices
        cand_col.create_index([("cargo", ASCENDING), ("uf", ASCENDING)])
        cand_col.create_index([("cidade", ASCENDING)])
        cand_col.create_index([("tags", ASCENDING)])
        cand_col.create_index([
            ("n", TEXT), 
            ("perfil", TEXT), 
            ("propostas_destaque.saude", TEXT), 
            ("propostas_destaque.seguranca", TEXT), 
            ("propostas_destaque.educacao", TEXT)
        ], name="CandidatesSearchIndex")
        print(f"[OK] {cand_upserted} candidatos gravados/atualizados na coleção 'candidates'.")

        # 2. Popula cities
        city_col = db["cities"]
        for c in cities:
            city_col.update_one({"_id": c["_id"]}, {"$set": c}, upsert=True)
        city_col.create_index([("id", ASCENDING)], unique=True)
        city_col.create_index([("uf", ASCENDING)])
        print(f"[OK] {len(cities)} cidades gravadas na coleção 'cities'.")

        # 3. Popula states
        st_col = db["states"]
        for s in states:
            st_col.update_one({"_id": s["_id"]}, {"$set": s}, upsert=True)
        st_col.create_index([("uf", ASCENDING)], unique=True)
        print(f"[OK] {len(states)} estados gravados na coleção 'states'.")

        # Registro de log de auditoria
        db["system_logs"].insert_one({
            "action": "database_seed_init",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "candidates_count": len(candidates),
            "status": "ready"
        })

        print("\n[SUCESSO] Banco de dados 'radar_civico' inicializado e pronto para uso no MongoDB!")
        return True

    except Exception as e:
        print(f"\n[AVISO] Não foi possível conectar ao servidor MongoDB em {mongo_uri}:")
        print(f"        Detalhe: {e}")
        print("\n-> O frontend e a API continuam funcionando 100% lendo diretamente o arquivo 'mongodb_seed.json'.")
        print("-> Quando o MongoDB estiver rodando, execute 'python init_mongo.py' para carregar os dados no banco.")
        return False


if __name__ == "__main__":
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    init_database(mongo_uri=uri)
