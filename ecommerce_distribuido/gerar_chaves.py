import rsa
import os

# Lista de todos os microserviços e consumidores que precisam de chaves
pastas = [
    "ms_principal",
    "ms_estoque",
    "ms_pagamento",
    "ms_entrega",
    "ms_promocoes"
]

# Gardar as chaves publicas geradas para cada microserviço
chaves_geradas = {}

print("Geração de chaves RSA para os microserviços e consumidores\n")
for ms in pastas:
    print(f"Geração da par de chaves para {ms}")
    pub, priv = rsa.newkeys(512)
    chaves_geradas[ms] = pub 

    pasta = f"ecommerce/{ms}"
    
    # Criamos a pasta do microserviço e salvamos a chave privada
    os.makedirs(pasta, exist_ok=True)
    with open(f'{pasta}/{ms}_privada.pem', 'wb') as f:
        f.write(priv.save_pkcs1())

print("\nDistribution das chaves publicas")
for pasta_destino in pastas:
    # Criamos o diretorio chaves_publicas para todos
    pasta_pub = f"ecommerce/{pasta_destino}/chaves_publicas"
    os.makedirs(pasta_pub, exist_ok=True)
    
    # Copiamos as chaves publicas de todos os MS para dentro
    for nome_ms_origem, chave_pub in chaves_geradas.items():
        if pasta_destino != nome_ms_origem: # Nao precisamos nos dar a nossa própria chave pública
            with open(f'{pasta_pub}/{nome_ms_origem}_publica.pem', 'wb') as f:
                f.write(chave_pub.save_pkcs1())

print("\n[Sucesso] Todas as chaves estão geradas e organizadas nos diretórios corretos")