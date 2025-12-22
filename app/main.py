
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from app.config import get_settings
import logging

# Try to import handler with error catching
try:
    from app.whatsapp.handler import whatsapp_handler
    HANDLER_AVAILABLE = True
except Exception as e:
    print(f"⚠️ WhatsApp handler import failed: {e}")
    import traceback
    traceback.print_exc()
    HANDLER_AVAILABLE = False
    whatsapp_handler = None

from app.database import init_db

# Try to import services
try:
    from app.services.redis_cache import redis_cache
except:
    redis_cache = None

try:
    from app.services.vector_store import vector_store
except:
    vector_store = None
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="IPL Auction Insights Agent",
    description="WhatsApp bot for IPL player analysis and auction insights",
    version="1.0.0"
)

settings = get_settings()

# Initialize Twilio client
twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting IPL Auction Bot...")
    
    # Initialize database
    init_db()
    logger.info("✅ Database initialized")
    
    # Check Redis connection
    if redis_cache and redis_cache.health_check():
        logger.info("✅ Redis connected")
    else:
        logger.warning("⚠️ Redis connection failed")
    
    # Check Qdrant connection
    if vector_store and vector_store.health_check():
        logger.info("✅ Qdrant connected")
    else:
        logger.warning("⚠️ Qdrant connection failed")
    
    logger.info("✅ IPL Auction Bot is ready!")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "IPL Auction Insights Agent",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/whatsapp/webhook",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "redis": redis_cache.health_check() if redis_cache else False,
            "qdrant": vector_store.health_check() if vector_store else False,
            "database": True,  # If we got here, DB is working
            "handler": HANDLER_AVAILABLE
        }
    }


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...),
    MessageSid: str = Form(...)
):
    """
    Twilio WhatsApp webhook endpoint
    Receives incoming messages and sends responses
    """
    try:
        logger.info(f"📩 Message from {From}: {Body}")
        
        # Check if handler is available
        if not HANDLER_AVAILABLE or not whatsapp_handler:
            twiml_response = MessagingResponse()
            twiml_response.message("❌ Bot is currently initializing. Please try again in a moment.")
            return Response(
                content=str(twiml_response),
                media_type="application/xml"
            )
        
        # Validate request (optional but recommended)
        # In production, verify Twilio signature for security
        
        # Process message
        response_text = whatsapp_handler.process_message(Body, From)
        
        # Debug: Log the FULL response
        logger.info(f"📤 FULL Response text:")
        logger.info(response_text)
        logger.info(f"📤 Response length: {len(response_text)} chars")
        
        # Create TwiML response
        twiml_response = MessagingResponse()
        twiml_response.message(response_text)
        
        # Debug: Log the FULL TwiML XML
        twiml_xml = str(twiml_response)
        logger.info(f"📤 FULL TwiML XML:")
        logger.info(twiml_xml)
        
        logger.info(f"✅ Sent response to {From}")
        
        # Return TwiML XML
        return Response(
            content=twiml_xml,
            media_type="application/xml"
        )
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        
        # Send error message to user
        error_response = MessagingResponse()
        error_response.message(
            "❌ Sorry, I encountered an error. Please try again later."
        )
        
        return Response(
            content=str(error_response),
            media_type="application/xml"
        )


@app.post("/whatsapp/send")
async def send_whatsapp_message(
    to: str,
    message: str
):
    """
    Send proactive WhatsApp message
    Useful for notifications and alerts
    """
    try:
        # Ensure phone number has whatsapp: prefix
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"
        
        message = twilio_client.messages.create(
            body=message,
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=to
        )
        
        return {
            "status": "sent",
            "sid": message.sid,
            "to": to
        }
    
    except Exception as e:
        logger.error(f"❌ Send message error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get bot usage statistics"""
    popular_players = redis_cache.get_popular_players(limit=10)
    
    return {
        "popular_players": popular_players,
        "total_searches": sum(count for _, count in popular_players)
    }


@app.post("/broadcast")
async def broadcast_message(
    recipients: list,
    message: str
):
    """
    Broadcast message to multiple recipients
    Useful for auction updates or alerts
    """
    results = []
    
    for recipient in recipients:
        try:
            result = await send_whatsapp_message(recipient, message)
            results.append({
                "recipient": recipient,
                "status": "sent",
                "sid": result['sid']
            })
        except Exception as e:
            results.append({
                "recipient": recipient,
                "status": "failed",
                "error": str(e)
            })
    
    return {
        "total": len(recipients),
        "successful": len([r for r in results if r['status'] == 'sent']),
        "failed": len([r for r in results if r['status'] == 'failed']),
        "results": results
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True
    )