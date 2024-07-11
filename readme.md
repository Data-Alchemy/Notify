# Snowflake Query Alert System

This project is a Flask web application designed to run Snowflake queries securely and send the results via email. The application includes authentication and authorization functionalities, integrates with Snowflake for data querying, and uses Flask-Mail for sending email alerts.

## Table of Contents
- [Features](#features)
- [Setup](#setup)
- [Usage](#usage)
  - [Running the App](#running-the-app)
  - [Endpoints](#endpoints)
- [Environment Variables](#environment-variables)

## Features
- User registration and login with token-based authentication.
- Secure Snowflake query execution.
- Email alerts with query results.
- Query validation to prevent dangerous operations.

## Setup

### Prerequisites
- Python 3.8+
- Flask
- Flask-Mail
- Flask-SQLAlchemy
- Snowflake Connector for Python
- SQLite (or any other SQLAlchemy supported database)

### Installation
1. Clone the repository:
    ```sh
    git clone <repository_url>
    cd <repository_directory>
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Set up environment variables. Create a `.env` file in the project root directory and populate it with your configuration. Example:
    ```dotenv
    SECRET_KEY=your_secret_key
    ALLOWED_DOMAINS=example.com
    TOKEN_EXPIRY_DAYS=0
    TOKEN_EXPIRY_MINUTES=60
    ENCRYPTION_KEY=your_encryption_key
    MAIL_USERNAME=your_email@example.com
    MAIL_PASSWORD=your_email_password
    MAIL_DEFAULT_SENDER=your_email@example.com
    SNOWFLAKE_CONNECTION={"account":"your_account", "user":"your_user", "password":"your_password", "database":"your_database", "warehouse":"your_warehouse", "schema":"your_schema", "role":"your_role"}
    COMPANY=your_company_name
    ```

### Database Setup
1. Initialize the database:
    ```sh
    flask db init
    flask db migrate -m "Initial migration."
    flask db upgrade
    ```

## Usage

### Running the App
To run the application, use:
```sh
python app.py
```

The application will be available at `http://127.0.0.1:5000`.

### Endpoints

#### 1. User Registration
- **URL:** `/register`
- **Method:** `POST`
- **Request Body:**
```json
  {
      "email": "user@example.com",
      "name": "User Name"
  }
```

- **Response:**
``` 
{
    "message": "User registered successfully and email sent"
}
```

#### 2. User Login
- **URL:** `/login`
- **Method:** `POST`
- **Request Body:**
```json
  {
      "email": "user@example.com"
  }
```

- **Response:**
```
{
    "message": "Token sent to your email"
}
```

#### 3. Send Alert
- **URL:** `/send_alert`
- **Method:** `POST`
- **Headers:**
  Authorization: Bearer <token>
- **Request Body:**
  {
      "query": "SELECT * FROM your_table",
      "email": "alert_recipient@example.com",
      "message": "Custom message for the email body"
  }
- **Response:**
  {
      "message": "Alert sent successfully"
  }
