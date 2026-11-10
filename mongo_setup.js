/**
 * Radar Cívico - Script de Configuração e Importação para MongoDB
 * 
 * Como executar no terminal do mongosh:
 *   mongosh "mongodb://localhost:27017/radar_civico" mongo_setup.js
 * 
 * Ou utilizando o mongoimport oficial:
 *   mongoimport --db radar_civico --collection candidates --file candidates.json --jsonArray --upsertFields=_id
 */

const dbName = 'radar_civico';
const targetDb = db.getSiblingDB(dbName);

print("=== Inicializando Banco de Dados: " + dbName + " ===");

// 1. Criação de índices na coleção 'candidates'
targetDb.candidates.createIndex({ cargo: 1, uf: 1, cidade: 1 });
targetDb.candidates.createIndex({ uf: 1 });
targetDb.candidates.createIndex({ tags: 1 });
targetDb.candidates.createIndex({ 
    n: "text", 
    perfil: "text", 
    "propostas_destaque.saude": "text", 
    "propostas_destaque.seguranca": "text", 
    "propostas_destaque.educacao": "text" 
}, { 
    weights: { 
        "propostas_destaque.saude": 5, 
        "propostas_destaque.seguranca": 5, 
        "propostas_destaque.educacao": 5, 
        n: 3, 
        perfil: 2 
    },
    name: "TextSearchIndex"
});

// 2. Criação de índices na coleção 'cities'
targetDb.cities.createIndex({ id: 1 }, { unique: true });
targetDb.cities.createIndex({ uf: 1 });

// 3. Criação de índices na coleção 'states'
targetDb.states.createIndex({ uf: 1 }, { unique: true });

print("Índices criados com sucesso no banco " + dbName);
print("Para carregar os 24 candidatos e cidades completos, execute:");
print("  python init_mongo.py");
print("ou utilize mongoimport com o arquivo candidates.json");
