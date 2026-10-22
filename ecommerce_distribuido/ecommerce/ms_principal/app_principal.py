import pika
import json
import rsa
import base64
import threading

import requests
import queue 
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

URL_MS_ESTOQUE = 'http://localhost:5001/produtos'

@app.route('/produtos', methods=['GET'])
def obter_produtos():
    try:
        resposta = requests.get(URL_MS_ESTOQUE, timeout=3)
        return jsonify(resposta.json()), resposta.status_code
    except requests.exceptions.RequestException:
        return jsonify({"erro": "ms_estoque indisponivel"}), 503

@app.route('/promocoes', methods=['POST'])
def cadastrar_promocao():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({"erro": "corpo da requisicao invalido"}), 400

    email = dados.get('email')
    categorias = dados.get('categorias')
    if not isinstance(email, str) or not email.strip():
        return jsonify({"erro": "email obrigatorio"}), 400
    if not isinstance(categorias, list):
        return jsonify({"erro": "categorias deve ser uma lista"}), 400

    inscricao = {
        "email": email.strip(),
        "categorias": categorias
    }
    publicar_evento('interesse.promocao', inscricao)

    return jsonify({
        "status": "inscricao.realizada",
        "mensagem": "Inscricao em promocoes realizada com sucesso"
    }), 201

@app.route('/comprar', methods=['POST'])
def comprar():
    dados_pedido = request.get_json()
    
    id_pedido = len(meus_pedidos) + 1
    
    novo_pedido = {
        "id_pedido": id_pedido,
        "produtos": [
            {
                "id_produto": dados_pedido['id_produto'], 
                "quantidade": dados_pedido['quantidade']
            }
        ],
        "status": "pedido.criado",
        "cliente": dados_pedido.get('cliente', 'Desconhecido')
    }
    
    meus_pedidos[id_pedido] = novo_pedido
    
    publicar_evento('pedido.criado', novo_pedido)
    
    print(f"Pedido {id_pedido} criado e enviado")
    
    return jsonify({
        "status": "pedido.criado", 
        "mensagem": "Pedido criado com sucesso",
        "id_pedido": id_pedido
    }), 201

@app.route('/stream')
def stream():
    def gerador():
        while True:
            try:

                notificacao = fila_notificacoes.get(timeout=1)

                yield f"data: {json.dumps(notificacao)}\n\n"
            except queue.Empty:
                # manda um sinal vazio so pra conexao nao cair 
                yield ": keep-alive\n\n"

    return Response(gerador(), mimetype='text/event-stream')

@app.route('/pedido/<int:id_pedido>', methods=['DELETE'])
def cancelar_pedido(id_pedido):
    if id_pedido in meus_pedidos:
        pedido = meus_pedidos[id_pedido]
        
        pedido['status'] = 'pedido.excluido'
        
        publicar_evento('pedido.excluido', pedido)
        
        fila_notificacoes.put({"id_pedido": id_pedido, "status": "pedido.excluido"})
        
        print(f"Pedido {id_pedido} cancelado pelo usuario.")
        return jsonify({"mensagem": "Pedido cancelado com sucesso"}), 200
    else:
        return jsonify({"erro": "Pedido nao encontrado"}), 404

# #carregar a chave privada do ms principal para ele assinar os pedidos
# with open('ecommerce_distribuido/ecommerce/ms_principal/ms_principal_privada.pem', 'rb') as f:
#     chave_privada = rsa.PrivateKey.load_pkcs1(f.read())

# # carregar as chaves publicas dos outros microsservicos para validar quem mandou
# with open('ecommerce_distribuido/ecommerce/chaves_publicas/ms_estoque_publica.pem', 'rb') as f:
#     chave_pub_estoque = rsa.PublicKey.load_pkcs1(f.read())
    
# with open('ecommerce_distribuido/ecommerce/chaves_publicas/ms_pagamento_publica.pem', 'rb') as f:
#     chave_pub_pagamento = rsa.PublicKey.load_pkcs1(f.read())
    
