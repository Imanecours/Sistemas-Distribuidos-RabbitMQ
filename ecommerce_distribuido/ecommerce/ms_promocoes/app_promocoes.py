import pika
import random
import time

import sys
from pathlib import Path
pasta_atual = Path(__file__).resolve().parent
pasta_produtos = (pasta_atual / ".." / ".." / "pasta_produtos").resolve()
sys.path.append(str(pasta_produtos))
from produtos import ESTOQUE

def publicar_promocao():
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    canal = connection.channel()
    canal.exchange_declare(exchange='Promoções', exchange_type='topic')

    item_promo = random.choice(ESTOQUE)
    routing_key = f"promocao.categoria.{item_promo['categoria']}"
    valores = [90, 80, 70, 60]
    desconto = random.choice(valores)
    msg_texto = f"{item_promo['nome']} custando {desconto}% do valor original."

    canal.basic_publish(exchange='Promoções', routing_key=routing_key, body=msg_texto)
    connection.close()

if __name__ == '__main__':
    while True:
        publicar_promocao()
        time.sleep(15)