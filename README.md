IPL Auction Insights – WhatsApp Bot

This project is a WhatsApp-based chatbot that provides IPL player statistics and auction-related insights using natural language queries.

Users can send messages through WhatsApp. The bot converts user queries into SQL, fetches data from a PostgreSQL database, and returns responses using AI.

Features
- IPL player batting and bowling statistics
- Natural language query handling (Text to SQL)
- AI-generated responses
- Redis caching for improved performance
- WhatsApp integration using Twilio

Technology Stack
Backend: Python, FastAPI
Database: PostgreSQL
Cache: Redis
AI Model: Google Gemini
Vector Database: Qdrant
Messaging API: Twilio WhatsApp

Project Structure
ipl-auction-bot/
app/
main.py
config.py
database.py
models.py
services/
text_to_sql.py
ai_response.py
redis_cache.py
whatsapp/
handler.py
scripts/
init_db.py
insert_sample_data.py
setup_qdrant.py
run.py
requirements.txt
README.md

Installation
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

Configuration
Create a .env file and add:
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_NUMBER
DATABASE_URL
REDIS_URL
QDRANT_URL
QDRANT_API_KEY
GEMINI_API_KEY
GEMINI_MODEL

Database Setup
createdb ipl_auction
python scripts/init_db.py
python scripts/insert_sample_data.py

Run Application
python run.py

Access URL
http://localhost:8000

License
MIT
