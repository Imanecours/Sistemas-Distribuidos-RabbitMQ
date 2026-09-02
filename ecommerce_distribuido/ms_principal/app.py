import pika
import json
import rsa
import base64

def enviar_pedido():

    with open('ms_principal/privada.pem', 'rb') as f:
        chave_privada = rsa.PrivateKey.load_pkcs1(f.read())
        
    credenciais = pika.PlainCredentials('admin', 'admin123')

    connection = pika.BlockingConnection(pika.ConnectionParameters(credentials=credenciais))
    channel = connection.channel()

    channel.exchange_declare(exchange='eCommerce', exchange_type='direct')

    pedido = {"id_pedido": 12345,"produtos": [{"id_produto": 1, "quantidade": 2}],"status": "criado"}
    mensagem_texto = json.dumps(pedido)
    mensagem_bytes = mensagem_texto.encode('utf-8')

    # Cryptografia
    # A função sign() gera o hash (SHA-256) e o assina com a chave privada
    assinatura_bytes = rsa.sign(mensagem_bytes, chave_privada, 'SHA-256')
    # Convertimos a assinatura em base64 para poder enviá-la como string
    assinatura_texto = base64.b64encode(assinatura_bytes).decode('utf-8')

    # Propriedades da mensagem com a assinatura
    propriedades = pika.BasicProperties(headers={'Signature': assinatura_texto})

    routing_key = 'pedido.criado'
    channel.basic_publish(exchange='eCommerce',routing_key=routing_key,body=mensagem_texto,properties=propriedades)
    
    print(f"Enviado '{routing_key}': {pedido}")
    connection.close()

if __name__ == '__main__':
    enviar_pedido()