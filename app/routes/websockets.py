from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
import redis.asyncio as redis
import json
from ..config import settings
from ..logging_config import logger
from ..database import SessionLocal
from ..models import Download, User

router = APIRouter(prefix="/ws", tags=["WebSockets"])


def verify_ws_token_and_ownership(token: str | None, download_id: int) -> bool:
    """Validate JWT token and verify object-level ownership or admin role for download progress."""
    if not token:
        return False
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return False
    except JWTError:
        return False

    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        if user.role == "admin":
            return True

        download = db.query(Download).filter(Download.id == download_id).first()
        if not download or download.user_id != user.id:
            return False
        return True


@router.websocket("/progress/{download_id}")
async def websocket_progress(websocket: WebSocket, download_id: int, token: str | None = None):
    # Verify authentication and authorization context before accepting stream
    if not verify_ws_token_and_ownership(token, download_id):
        logger.warning(f"Unauthorized WebSocket connection attempt for download_id: {download_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logger.info(f"Authorized WebSocket connected for download_id: {download_id}")

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
