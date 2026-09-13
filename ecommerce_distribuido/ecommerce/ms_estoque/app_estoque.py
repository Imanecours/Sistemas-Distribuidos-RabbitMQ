import pika
import json
import rsa
import base64

import sys
from pathlib import Path
pasta_atual = Path(__file__).resolve().parent
pasta_produtos = (pasta_atual / ".." / ".." / "pasta_produtos").resolve()
sys.path.append(str(pasta_produtos))
from produtos import ESTOQUE

# carrega a chave pública do ms_principal para saber QUEM mandou o pedido:
with open('ms_estoque/chaves_publicas/ms_principal_publica.pem', 'rb') as f:
    chave_publica_principal = rsa.PublicKey.load_pkcs1(f.read())

# carrega a chave privada do ms_estoque (para ele assinar as proprias mensagens):
with open('ms_estoque/privada.pem', 'rb') as f:
    chave_privada_estoque = rsa.PrivateKey.load_pkcs1(f.read())

# função para enviar mensagem ASSINADA:

def publicar_evento(canal, routing_key, msg):
    msg_texto = json.dumps(msg) #transforma o dicionario em json
    msg_bytes = msg_texto.encode('utf-8') #transforma o json em bytes
    assinatura_bytes = rsa.sign(msg_bytes, chave_privada_estoque, 'SHA-256') #assina a mensagem com a chave privada do ms_estoque
    assinatura_texto = base64.b64encode(assinatura_bytes).decode('utf-8')

    #prepara cabeçalho com a assinatura:
    cabecalho = pika.BasicProperties(headers={'Signature': assinatura_texto})

    #publica a mensagem na exchange
    canal.basic_publish(exchange='eCommerce', routing_key=routing_key, body=msg_texto, properties=cabecalho)

    print(f"evento publicado (estoque): msg= {msg_texto}, assinatura= {assinatura_texto}, routing_key= {routing_key}, cabeçalho= {cabecalho}")

def processar_pedido(canal, metodo, cabecalho, msg):
    routing_key_recebida = metodo.routing_key

    if cabecalho.headers is None or 'Signature' not in cabecalho.headers:
        print("Mensagem recebida sem assinatura")
        return

    assinatura_texto = cabecalho.headers['Signature']
    assinatura_bytes = base64.b64decode(assinatura_texto.encode('utf-8'))

    try: 
        #verifica a assinatura da mensagem recebida com a chave pública do ms_principal
        rsa.verify(msg, assinatura_bytes, chave_publica_principal)
        pedido = json.loads(msg)
        print(f"Assinatura verificada com sucesso para a mensagem recebida: {msg.decode('utf-8')}")

        if routing_key_recebida == 'pedido.criado':
            processar_novo_pedido(canal, pedido)

        elif routing_key_recebida == 'pedido.excluido':
            devolver_ao_estoque(pedido)

    except rsa.VerificationError:
        print("assinatura invalida")

def processar_novo_pedido(canal, pedido):
    id_pedido = pedido['id_pedido']
    produtos_pedidos = pedido['produtos']

    print(f"\nAnalisando disponibilidade para o Pedido #{id_pedido}")

    # verifica se tem estoque:
    tem_estoque = True
    for item in produtos_pedidos:
        produto_estoque = next((p for p in ESTOQUE if p['id_produto'] == item['id_produto']), None)
        if not produto_estoque or produto_estoque['quantidade'] < item['quantidade']:
            tem_estoque = False
            break

    if tem_estoque:
        # dá baixa no estoque
        for item in produtos_pedidos:
            produto_estoque = next(p for p in ESTOQUE if p['id_produto'] == item['id_produto'])
            produto_estoque['quantidade'] -= item['quantidade']
            print(f"tem estoque; sai produto {produto_estoque['nome']} e sobram {produto_estoque['quantidade']}")

        publicar_evento(canal, 'pedido.estoque_ok', pedido) #publica evento avisando que o estoque está ok

    else:
        publicar_evento(canal, 'estoque.indisponivel', pedido)  


def devolver_ao_estoque(pedido):
    # repoe quantidade
    for item in pedido['produtos']:
        produto_estoque = next((p for p in ESTOQUE if p['id_produto'] == item['id_produto']), None)
        if produto_estoque:
            produto_estoque['quantidade'] += item['quantidade']
            print(f"[ESTOQUE] Devolvido {item['quantidade']}x do produto {produto_estoque['nome']} ao estoque")


def iniciar_consumidor():
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    channel = connection.channel()

    
    channel.exchange_declare(exchange='eCommerce', exchange_type='direct')
    fila = channel.queue_declare(queue='fila_estoque') #cria fila exclusiva para o estoque
    nome_fila = fila.method.queue

    # o estoque precisa escutar dois eventos, então fazemos dois bindings na mesma fila
    channel.queue_bind(exchange='eCommerce', queue=nome_fila, routing_key='pedido.criado')
    channel.queue_bind(exchange='eCommerce', queue=nome_fila, routing_key='pedido.excluido')
    print('[ESTOQUE] Inicializado. Esperando eventos de pedidos...')
    
    channel.basic_consume(queue=nome_fila, on_message_callback=processar_pedido, auto_ack=True)
    channel.start_consuming()

if __name__ == '__main__':
    iniciar_consumidor()