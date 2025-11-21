from flask import Flask, jsonify
import requests
from dotenv import load_dotenv
import os
import math
import csv

load_dotenv()

app = Flask(__name__)

CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]

LAT = 41.219215
LON = -8.230035

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "voos.csv")
LOG_FILE = os.path.join(BASE_DIR, "logs.txt")  # Caminho absoluto do logs.txt

def get_access_token():
    url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(url, data=payload, headers=headers, timeout=10)
    res.raise_for_status()
    return res.json().get("access_token")

def distancia(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def carregar_callsigns_csv():
    callsigns = set()
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                callsigns.add(row["callsign"].strip())
    return callsigns

def registar_log(callsign):
    # Criar ficheiro vazio se não existir
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            pass

    # Ler logs existentes
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs_existentes = {line.strip() for line in f}

    # Escrever novo callsign se ainda não estiver
    if callsign not in logs_existentes:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{callsign}\n")
        print(f"[LOG] Adicionado callsign desconhecido: {callsign}", flush=True)
    else:
        print(f"[DEBUG] Callsign já existente no log: {callsign}", flush=True)

@app.route("/aviao")
def aviao_proximo():
    try:
        token = get_access_token()
    except Exception as e:
        return jsonify({"erro": "Erro ao obter token", "detalhes": str(e)}), 500

    headers = {"Authorization": f"Bearer {token}"}
    delta = 0.2
    url = (
        f"https://opensky-network.org/api/states/all?"
        f"lamin={LAT - delta}&lomin={LON - delta}&lamax={LAT + delta}&lomax={LON + delta}"
    )

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        return jsonify({"erro": "Erro ao obter dados da API", "detalhes": str(e)}), 500

    states = data.get("states", [])
    if not states:
        return jsonify({"erro": "Nenhum avião encontrado"})

    callsigns_conhecidos = carregar_callsigns_csv()
    aviao_mais_proximo = None
    menor_distancia = float("inf")

    for plane in states:
        lat = plane[6]
        lon = plane[5]
        if lat is not None and lon is not None:
            dist = distancia(LAT, LON, lat, lon)
            if dist < menor_distancia:
                menor_distancia = dist
                aviao_mais_proximo = plane

    if not aviao_mais_proximo:
        return jsonify({"erro": "Não foi possível determinar o avião mais próximo"})

    callsign = aviao_mais_proximo[1].strip() if aviao_mais_proximo[1] else "Desconhecido"
    print(f"[INFO] Avião mais próximo: {callsign}")

    origem = destino = airline = modelo = "Desconhecido"

    # Verifica se está no CSV
    if callsign in callsigns_conhecidos:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["callsign"].strip() == callsign:
                    origem = row.get("origin", "Desconhecido")
                    destino = row.get("destination", "Desconhecido")
                    airline = row.get("airline", "Desconhecido")
                    modelo = row.get("model", "Desconhecido")
                    break
    else:
        registar_log(callsign)

    return jsonify({
        "callsign": callsign,
        "origin": origem,
        "destination": destino,
        "airline": airline,
        "model": modelo
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7007))
    app.run(host="0.0.0.0", port=port)