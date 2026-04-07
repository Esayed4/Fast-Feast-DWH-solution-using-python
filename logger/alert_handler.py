# Create multi-threading for real-time error alert system

import logging
import smtplib
import threading
from email.mime.text import MIMEText
from config.settings import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_PASSWORD,
    ALERT_EMAIL_FROM,
    ALERT_EMAIL_TO,
)

# =============================================================================

# Called once in orchestrator.py at pipeline startup

def register_alert_handler():

    # Create a logging.Handler just for error level
    handler = logging.Handler().setLevel(logging.ERROR)

    # Replace the handler's emit method with our own function for email
    handler.emit = _email_format

    # attach to parent logger, this means logger.error() anywhere automatically reaches email_format
    logging.getLogger().addHandler(handler)

# =============================================================================

# Called automatically by Python's logging system on every log line

def _email_format(record: logging.LogRecord):

    # Ignore anything below ERROR level
    if record.levelno < logging.ERROR:
        return

    # Build the email subject using the module name so you know where it broke
    subject = f"FastFeast Pipeline Error — {record.filename}"

    # Build the email body with full context about where and what went wrong
    body = (
        f"Module:   {record.filename}\n"
        f"Function: {record.funcName}\n"
        f"Line:     {record.lineno}\n"
        f"Message:  {record.getMessage()}\n"
    )

    # Spin up a daemon thread so email sending never blocks the pipeline
    threading.Thread(
        target = _send_email,
        args   = (subject, body),
        daemon = True  # Thread dies automatically if the main program exits
    ).start()

# =============================================================================

# Runs inside the background thread, builds and delivers the email

def _send_email(subject: str, body: str):

    try:
        # MIMEText builds a plain text email object from the body string
        msg = MIMEText(body)

        # Set the three required email headers
        msg["Subject"] = subject
        msg["From"] = ALERT_EMAIL_FROM
        msg["To"] = ALERT_EMAIL_TO

        # Open SMTP connection ('with' closes it automatically when done)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(ALERT_EMAIL_FROM, SMTP_PASSWORD)
            server.sendmail(ALERT_EMAIL_FROM, ALERT_EMAIL_TO, msg.as_string())

    except Exception as e:
        
        print(f"[alert_handler] Failed to send email: {e}")