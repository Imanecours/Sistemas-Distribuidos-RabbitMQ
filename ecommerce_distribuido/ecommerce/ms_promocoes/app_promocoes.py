import base64
import json
import threading

import pika
import random
import time
import rsa

import sys
from pathlib import Path
pasta_atual = Path(__file__).resolve().parent
pasta_produtos = (pasta_atual / ".." / ".." / "pasta_produtos").resolve()
sys.path.append(str(pasta_produtos))
from produtos import ESTOQUE
from email import send_email

# lista de cadastros para receber promoções (email + produtos de interesse):
#cadastros = [{"email": [], "produtos_interesse": []}]  
cadastros = []

# obtém a chave pública do ms Principal:
with open('chaves_publicas/ms_principal_publica.pem', 'rb') as f:
    chave_publica_msprincipal = rsa.PublicKey.load_pkcs1(f.read())


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
    notificar_clientes_promocao(item_promo, desconto)

def processar_mensagem(canal, metodo, cabecalho, msg):

    if cabecalho.headers is None or 'Signature' not in cabecalho.headers:
        print("mensagem recebida sem assinatura")
        return

    assinatura_texto = cabecalho.headers['Signature']
    assinatura_bytes = base64.b64decode(assinatura_texto.encode('utf-8'))

    try: 
        # verificar a assinatura digital do evento e confirmar a autenticidade e a integridade da mensagem
        rsa.verify(msg, assinatura_bytes, chave_publica_msprincipal)
        
        # processar o evento 
        evento = json.loads(msg)
        
        if metodo.routing_key == 'interesse.promocao':
            cadastros.append({"email": evento['emails'], "produtos_interesse": evento['id_produto']})

    except rsa.VerificationError:
        print("Assinatura inválida")

def notificar_clientes_promocao(item_promo, desconto):
    #itera sobre "cadastros" e, se o cliente tem interesse no produto, envia um email com o desconto.
    for cadastro in cadastros:
        if item_promo['id'] in cadastro['produtos_interesse']:
            print(f"Enviando{cadastro['email']} com promoção de {item_promo['nome']} com desconto de {desconto}%")
            send_email(cadastro['email'], item_promo, desconto)



def iniciar_consumidor(): 
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    canal = connection.channel()
    canal.exchange_declare(exchange='eCommerce', exchange_type='direct')
    fila = canal.queue_declare(queue='fila_promocoes')
    nome_fila = fila.method.queue

    routing_key = 'interesse.promocao'

    canal.queue_bind(exchange='eCommerce', queue=nome_fila, routing_key=routing_key)
    canal.basic_consume(queue=nome_fila, on_message_callback=processar_mensagem, auto_ack=True)
    canal.start_consuming()


if __name__ == '__main__':
    # cria a thread paralela. daemon=True faz ela desligar quando o programa principal fechar.
    thread_escuta = threading.Thread(target=iniciar_consumidor, daemon=True)
    thread_escuta.start()
    
    # publica promocoes periodicamente:
    while(True):
        publicar_promocao()
        time.sleep(10)  # espera 10 segundos antes de publicar a próxima promoção
