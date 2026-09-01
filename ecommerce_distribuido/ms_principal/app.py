import pika
import json

def enviar_pedido():

    credenciais = pika.PlainCredentials('admin', 'admin123')

    connection = pika.BlockingConnection(pika.ConnectionParameters(credentials=credenciais))
    channel = connection.channel()

    channel.exchange_declare(exchange='eCommerce', exchange_type='direct')

    pedido = {
        "id_pedido": 12345,
        "produtos": [{"id_produto": 1, "quantidade": 2}],
        "status": "criado"
    }
    mensagem_json = json.dumps(pedido)

    routing_key = 'pedido.criado'
    channel.basic_publish(
        exchange='eCommerce',
        routing_key=routing_key,
        body=mensagem_json
    )
    
    print(f"Enviado '{routing_key}': {pedido}")
    connection.close()

if __name__ == '__main__':
    enviar_pedido()