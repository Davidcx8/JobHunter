import os
import smtplib
import json
import requests
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EmailDispatcher:
    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Loads SMTP settings from environment variables"""
        return {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'email': os.getenv('EMAIL_USER', ''),
            'password': os.getenv('EMAIL_PASSWORD', ''),
        }

    @classmethod
    def send_email(cls, to_email: str, subject: str, body_html: str) -> Dict[str, Any]:
        """
        Sends an outreach email.
        If email or password are not set, runs in DRY RUN mode.
        """
        config = cls.get_config()
        
        # Determine if we should run in simulated dry-run mode
        if not config['email'] or not config['password']:
            logger.info(f"[SIMULATION] SMTP not configured. Dry-run sending email:")
            logger.info(f"  To: {to_email}")
            logger.info(f"  Subject: {subject}")
            logger.info(f"  Body (first 100 chars): {body_html[:100]}...")
            return {
                "success": True,
                "status": "simulated",
                "message": f"Email simulation successful to {to_email} (Dry-run mode)"
            }
            
        try:
            msg = MIMEMultipart()
            msg['From'] = config['email']
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body_html, 'html'))
            
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['email'], config['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return {
                "success": True,
                "status": "sent",
                "message": f"Email sent successfully to {to_email}"
            }
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return {
                "success": False,
                "status": "failed",
                "error": str(e)
            }


class WebhookDispatcher:
    @staticmethod
    def send_notification(job: Dict[str, Any], webhook_url: Optional[str] = None):
        """
        Triggers a POST request to a webhook URL when a high-matching job is saved.
        Supports generic JSON, Discord, Slack, and Telegram webhooks.
        """
        url = webhook_url or os.getenv("NOTIFICATION_WEBHOOK")
        if not url:
            logger.info("No webhook URL configured. Skipping notification.")
            return
            
        logger.info(f"Triggering webhook alert for job: {job.get('title')} at {job.get('company')}")
        
        # Prepare rich payloads for popular services
        title = job.get('title', 'N/A')
        company = job.get('company', 'N/A')
        location = job.get('location', 'Remote')
        salary = job.get('salary') or 'Not disclosed'
        job_url = job.get('url', '#')
        score = job.get('match_score', 0)
        source = job.get('source', 'unknown')
        
        # Detect webhook platform
        try:
            if "discord.com/api/webhooks" in url:
                # Discord Rich Embed
                payload = {
                    "username": "JobHunter Pro Bot",
                    "embeds": [{
                        "title": f"🎯 Alta Coincidencia Laboral: {score}% Match",
                        "color": 65500, # Cyan color code
                        "fields": [
                            {"name": "Posición", "value": title, "inline": True},
                            {"name": "Empresa", "value": company, "inline": True},
                            {"name": "Ubicación", "value": location, "inline": True},
                            {"name": "Salario", "value": salary, "inline": True},
                            {"name": "Fuente", "value": source.capitalize(), "inline": True},
                            {"name": "Enlace", "value": f"[Ver Oferta]({job_url})", "inline": False}
                        ],
                        "timestamp": datetime.now().isoformat()
                    }]
                }
            elif "hooks.slack.com/services" in url:
                # Slack Blocks
                payload = {
                    "text": f"🎯 *Nueva oferta de interés:* {title} en *{company}* ({score}% Match)",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"🎯 *Alta Coincidencia: {score}% Match*\n*Puesto:* {title}\n*Empresa:* {company}\n*Ubicación:* {location}\n*Salario:* {salary}\n*Fuente:* {source.capitalize()}"}
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Ver Oferta"},
                                    "url": job_url
                                }
                            ]
                        }
                    ]
                }
            elif "api.telegram.org/bot" in url:
                # Telegram Send Message API (expects token in URL and chatId in params or payload)
                # For a Telegram webhook, we can parse the chatId if appended to the webhook URL as query param or JSON
                # E.g. https://api.telegram.org/bot<token>/sendMessage?chat_id=<chat_id>
                text = (
                    f"🎯 *Alta Coincidencia Laboral ({score}% Match)*\n\n"
                    f"💼 *Puesto:* {title}\n"
                    f"🏢 *Empresa:* {company}\n"
                    f"📍 *Ubicación:* {location}\n"
                    f"💰 *Salario:* {salary}\n"
                    f"🌐 *Fuente:* {source.upper()}\n\n"
                    f"🔗 [Ver oferta de empleo]({job_url})"
                )
                payload = {
                    "text": text,
                    "parse_mode": "Markdown"
                }
                # Check if chat_id is already in the URL
                if "chat_id" not in url:
                    # Try reading chat_id from TELEGRAM_CHAT_ID env var
                    chat_id = os.getenv("TELEGRAM_CHAT_ID")
                    if chat_id:
                        payload["chat_id"] = chat_id
            else:
                # Generic JSON Payload
                payload = {
                    "event": "high_match_job_found",
                    "timestamp": datetime.now().isoformat(),
                    "job": {
                        "title": title,
                        "company": company,
                        "location": location,
                        "salary": salary,
                        "url": job_url,
                        "match_score": score,
                        "source": source
                    }
                }
                
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code in [200, 201, 204]:
                logger.info("Webhook triggered successfully.")
            else:
                logger.warning(f"Webhook returned status code {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error triggering webhook notification: {e}")
