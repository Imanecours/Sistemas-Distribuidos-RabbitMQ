import pika
import json
import rsa
import base64
import random

# obter a chave pública do microsserviço produtor (MS Estoque)
with open('chaves_publicas/ms_estoque_publica.pem', 'rb') as f:
    chave_publica_estoque = rsa.PublicKey.load_pkcs1(f.read())

# para asinar as mensagens 
with open('ms_pagamento_privada.pem', 'rb') as f:
    chave_privada_pagamento = rsa.PrivateKey.load_pkcs1(f.read())

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
    
    # aleatorio para saber se um pagamento foi aprovado ou recusado
    pagamento_aprovado = random.choice([True, False])

    if pagamento_aprovado:
        print(f"Pagamento aprovado para o pedido #{id_pedido}.")
        publicar_evento(canal, 'pagamento.aprovado', pedido)
    else:
        print(f"Pagamento recusado para o pedido #{id_pedido}.")
        publicar_evento(canal, 'pagamento.recusado', pedido)

def iniciar_consumidor():
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    channel = connection.channel()

    channel.exchange_declare(exchange='eCommerce', exchange_type='direct')
    
    fila = channel.queue_declare(queue='fila_pagamento')
    nome_fila = fila.method.queue

    # o serviço vai consumir o evento pedido.estoque_ok.
    channel.queue_bind(exchange='eCommerce', queue=nome_fila, routing_key='pedido.estoque_ok')
    
    channel.basic_consume(queue=nome_fila, on_message_callback=processar_mensagem, auto_ack=True)
    channel.start_consuming()

if __name__ == '__main__':
    iniciar_consumidor()