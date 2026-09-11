import pika
import json
import rsa
import base64
import threading

# carregar a chave privada do ms principal para ele assinar os pedidos
with open('ms_principal/privada.pem', 'rb') as f:
    chave_privada = rsa.PrivateKey.load_pkcs1(f.read())

# carregar as chaves publicas dos outros microsservicos para validar quem mandou
with open('ms_principal/chaves_publicas/ms_estoque_publica.pem', 'rb') as f:
    chave_pub_estoque = rsa.PublicKey.load_pkcs1(f.read())
    
with open('ms_principal/chaves_publicas/ms_pagamento_publica.pem', 'rb') as f:
    chave_pub_pagamento = rsa.PublicKey.load_pkcs1(f.read())
    
with open('ms_principal/chaves_publicas/ms_entrega_publica.pem', 'rb') as f:
    chave_pub_entrega = rsa.PublicKey.load_pkcs1(f.read())

# banco de dados simulado
produtos = [
    {"id_produto": 1, "nome": "papel", "quantidade": 10, "preco": 3.00},
    {"id_produto": 2, "nome": "caneta", "quantidade": 50, "preco": 12.00},
    {"id_produto": 3, "nome": "lapis", "quantidade": 30, "preco": 20.00},
    {"id_produto": 4, "nome": "apontador", "quantidade": 30, "preco": 15.00}
]
meus_pedidos = {}

def publicar_evento(routing_key, msg):
    # abrimos uma conexao rapida aqui para evitar erros do pika com threads
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    canal = connection.channel()
    canal.exchange_declare(exchange='eCommerce', exchange_type='direct')

    msg_texto = json.dumps(msg)
    msg_bytes = msg_texto.encode('utf-8')

    assinatura_bytes = rsa.sign(msg_bytes, chave_privada, 'SHA-256')
    assinatura_texto = base64.b64encode(assinatura_bytes).decode('utf-8')
    cabecalho = pika.BasicProperties(headers={'Signature': assinatura_texto})

    canal.basic_publish(exchange='eCommerce', routing_key=routing_key, body=msg_texto, properties=cabecalho)
    connection.close()

def processar_mensagem(canal, metodo, cabecalho, msg):
    if cabecalho.headers is None or 'Signature' not in cabecalho.headers:
        return

    assinatura_texto = cabecalho.headers['Signature']
    assinatura_bytes = base64.b64decode(assinatura_texto.encode('utf-8'))
    routing_key = metodo.routing_key

    try:
        # verifica de quem veio a mensagem para usar a chave publica certa
        if routing_key in ['pedido.estoque_ok', 'estoque.indisponivel']:
            rsa.verify(msg, assinatura_bytes, chave_pub_estoque)
        elif routing_key in ['pagamento.aprovado', 'pagamento.recusado']:
            rsa.verify(msg, assinatura_bytes, chave_pub_pagamento)
        elif routing_key == 'pedido.enviado':
            rsa.verify(msg, assinatura_bytes, chave_pub_entrega)
        else:
            return

        pedido = json.loads(msg)
        id_pedido = pedido['id_pedido']

        if id_pedido in meus_pedidos:
            # atualiza o status do pedido na memoria
            meus_pedidos[id_pedido]['status'] = routing_key
            print(f"\nstatus do pedido {id_pedido} atualizado para: {routing_key}")
            
            # o documento exige publicar pedido.excluido se o estoque faltar ou pagamento for recusado
            if routing_key in ['estoque.indisponivel', 'pagamento.recusado']:
                publicar_evento('pedido.excluido', meus_pedidos[id_pedido])

            # apenas para manter o terminal organizado e mostrar a opcao novamente
            print("escolha uma opcao: ", end="", flush=True)

    except rsa.VerificationError:
        print("\nassinatura invalida recebida.")

def escutar_rabbit():
    # essa funcao vai rodar em segundo plano sem parar
    credenciais = pika.PlainCredentials('admin', 'admin123')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', credentials=credenciais))
    channel = connection.channel()
    channel.exchange_declare(exchange='eCommerce', exchange_type='direct')
    
    fila = channel.queue_declare(queue='fila_principal')
    nome_fila = fila.method.queue

    # o ms principal precisa escutar todos esses eventos
    eventos = [
        'pagamento.aprovado', 'pagamento.recusado', 
        'pedido.enviado', 'pedido.estoque_ok', 'estoque.indisponivel'
    ]
    for evento in eventos:
        channel.queue_bind(exchange='eCommerce', queue=nome_fila, routing_key=evento)

    channel.basic_consume(queue=nome_fila, on_message_callback=processar_mensagem, auto_ack=True)
    channel.start_consuming()

def menu():
    # essa funcao roda no terminal principal para interagir com o usuario
    while True:
        print("\n--- menu ---")
        print("1. ver produtos")
        print("2. fazer pedido")
        print("3. excluir pedido")
        print("4. ver meus pedidos")
        print("0. sair")
        opcao = input("escolha uma opcao: ")

        if opcao == '1':
            for p in produtos:
                print(f"{p['id_produto']} - {p['nome']} (R$ {p['preco']})")
        
        elif opcao == '2':
            id_pedido = len(meus_pedidos) + 1
            id_prod = int(input("id do produto: "))
            qtd = int(input("quantidade: "))
            
            novo_pedido = {
                "id_pedido": id_pedido,
                "produtos": [{"id_produto": id_prod, "quantidade": qtd}],
                "status": "pedido.criado"
            }
            meus_pedidos[id_pedido] = novo_pedido
            publicar_evento('pedido.criado', novo_pedido)
            print("pedido criado com sucesso.")

        elif opcao == '3':
            id_pedido = int(input("id do pedido para excluir: "))
            if id_pedido in meus_pedidos:
                meus_pedidos[id_pedido]['status'] = "pedido.excluido"
                publicar_evento('pedido.excluido', meus_pedidos[id_pedido])
                print("pedido excluido.")
            else:
                print("pedido nao encontrado.")

        elif opcao == '4':
            for k, v in meus_pedidos.items():
                print(f"pedido {k}: status = {v['status']}")
        
        elif opcao == '0':
            print("saindo.")
            break

if __name__ == '__main__':
    # cria a thread paralela. daemon=True faz ela desligar quando o programa principal fechar.
    thread_consumidor = threading.Thread(target=escutar_rabbit, daemon=True)
    thread_consumidor.start()
    
    # inicia o menu no terminal
    menu()