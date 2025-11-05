"""
Authentication middleware
"""
from fastapi import HTTPException, Security, Header
from fastapi.security import APIKeyHeader
from typing import Optional

from ..config import settings
from ..database import SessionLocal, APIKey

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify API key from request header
    
    Args:
        api_key: API key from header
        
    Returns:
        API key if valid
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is missing"
        )
    
    # Check if API key is in the allowed list (for simple configuration)
    if settings.ALLOWED_API_KEYS and api_key in settings.ALLOWED_API_KEYS:
        return api_key
    
    # Check database for API key
    db = SessionLocal()
    try:
        db_api_key = db.query(APIKey).filter(
            APIKey.key == api_key,
            APIKey.is_active == True
        ).first()
        
        if not db_api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        # Update last used timestamp
        from datetime import datetime
        db_api_key.last_used_at = datetime.utcnow()
        db.commit()
        
        return api_key
        
    finally:
        db.close()
