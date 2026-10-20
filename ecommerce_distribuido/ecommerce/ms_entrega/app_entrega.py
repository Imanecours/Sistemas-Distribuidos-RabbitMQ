import pika
import json
import rsa
import base64
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# obter a chave publica do microsservico produtor (MS Pagamento)
with open(os.path.join(BASE_DIR, 'chaves_publicas', 'ms_pagamento_publica.pem'), 'rb') as f:
    chave_publica_pagamento = rsa.PublicKey.load_pkcs1(f.read())

# para assinar as mensagens com a propria chave
with open(os.path.join(BASE_DIR, 'ms_entrega_privada.pem'), 'rb') as f:
    chave_privada_entrega = rsa.PrivateKey.load_pkcs1(f.read())

def publicar_evento(canal, routing_key, msg):
    msg_texto = json.dumps(msg)
    msg_bytes = msg_texto.encode('utf-8')

    assinatura_bytes = rsa.sign(msg_bytes, chave_privada_entrega, 'SHA-256')
    assinatura_texto = base64.b64encode(assinatura_bytes).decode('utf-8')

    # incluir a assinatura digital no envelope
    cabecalho = pika.BasicProperties(headers={'Signature': assinatura_texto})

    canal.basic_publish(exchange='eCommerce', routing_key=routing_key, body=msg_texto, properties=cabecalho)
    print(f"o evento '{routing_key}' foi publicado com assinatura.")

def processar_mensagem(canal, metodo, cabecalho, msg):
    # descartar se a mensagem vier sem assinatura
    if cabecalho.headers is None or 'Signature' not in cabecalho.headers:
        print("mensagem recebida sem assinatura.")
        return

    assinatura_texto = cabecalho.headers['Signature']
    assinatura_bytes = base64.b64decode(assinatura_texto.encode('utf-8'))

    try: 
        # verificar autenticidade usando a chave do ms pagamento
        rsa.verify(msg, assinatura_bytes, chave_publica_pagamento)
        
        pedido = json.loads(msg)
        
        if metodo.routing_key == 'pagamento.aprovado':
            processar_entrega(canal, pedido)

    except rsa.VerificationError:
        print("assinatura invalida.")

def processar_entrega(canal, pedido):
    id_pedido = pedido['id_pedido']
    print(f"\nemitindo nota e preparando entrega para o pedido #{id_pedido}")
    
    # simulando o tempo de emissao de nota
    time.sleep(2)
    
    print(f"pedido #{id_pedido} despachado.")
    pedido['status'] = 'enviado'
    
    publicar_evento(canal, 'pedido.enviado', pedido)

def iniciar_consumidor():
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    channel = connection.channel()

    channel.exchange_declare(exchange='eCommerce', exchange_type='direct')
    
    fila = channel.queue_declare(queue='fila_entrega')
    nome_fila = fila.method.queue

    # o servico vai consumir apenas pagamentos aprovados
    channel.queue_bind(exchange='eCommerce', queue=nome_fila, routing_key='pagamento.aprovado')
    
    print('aguardando pagamentos aprovados')
    
    channel.basic_consume(queue=nome_fila, on_message_callback=processar_mensagem, auto_ack=True)
    channel.start_consuming()

if __name__ == '__main__':
    iniciar_consumidor()