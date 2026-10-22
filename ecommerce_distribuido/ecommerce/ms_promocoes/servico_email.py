import os
import resend
from resend.exceptions import ResendError
from dotenv import load_dotenv

def send_email(email, item_promo, desconto):

    load_dotenv()
<<<<<<< HEAD
    resend.api_key = os.environ.get("API_KEY")
=======
    resend.api_key = "re_LHYyUVCm_BUyDnxGy6Wjx3Vk1sYueuDmo"
>>>>>>> parent of 551d309 (corrigindo caminhos e adicionando .env)

    params: resend.Emails.SendParams = {
        "from": "Acme <onboarding@resend.dev>",
        "to": [email],
        "subject": f"Promoção do produto {item_promo['nome']}",
        "html": f"<strong> promoção do produto {item_promo['nome']} com desconto de {desconto}% !!! </strong>",
    }

    try:
        resposta = resend.Emails.send(params)
        print(resposta)
    except ResendError as error:
        print(error)