from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]

# Coordenadas fixas para testes
LAT = 41.351047
LON = -8.720682
RANGE_KM = 10

def get_access_token():
    token_url = "https://auth.opensky-network.org/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "audience": "https://opensky-network.org/api"
    }
    res = requests.post(token_url, json=payload)
    return res.json().get("access_token")

def get_planes(token):
    headers = {
        "Authorization": f"Bearer {token}"
    }
    lamax = LAT + 0.1
    lamin = LAT - 0.1
    lomax = LON + 0.1
    lomin = LON - 0.1

    url = f"https://opensky-network.org/api/states/all?lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}"
    res = requests.get(url, headers=headers)
    return res.json()

@app.route("/aviao")
def aviao_proximo():
    token = get_access_token()
    data = get_planes(token)

    states = data.get("states", [])
    if not states:
        return jsonify({"erro": "Nenhum avião encontrado"})

    # Vamos só pegar o primeiro avião para simplificar
    plane = states[0]
    return jsonify({
        "callsign": plane[1].strip(),
        "origin_country": plane[2],
        "latitude": plane[6],
        "longitude": plane[5],
        "altitude": plane[7]
    })

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)