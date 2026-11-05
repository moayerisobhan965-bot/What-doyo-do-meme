"""
Email Service
E-Mail-Versand mit Resend API (kostenlos, 100 Mails/Tag)
Wie bei GitHub/Google: Code wird gesendet, Benutzer gibt Code ein
"""
import os
from typing import Optional
import aiohttp
from fastapi import HTTPException
from app.config import get_settings

settings = get_settings()


class EmailService:
    """E-Mail Service Wrapper"""

    def __init__(self):
        self.api_key = settings.SMTP_PASSWORD  # Resend API Key
        self.from_email = settings.SMTP_FROM
        self.from_name = settings.SMTP_FROM_NAME
        self.base_url = "https://api.resend.com/emails"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        template: Optional[str] = None
    ) -> bool:
        """Sendet eine E-Mail"""
        if not self.api_key:
            print(f"⚠️  Email API Key nicht gesetzt - E-Mail wird NICHT gesendet")
            print(f"   To: {to_email}")
            print(f"   Subject: {subject}")
            return False

        payload = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }

        if template:
            payload["template"] = template

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ E-Mail gesendet: {to_email} - {subject}")
                        return True
                    else:
                        error_text = await response.text()
                        print(f"❌ Fehler beim Senden der E-Mail: {error_text}")
                        return False
        except Exception as e:
            print(f"❌ E-Mail Sendung fehlgeschlagen: {str(e)}")
            return False

    async def send_verification_email(
        self,
        to_email: str,
        username: str,
        verification_code: str,
        domain: str = "whatmeme.de"
    ) -> bool:
        """
        Sendet E-Mail mit Code (wie bei GitHub/Google)
        Benutzer erhält Code in E-Mail
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>E-Mail verifizieren - What Meme</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f4f4;
                }}
                .container {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #4CAF50;
                    margin-top: 0;
                }}
                .info {{
                    background-color: #f9f9f9;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .code {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #4CAF50;
                    letter-spacing: 5px;
                    word-break: break-all;
                }}
                .footer {{
                    margin-top: 30px;
                    font-size: 12px;
                    color: #888;
                    text-align: center;
                }}
                .instructions {{
                    background-color: #e3f2fd;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ E-Mail verifizieren</h1>
                <p>Hallo {{username}},</p>
                <p>Vielen Dank für die Registrierung bei <strong>What Meme</strong>!</p>

                <div class="instructions">
                    <p style="margin: 0 0 10px 0; font-weight: bold;">So verifizierst du deine E-Mail:</p>
                    <ol style="margin: 0; padding-left: 20px;">
                        <li>Schau in deine E-Mails nach</li>
                        <li>Kopiere den Code: <strong>{{verification_code}}</strong></li>
                        <li>Gehe zurück zum Frontend</li>
                        <li>Füge den Code ein und bestätige</li>
                    </ol>
                </div>

                <div class="info">
                    <p style="margin: 0 0 10px 0;"><strong>Dein Verifizierungs-Code:</strong></p>
                    <p class="code">{{verification_code}}</p>
                </div>

                <p style="font-size: 14px; color: #666;">
                    Der Code ist 24 Stunden gültig.
                </p>

                <div class="footer">
                    <p>Dies ist eine automatisch generierte E-Mail von What Meme.</p>
                    <p>Wenn du dich nicht registriert hast, kannst du diese E-Mail ignorieren.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            subject="Verifizierungs-Code für What Meme",
            html_content=html_content,
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_code: str,
        domain: str = "whatmeme.de"
    ) -> bool:
        """
        Sendet E-Mail mit Code (wie bei GitHub/Google)
        Benutzer erhält Code in E-Mail
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Passwort zurücksetzen - What Meme</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f4f4;
                }}
                .container {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #FF5722;
                    margin-top: 0;
                }}
                .info {{
                    background-color: #f9f9f9;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .code {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #FF5722;
                    letter-spacing: 5px;
                    word-break: break-all;
                }}
                .footer {{
                    margin-top: 30px;
                    font-size: 12px;
                    color: #888;
                    text-align: center;
                }}
                .instructions {{
                    background-color: #ffebee;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔑 Passwort zurücksetzen</h1>
                <p>Hallo {{username}},</p>
                <p>Wir haben ein Passwort-Reset für dein <strong>What Meme</strong> Konto angefordert.</p>

                <div class="instructions">
                    <p style="margin: 0 0 10px 0; font-weight: bold;">So setzt du dein Passwort zurück:</p>
                    <ol style="margin: 0; padding-left: 20px;">
                        <li>Schau in deine E-Mails nach</li>
                        <li>Kopiere den Code: <strong>{{reset_code}}</strong></li>
                        <li>Gehe zurück zum Frontend</li>
                        <li>Füge den Code und dein neues Passwort ein</li>
                    </ol>
                </div>

                <div class="info">
                    <p style="margin: 0 0 10px 0;"><strong>Dein Reset-Code:</strong></p>
                    <p class="code">{{reset_code}}</p>
                </div>

                <p style="font-size: 14px; color: #666;">
                    Der Code ist 24 Stunden gültig.
                </p>

                <div class="footer">
                    <p>Dies ist eine automatisch generierte E-Mail von What Meme.</p>
                    <p>Wenn du dieses Anliegen nicht gestellt hast, kannst du diese E-Mail ignorieren.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            subject="Reset-Code für What Meme",
            html_content=html_content,
        )


# Singleton Instance
email_service = EmailService()
