import base64
import json
import threading
import pika
import random
import time
import rsa
import requests
from servico_email import send_email

# Lista de clientes cadastrados
cadastros = []

# Caminho corrigido para a chave
with open('ecommerce/ms_promocoes/chaves_publicas/ms_principal_publica.pem', 'rb') as f:
    chave_publica_msprincipal = rsa.PublicKey.load_pkcs1(f.read())

def publicar_promocao():
    try:
        
        resposta = requests.get('http://localhost:5000/produtos')
        lista_produtos = resposta.json()
        
        if not lista_produtos:
            return

        item_promo = random.choice(lista_produtos)
        desconto = random.choice([10, 20, 30, 50])
        
        notificar_clientes_promocao(item_promo, desconto)
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar produtos do MS Principal: {e}")

def processar_mensagem(canal, metodo, cabecalho, msg):
    if cabecalho.headers is None or 'Signature' not in cabecalho.headers:
        print("Mensagem recebida sem assinatura")
        return

    assinatura_texto = cabecalho.headers['Signature']
    assinatura_bytes = base64.b64decode(assinatura_texto.encode('utf-8'))

    try: 
        rsa.verify(msg, assinatura_bytes, chave_publica_msprincipal)
        evento = json.loads(msg)
        
        if metodo.routing_key == 'interesse.promocao':
            # Pegamos exatamente os nomes que o MS Principal enviou
            cadastros.append({
                "email": evento['email'], 
                "categorias": evento['categorias']
            })
            print(f"\n[PROMOÇÕES] Novo cliente cadastrado: {evento['email']} - Interesses: {evento['categorias']}")

    except rsa.VerificationError:
        print("Assinatura inválida")

def notificar_clientes_promocao(item_promo, desconto):
    for cadastro in cadastros:
        # Verifica se o cliente marcou a categoria do produto sorteado
        if item_promo['categoria'] in cadastro['categorias']:
            print(f"> Enviando para {cadastro['email']} promoção de {item_promo['nome']} com desconto de {desconto}%")
            
            # ATENÇÃO: Só descomente a linha abaixo se o seu colega te passou o arquivo .env com a chave da API Resend!
            # send_email(cadastro['email'], item_promo, desconto)

def iniciar_consumidor(): 
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    canal = connection.channel()
    canal.exchange_declare(exchange='eCommerce', exchange_type='direct')
    fila = canal.queue_declare(queue='fila_promocoes')
    nome_fila = fila.method.queue

    canal.queue_bind(exchange='eCommerce', queue=nome_fila, routing_key='interesse.promocao')
    canal.basic_consume(queue=nome_fila, on_message_callback=processar_mensagem, auto_ack=True)
    canal.start_consuming()

if __name__ == '__main__':
    thread_escuta = threading.Thread(target=iniciar_consumidor, daemon=True)
    thread_escuta.start()
    
    print("[PROMOÇÕES] Iniciado. Esperando cadastros...")
    
    while True:
        publicar_promocao()
        time.sleep(15)