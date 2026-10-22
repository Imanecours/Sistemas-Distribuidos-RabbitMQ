from flask import Flask, jsonify, request
from flask_cors import CORS
import uuid
import os

app = Flask(__name__)
CORS(app)
pagamentos_pendentes = {}
URL_CONFIRMA_PAGAMENTO = os.getenv(
    'URL_CONFIRMA_PAGAMENTO',
    'http://localhost:8000/confirma_pagamento.html',
)
URL_WEBHOOK = os.getenv(
    'URL_WEBHOOK_PAGAMENTO',
    'http://localhost:5002/webhook/pagamento',
)

@app.route('/pagamento', methods=['GET'])
def enviar_dados():
    token = uuid.uuid4().hex
    pagamentos_pendentes[token] = pedido
    webhook = f'{URL_WEBHOOK}/{token}'
    link_pagamento = f'{URL_CONFIRMA_PAGAMENTO}?webhook={quote(webhook, safe="")}'
    resposta = {
        "msg": "Olá do servidor externo!",
        "status": 200
    }
    return jsonify(resposta)

if __name__ == '__main__':
    # host='0.0.0.0' permite conexões de fora da sua máquina
    app.run(host='0.0.0.0', port=8000)