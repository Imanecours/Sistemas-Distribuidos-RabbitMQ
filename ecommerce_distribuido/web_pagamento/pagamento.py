import os
from pathlib import Path
from urllib.parse import urlencode, urlparse

from flask import Flask, jsonify, redirect, request, send_from_directory
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

PASTA_PAGAMENTO = Path(__file__).resolve().parent
URL_PAGINA_PAGAMENTO = os.getenv(
    'URL_PAGINA_PAGAMENTO',
    'http://localhost:8000/confirma_pagamento.html',
)
URL_WEBHOOK_PADRAO = os.getenv(
    'URL_WEBHOOK_PAGAMENTO',
    'http://localhost:5002/webhook/pagamento',
)


def obter_dados_requisicao():
    dados = request.get_json(silent=True)
    if isinstance(dados, dict):
        return dados
    return request.form.to_dict() or request.args.to_dict()


def link_valido(link):
    partes = urlparse(link)
    return partes.scheme in ('http', 'https') and bool(partes.netloc)


@app.post('/pagamento')
def gerar_link_pagamento():
    dados = obter_dados_requisicao()
    id_pedido = dados.get('id_pedido')

    if isinstance(id_pedido, bool) or id_pedido is None:
        return jsonify({'erro': 'id_pedido é obrigatório'}), 400

    try:
        id_pedido = int(id_pedido)
    except (TypeError, ValueError):
        return jsonify({'erro': 'id_pedido deve ser um número inteiro'}), 400

    if id_pedido <= 0:
        return jsonify({'erro': 'id_pedido deve ser positivo'}), 400

    webhook = dados.get('webhook')
    if webhook is None:
        webhook = f'{URL_WEBHOOK_PADRAO}/{id_pedido}'
    if not isinstance(webhook, str) or not link_valido(webhook):
        return jsonify({'erro': 'webhook deve ser uma URL válida'}), 400

    link_pagamento = f'{URL_PAGINA_PAGAMENTO}?{urlencode({"webhook": webhook, "id_pedido": id_pedido})}'
    return jsonify({
        'id_pedido': id_pedido,
        'url': link_pagamento,
        'link_pagamento': link_pagamento,
    }), 200


@app.route('/confirma_pagamento.html', methods=['GET', 'POST'])
def pagina_pagamento():
    if request.method == 'POST':
        dados = obter_dados_requisicao()
        link = dados.get('link')
        if not isinstance(link, str) or not link_valido(link):
            return jsonify({'erro': 'link deve ser uma URL válida'}), 400
        return redirect(link, code=303)

    return send_from_directory(PASTA_PAGAMENTO, 'confirma_pagamento.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
