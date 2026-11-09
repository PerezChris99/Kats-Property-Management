"""Outbound transactional email gateway. Never send via plaintext SMTP."""
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlparse

class MailNotConfigured(RuntimeError):
    pass

def mail_configured():
    keys=("SMTP_HOST","SMTP_PORT","SMTP_USERNAME","SMTP_PASSWORD","MAIL_FROM","PUBLIC_APP_URL")
    return all(os.getenv(x) for x in keys)

def app_origin():
    origin=os.getenv("PUBLIC_APP_URL","http://localhost:5173").rstrip("/")
    parsed=urlparse(origin)
    if (parsed.scheme not in ("https","http") or
            parsed.username or parsed.password or not parsed.hostname or
            parsed.path not in ("","/") or parsed.query or parsed.fragment):
        raise MailNotConfigured("Invalid application public URL")
    if parsed.scheme!="https" and parsed.hostname not in ("localhost","127.0.0.1"):
        raise MailNotConfigured("Public email links require HTTPS outside localhost")
    return origin

def send_transactional_email(email,subject,body):
    if not mail_configured():
        raise MailNotConfigured("Transactional SMTP is not configured")
    port=int(os.environ["SMTP_PORT"])
    if port not in (465,587):
        raise MailNotConfigured("SMTP must use TLS port 465 or STARTTLS port 587")
    msg=EmailMessage()
    msg["From"]=os.environ["MAIL_FROM"]
    msg["To"]=email
    msg["Subject"]=subject
    msg.set_content(body)
    try:
        context=ssl.create_default_context()
        if port==465:
            with smtplib.SMTP_SSL(os.environ["SMTP_HOST"],port,timeout=10,context=context) as smtp:
                smtp.login(os.environ["SMTP_USERNAME"],os.environ["SMTP_PASSWORD"])
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(os.environ["SMTP_HOST"],port,timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(os.environ["SMTP_USERNAME"],os.environ["SMTP_PASSWORD"])
                smtp.send_message(msg)
    except (OSError,smtplib.SMTPException) as exc:
        raise MailNotConfigured("Transactional SMTP delivery failed") from exc
