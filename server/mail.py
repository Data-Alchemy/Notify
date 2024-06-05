import os
from flask import Flask
from flask_mail import Mail, Message
import logging
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def df_to_html_table(df):
    """Convert a pandas DataFrame to an HTML table string with styling."""
    html_table = df.to_html(index=False, classes='table table-striped')
    styled_table = f"""
    <style>
        .table {{
            width: 100%;
            border-collapse: collapse;
            display: block;
            overflow-x: auto;
            white-space: nowrap;
        }}
        .table th, .table td {{
            border: 1px solid #dddddd;
            padding: 8px;
            text-align: left;
        }}
        .table-striped tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
    </style>
    {html_table}
    """
    return styled_table

class EmailSender:
    def __init__(self, app: Flask):
        self.mail = Mail(app)
    
    def send_email(self, recipient: str, subject: str, body: str, content_type='plain'):
        try:
            msg = Message(subject, recipients=[recipient])
            if content_type == 'html':
                msg.html = body
            else:
                msg.body = body
            self.mail.send(msg)
            logger.info(f"Email sent to {recipient} with subject '{subject}'.")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise

def create_app():
    app = Flask(__name__)

    # Mail configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] =  os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] =  os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    
    return app
