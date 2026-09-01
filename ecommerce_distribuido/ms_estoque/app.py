import pika
import json

def processar_pedido(ch, method, properties, body):
    pedido = json.loads(body)
    print(f" Recebido {method.routing_key} : Verificando o estoque do pedido : {pedido['id_pedido']}...")


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