import os
import resend
from resend.exceptions import ResendError
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')

def send_email(email, item_promo, desconto):

    load_dotenv(ENV_PATH)

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