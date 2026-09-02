import rsa
import os

# Lista de todos os microserviços e consumidores que precisam de chaves
pastas = [
    "ms_principal",
    "ms_estoque",
    "ms_pagamento",
    "ms_entrega",
    "ms_promocoes",
    "consumidores_promocao" 
]

# Gardar as chaves públicas geradas para cada microserviço
chaves_geradas = {}

print("Geração de chaves RSA para os microserviços e consumidores\n")
for ms in pastas:
    if ms.startswith("ms_"):
        print(f"Geração da par de chaves para {ms}")
        pub, priv = rsa.newkeys(512)
        chaves_geradas[ms] = pub 
        
        # Criamos a pasta do microserviço e salvamos a chave privada
        os.makedirs(ms, exist_ok=True)
        with open(f'{ms}/privada.pem', 'wb') as f:
            f.write(priv.save_pkcs1())

print("\nDistribution das chaves públicas")
for pasta_destino in pastas:
    # Criamos o diretório chaves_publicas para TODOS
    pasta_pub = f"{pasta_destino}/chaves_publicas"
    os.makedirs(pasta_pub, exist_ok=True)
    
    # Copiamos as chaves públicas de todos os MS para dentro
    for nome_ms_origem, chave_pub in chaves_geradas.items():
        if pasta_destino != nome_ms_origem: # Não precisamos nos dar a nossa própria chave pública
            with open(f'{pasta_pub}/{nome_ms_origem}_publica.pem', 'wb') as f:
                f.write(chave_pub.save_pkcs1())

print("\n[Sucesso] Todas as chaves estão geradas e organizadas nos diretórios corretos")