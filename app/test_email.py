import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()  # Carrega les variables del .env

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

TO_EMAIL = "marc.hostalot@gmail.com"

msg = MIMEText("Això és un test d'enviament de correu amb FastAPI i Gmail.")
msg["Subject"] = "Prova de correu SMTP"
msg["From"] = SMTP_USER
msg["To"] = TO_EMAIL

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    print("✅ Correu enviat correctament.")
except Exception as e:
    print("❌ Error en enviar el correu:", e)