# with open('ecommerce_distribuido/ecommerce/chaves_publicas/ms_entrega_publica.pem', 'rb') as f:
#     chave_pub_entrega = rsa.PublicKey.load_pkcs1(f.read())

meus_pedidos = {}
fila_notificacoes = queue.Queue() # fila segura para as threads conversarem

def publicar_evento(routing_key, msg):
    # abrimos uma conexao rapida aqui para evitar erros do pika com threads
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    canal = connection.channel()
    canal.exchange_declare(exchange='eCommerce', exchange_type='direct')

    msg_texto = json.dumps(msg)
    msg_bytes = msg_texto.encode('utf-8')

    assinatura_bytes = rsa.sign(msg_bytes, chave_privada, 'SHA-256')
    assinatura_texto = base64.b64encode(assinatura_bytes).decode('utf-8')
    cabecalho = pika.BasicProperties(headers={'Signature': assinatura_texto})

    canal.basic_publish(exchange='eCommerce', routing_key=routing_key, body=msg_texto, properties=cabecalho)
    connection.close()

def fw(canal, metodo, cabecalho, msg):
    if cabecalho.headers is None or 'Signature' not in cabecalho.headers:
        return

    assinatura_texto = cabecalho.headers['Signature']
    assinatura_bytes = base64.b64decode(assinatura_texto.encode('utf-8'))
    routing_key = metodo.routing_key

    try:
        # verifica de quem veio a mensagem para usar a chave publica certa
        if routing_key in ['pedido.estoque_ok', 'estoque.indisponivel']:
            rsa.verify(msg, assinatura_bytes, chave_pub_estoque)
        elif routing_key in ['pagamento.aguardando', 'pagamento.aprovado', 'pagamento.recusado']:
            rsa.verify(msg, assinatura_bytes, chave_pub_pagamento)
        elif routing_key == 'pedido.enviado':
            rsa.verify(msg, assinatura_bytes, chave_pub_entrega)
        else:
            return

        pedido = json.loads(msg)
        id_pedido = pedido['id_pedido']

        if id_pedido in meus_pedidos:
            # atualiza o status do pedido na memoria
            meus_pedidos[id_pedido]['status'] = routing_key
            print(f"\nstatus do pedido {id_pedido} atualizado para: {routing_key}")

            #envia a novidade para o react via fila de notificacoes
            notificacao = {"id_pedido": id_pedido, "status": routing_key}
            if routing_key == 'pagamento.aguardando':
                notificacao["link_pagamento"] = pedido.get("link_pagamento")
            fila_notificacoes.put(notificacao)
            # o documento exige publicar pedido.excluido se o estoque faltar ou pagamento for recusado
            if routing_key in ['pagamento.recusado']:
                publicar_evento('pedido.excluido', meus_pedidos[id_pedido])

    except rsa.VerificationError:
        print("\nassinatura invalida recebida.")

def escutar_rabbit():
    # essa funcao vai rodar em segundo plano sem parar
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    channel = connection.channel()
    channel.exchange_declare(exchange='eCommerce', exchange_type='direct')
    
    fila = channel.queue_declare(queue='fila_principal')
    nome_fila = fila.method.queue

    # o ms principal precisa escutar todos esses eventos
    eventos = [
        'pagamento.aprovado', 'pagamento.recusado', 
        'pagamento.aguardando',
        'pedido.enviado', 'pedido.estoque_ok', 'estoque.indisponivel'
    ]
    for evento in eventos:
        channel.queue_bind(exchange='eCommerce', queue=nome_fila, routing_key=evento)

    channel.basic_consume(queue=nome_fila, on_message_callback=processar_mensagem, auto_ack=True)
    channel.start_consuming()

if __name__ == '__main__':
    # cria a thread paralela. daemon=True faz ela desligar quando o programa principal fechar.
    thread_consumidor = threading.Thread(target=escutar_rabbit, daemon=True)
    thread_consumidor.start()
    
    app.run(port=5000)
