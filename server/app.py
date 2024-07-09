from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from mail import EmailSender, create_app, df_to_html_table
from auth import auth_bp, db, init_email_sender, verify_token
from Snowflake import Snowpipe
import os
import logging
import json

# Initialize Flask app
app = create_app()

# Initialize Flask-Mail
email_sender = EmailSender(app)

# Initialize email sender in authorization
init_email_sender(email_sender)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Register the authorization blueprint
app.register_blueprint(auth_bp)

# Create the database
with app.app_context():
    db.create_all()

# Snowflake connection parameters
SNOWFLAKE_CONFIG = os.getenv("snowflake_connection")
company = os.getenv("COMPANY")
creds = json.loads(SNOWFLAKE_CONFIG)
snowpipe = Snowpipe(connection_parameters=creds)

def query_scanner(query):
    """Check if the query contains forbidden operations."""
    forbidden_keywords = ["delete", "insert", "truncate", "drop", "create"]
    for keyword in forbidden_keywords:
        if keyword in query.lower():
            return False, f"Error: {keyword.upper()} operations are not allowed."
    return True, "Query is safe."

@app.route('/read_snowflake_query', methods=['POST'])
def run_snowflake_query():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"message": "Token not provided"}), 401

    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return jsonify({"message": "Token format invalid"}), 401

    payload, is_valid = verify_token(token, os.getenv('SECRET_KEY'))
    if not is_valid:
        return jsonify({"message": payload}), 401

    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"message": "Query is required"}), 400

        query = data['query']

        # Sanitize the query string to escape double quotes
        query = query.replace('"', '\\"')

        is_safe, message = query_scanner(query)
        if not is_safe:
            return jsonify({"message": message}), 400

        results = snowpipe.get_pdf(query)
        return jsonify(results.to_dict(orient='records')), 200
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        return jsonify({"message": "Invalid JSON format", "error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error running Snowflake query: {e}")
        return jsonify({"message": "Error running Snowflake query", "error": str(e)}), 500


@app.route('/cortex', methods=['POST'])
def run_cortex():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"message": "Token not provided"}), 401

    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return jsonify({"message": "Token format invalid"}), 401

    payload, is_valid = verify_token(token, os.getenv('SECRET_KEY'))
    if not is_valid:
        return jsonify({"message": payload}), 401

    try:
        query = "Select snowflake.cortex.complete('mistral-7b', 'What is a oxymoron') explain"
        if not query:
            return jsonify({"message": "Query is required"}), 400

        results = snowpipe.get_pdf(query)
        return jsonify(results.to_dict(orient='records')), 200
    except Exception as e:
        logging.error(f"Error running Snowflake query: {e}")
        return jsonify({"message": "Error running Snowflake query", "error": str(e)}), 500
    
@app.route('/send_alert', methods=['POST'])
def send_alert():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"message": "Token not provided"}), 401

    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return jsonify({"message": "Token format invalid"}), 401

    payload, is_valid = verify_token(token, os.getenv('SECRET_KEY'))
    if not is_valid:
        return jsonify({"message": payload}), 401

    data = request.json
    query = data.get('query')
    email = data.get('email')
    custom_message = data.get('message', 'The query returned the following results:')

    if not query or not email:
        return jsonify({"message": "Query and email are required"}), 400
    
    is_safe, message = query_scanner(query)
    if not is_safe:
        return jsonify({"message": message}), 400

    try:
        # Limiting to 200 rows per call
        results = snowpipe.get_pdf(query).head(200)
        if not results.empty:
            # Convert the DataFrame to an HTML table string with styling
            results_html = df_to_html_table(results)
            email_body = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f4;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        width: 100%;
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #ffffff;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                    }}
                    .header {{
                        background-color: #007bff;
                        color: #ffffff;
                        padding: 10px;
                        text-align: center;
                        border-radius: 8px 8px 0 0;
                    }}
                    .content {{
                        padding: 20px;
                    }}
                    .footer {{
                        background-color: #007bff;
                        color: #ffffff;
                        text-align: center;
                        padding: 10px;
                        border-radius: 0 0 8px 8px;
                        margin-top: 20px;
                    }}
                    @media only screen and (max-width: 600px) {{
                        .container {{
                            padding: 10px;
                        }}
                        .content {{
                            padding: 10px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Snowflake Query Alert</h2>
                    </div>
                    <div class="content">
                        <p>{custom_message}</p>
                        {results_html}
                    </div>
                    <div class="footer">
                        <p>&copy; 2024 {company}. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            email_sender.send_email(email, "Snowflake Query Alert", email_body, content_type='html')
            return jsonify({"message": "Alert sent successfully"}), 200
        else:
            return jsonify({"message": "No results returned from the query"}), 200
    except Exception as e:
        logging.error(f"Error running Snowflake query: {e}")
        return jsonify({"message": "Error running Snowflake query", "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)

