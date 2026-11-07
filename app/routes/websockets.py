from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as redis
import json
from ..config import settings
from ..logging_config import logger

router = APIRouter(prefix="/ws", tags=["WebSockets"])

@router.websocket("/progress/{download_id}")
async def websocket_progress(websocket: WebSocket, download_id: int):
    await websocket.accept()
    logger.info(f"WebSocket connected for download_id: {download_id}")
    
    redis_client = redis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"download_progress:{download_id}")
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data'].decode('utf-8')
                await websocket.send_text(data)
                
                # Stop listening if completed or failed
                parsed = json.loads(data)
                if parsed.get("status") in ["COMPLETED", "FAILED"]:
                    break
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for download_id: {download_id}")
    except Exception as e:
        logger.error(f"WebSocket error for download_id {download_id}: {str(e)}")
    finally:
        await pubsub.unsubscribe(f"download_progress:{download_id}")
        await redis_client.close()
