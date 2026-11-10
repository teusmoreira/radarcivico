import json
import sys
from pymongo import MongoClient

print("A iniciar o processo de importação...")

try:
  # 1. Conexão ao MongoDB Atlas
  uri = "mongodb+srv://mathusca123costamoreira_db_user:FCCdzN7SGNxj5eVZ@cluster0.kyqv4xl.mongodb.net/"
  client = MongoClient(uri)

  db = client["radar_civico"]
  collection = db["candidatos"]

  # 2. Leitura do ficheiro candidates.json
  with open("candidates.json", "r", encoding="utf-8") as f:
    data = json.load(f)

  # 3. Inserção dos dados
  if isinstance(data, list):
    resultado = collection.insert_many(data)
    print(
        f" Sucesso! Foram inseridos {len(resultado.inserted_ids)} documentos na coleção 'candidatos'."
    )
  else:
    resultado = collection.insert_one(data)
    print(" Sucesso! Documento único inserido com sucesso.")

except Exception as e:
  print(f" Ocorreu um erro durante a importação: {e}")