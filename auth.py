from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
import traceback
from config import settings
from database import get_db
from models import User

# 获取日志记录器
logger = logging.getLogger('ecometrics.auth')

# JWT令牌生成和验证
security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        role: str = payload.get("role")
        
        if user_id is None or username is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {"user_id": user_id, "username": username, "role": role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def authenticate_user(db: Session, username: str, password: str):
    """验证用户登录（明文密码）"""
    logger.debug(f"Authenticating user: {username}")
    
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            logger.debug(f"User not found: {username}")
            return False
        
        logger.debug(f"User found: {username} (ID: {user.id})")
        
        # 明文密码直接比较
        if user.password != password:
            logger.debug(f"Password mismatch for user: {username}")
            return False
        
        logger.debug(f"Authentication successful for user: {username}")
        return user
        
    except SQLAlchemyError as e:
        logger.error(f"Database error during authentication: {str(e)}")
        logger.error(f"Database error details: {traceback.format_exc()}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        return False

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """获取当前登录用户"""
    try:
        token = credentials.credentials
        logger.debug("Verifying token...")
        token_data = verify_token(token)
        
        logger.debug(f"Token verified for user ID: {token_data['user_id']}")
        
        user = db.query(User).filter(User.id == token_data["user_id"]).first()
        if user is None:
            logger.warning(f"User not found for ID: {token_data['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug(f"Current user retrieved: {user.username} (ID: {user.id})")
        return user
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error getting current user: {str(e)}")
        logger.error(f"Database error details: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error retrieving user"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting current user: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """获取当前管理员用户"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin only."
        )
    return current_user

def log_operation(db: Session, user_id: int, action: str, table_name: str, record_id: Optional[int] = None, 
                 old_data: Optional[dict] = None, new_data: Optional[dict] = None, 
                 description: Optional[str] = None, ip_address: Optional[str] = None):
    """记录操作日志"""
    from models import OperationLog
    
    logger.debug(f"Logging operation: {action} on {table_name} by user {user_id}")
    
    try:
        log_entry = OperationLog(
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_data=old_data,
            new_data=new_data,
            description=description,
            ip_address=ip_address
        )
        
        logger.debug("Adding log entry to database...")
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        logger.debug(f"Operation log created with ID: {log_entry.id}")
        
    except SQLAlchemyError as e:
        # 日志记录失败不影响主业务
        logger.error(f"Database error logging operation: {str(e)}")
        logger.error(f"Database error details: {traceback.format_exc()}")
        db.rollback()
    except Exception as e:
        # 日志记录失败不影响主业务
        logger.error(f"Unexpected error logging operation: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        db.rollback() 