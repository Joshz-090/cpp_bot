# cpp-telegram-bot

A production-ready Python Telegram bot project.

## Features
- **Asynchronous**: Built with `python-telegram-bot` v20+ using `asyncio`.
- **Database**: `SQLAlchemy` 2.0+ with PostgreSQL support.
- **Configurable**: Secure environment variable management with validation.
- **Production-Ready**: Supports both **Polling** (Development) and **Webhooks** (Production).
- **Modular Architecture**: Separate directories for handlers, services, and models.

## Project Structure
```text
cpp-telegram-bot/
│
├── app/
│   ├── main.py        # Entry point
│   ├── config.py      # Configuration logic
│   ├── database.py    # DB connection/session
│   ├── models.py      # SQLAlchemy models
│   ├── handlers/      # Bot command handlers
│   └── services/      # Business logic
│
├── .env               # Environment secrets
├── .gitignore         # Git ignore rules
├── requirements.txt   # Dependencies
└── README.md          # Documentation
```

## Setup Instructions

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd cpp-telegram-bot
    ```

2.  **Activate Virtual Environment**:
    ```bash
    .\venv\Scripts\activate  # Windows
    # source venv/bin/activate # Linux/macOS
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment**:
    Edit `.env` and provide your `BOT_TOKEN` and `DATABASE_URL`.

## Local Development
Run the bot in polling mode (default):
```bash
python -m app.main
```

## Production Deployment (Render-ready)
To deploy on Render:
1.  Set `ENV=production` in environment variables.
2.  Set `WEBHOOK_URL` to your Render service URL.
3.  Set `BOT_TOKEN` and `DATABASE_URL`.
4.  Render will automatically provide the `PORT` variable.
