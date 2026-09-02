import pika
import json
import rsa
import base64

# Carrega a chave pública do MS Principal 
with open('ms_estoque/chaves_publicas/ms_principal_publica.pem', 'rb') as f:
    chave_publica = rsa.PublicKey.load_pkcs1(f.read())

def processar_pedido(ch, method, properties, body):

    # Verifica se o envelope da mensagem possui cabeçalhos e a assinatura
    if properties.headers is None or 'Signature' not in properties.headers:
        print("Mensagem sem assinatura, descartando o evento")
        return 

    # Extrai a assinatura do cabeçalho e converte de Base64 para bytes
    assinatura_texto = properties.headers['Signature']
    assinatura_bytes = base64.b64decode(assinatura_texto)

    try:
        # Verifica a assinatura digital usando a chave pública do remetente
        # A função rsa.verify compara o hash do "body" com a assinatura
        rsa.verify(body, assinatura_bytes, chave_publica)

        pedido = json.loads(body)
        print(f"Assinatura valida, verificando o estoque do pedido : {pedido['id_pedido']}...")

    except rsa.VerificationError:
        print("Assinatura inválida, descartando o evento")

def iniciar_consumidor():

    credenciais = pika.PlainCredentials('admin', 'admin123')
    
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    channel = connection.channel()

    channel.exchange_declare(exchange='eCommerce', exchange_type='direct')

    fila = channel.queue_declare(queue='fila_estoque')
    nome_fila = fila.method.queue

    channel.queue_bind(exchange='eCommerce', queue=nome_fila, routing_key='pedido.criado')

    print('Esperando pedidos')
    
    channel.basic_consume(queue=nome_fila, on_message_callback=processar_pedido, auto_ack=True)
    channel.start_consuming()

if __name__ == '__main__':
    iniciar_consumidor()