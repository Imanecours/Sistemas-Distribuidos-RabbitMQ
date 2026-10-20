import pika
import json
import rsa
import base64
import os
import threading
import uuid
from urllib.parse import quote
from urllib.request import urlopen

from flask import Flask, jsonify, request
from flask_cors import CORS

# obter a chave pública do microsserviço produtor (MS Estoque)
with open('chaves_publicas/ms_estoque_publica.pem', 'rb') as f:
    chave_publica_estoque = rsa.PublicKey.load_pkcs1(f.read())

# para asinar as mensagens 
with open('ms_pagamento_privada.pem', 'rb') as f:
    chave_privada_pagamento = rsa.PrivateKey.load_pkcs1(f.read())

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

def publicar_evento(canal, routing_key, msg):
    msg_texto = json.dumps(msg)
    msg_bytes = msg_texto.encode('utf-8')

    assinatura_bytes = rsa.sign(msg_bytes, chave_privada_pagamento, 'SHA-256')
    assinatura_texto = base64.b64encode(assinatura_bytes).decode('utf-8')

    # incluir a assinatura digital no campo Signature do envelope do evento
    cabecalho = pika.BasicProperties(headers={'Signature': assinatura_texto})

    canal.basic_publish(exchange='eCommerce', routing_key=routing_key, body=msg_texto, properties=cabecalho)
    print(f" o evento '{routing_key}' publicado com assinatura digital.")

def processar_mensagem(canal, metodo, cabecalho, msg):
    # caso a assinatura seja invalida, o evento vai ser descartado
    if cabecalho.headers is None or 'Signature' not in cabecalho.headers:
        print("Mensagem recebida sem assinatura.")
        return

    assinatura_texto = cabecalho.headers['Signature']
    assinatura_bytes = base64.b64decode(assinatura_texto.encode('utf-8'))

    try: 
        # verificar a assinatura digital do evento e confirmar a autenticidade e a integridade da mensagem
        rsa.verify(msg, assinatura_bytes, chave_publica_estoque)
        
        # processar o evento 
        pedido = json.loads(msg)
        
        if metodo.routing_key == 'pedido.estoque_ok':
            processar_pagamento(canal, pedido)

    except rsa.VerificationError:
        print("Assinatura inválida.")

def processar_pagamento(canal, pedido):
    id_pedido = pedido['id_pedido']
    print(f"\n Processando pagamento para o pedido #{id_pedido}")

    token = uuid.uuid4().hex
    pagamentos_pendentes[token] = pedido
    webhook = f'{URL_WEBHOOK}/{token}'
    link_pagamento = f'{URL_CONFIRMA_PAGAMENTO}?webhook={quote(webhook, safe="")}'

    try:
        # Confirma que a página de pagamento está acessível antes de avisar o cliente.
        with urlopen(link_pagamento, timeout=3):
            pass
    except OSError as erro:
        print(f"Não foi possível acessar a página de pagamento: {erro}")

    pedido_com_pagamento = {
        **pedido,
        'link_pagamento': link_pagamento,
    }
    publicar_evento(canal, 'pagamento.aguardando', pedido_com_pagamento)
    print(f"Link de pagamento criado para o pedido #{id_pedido}.")


@app.post('/webhook/pagamento/<token>')
def receber_confirmacao(token):
    pedido = pagamentos_pendentes.pop(token, None)
    if pedido is None:
        return jsonify({'erro': 'link de pagamento inválido ou expirado'}), 404

    dados = request.get_json(silent=True) or {}
    status = dados.get('status')
    if status not in ('aprovado', 'recusado'):
        pagamentos_pendentes[token] = pedido
        return jsonify({'erro': 'status de pagamento inválido'}), 400

    evento = f'pagamento.{status}'
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost', credentials=credenciais)
    )
    canal = connection.channel()
    canal.exchange_declare(exchange='eCommerce', exchange_type='direct')
    publicar_evento(canal, evento, pedido)
    connection.close()
    print(f"Pagamento {status} para o pedido #{pedido['id_pedido']}.")
    return jsonify({'status': evento}), 200


def iniciar_webhook():
    app.run(host='0.0.0.0', port=5002, threaded=True, use_reloader=False)

def iniciar_consumidor():
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    channel = connection.channel()

    channel.exchange_declare(exchange='eCommerce', exchange_type='direct')
    
    fila = channel.queue_declare(queue='fila_pagamento')
    nome_fila = fila.method.queue

    # o serviço vai consumir o evento pedido.estoque_ok.
    channel.queue_bind(exchange='eCommerce', queue=nome_fila, routing_key='pedido.estoque_ok')
    
    threading.Thread(target=iniciar_webhook, daemon=True).start()
    channel.basic_consume(queue=nome_fila, on_message_callback=processar_mensagem, auto_ack=True)
    channel.start_consuming()

if __name__ == '__main__':
    iniciar_consumidor()