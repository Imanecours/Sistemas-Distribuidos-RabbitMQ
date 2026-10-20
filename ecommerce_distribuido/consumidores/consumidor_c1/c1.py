import pika

def esperar_promocao():
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    canal = connection.channel()
    canal.exchange_declare(exchange='Promoções', exchange_type='topic')

    fila = canal.queue_declare('fila.C1', exclusive=True)
    nome_fila = fila.method.queue
    binding_keys = ['promocao.categoria.A','promocao.categoria.B']

    for key in binding_keys:
        canal.queue_bind(exchange='Promoções', queue=nome_fila, routing_key=key)

    print(' -- Esperando promoções --')

    def callback(canal, metodo, cabecalho, msg):
        print(f"{metodo.routing_key}: {msg}")

    canal.basic_consume(queue=nome_fila, on_message_callback=callback, auto_ack=True)
    try:
        canal.start_consuming()
    except KeyboardInterrupt:
        print("\nencerrando o consumidor...")
        connection.close()

if __name__ == '__main__':
    esperar_promocao()