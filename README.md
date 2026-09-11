# Sistemas Distribuídos 

# Pré-requisitos

Python 3.x
Docker e Docker Compose

# Instalação e Execução

1. Instalar as dependências do Python

pip install -r requirements.txt

2. Subir o servidor de mensageria (RabbitMQ)

docker compose up -d

3. Gerar as chaves de segurança (RSA)

python gerar_chaves.py

4. Iniciar os microsserviços

Abra um terminal separado para cada microsserviço que deseja rodar. 

Exemplo de execução:

# Terminal 1: Iniciar o controle de estoque
python ms_estoque/app.py

# Terminal 2: Iniciar a interface do usuário
python ms_principal/app.py