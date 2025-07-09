from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime
import logging
import traceback
from database import get_db
from models import User
from schemas import UserLogin, UserRegister, UserResponse, TokenResponse, SuccessResponse, ErrorResponse
from auth import authenticate_user, create_access_token, get_current_user

# 获取日志记录器
logger = logging.getLogger('ecometrics.auth')

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=dict)
async def login(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    """User login"""
    logger.info(f"Login attempt for username: {user_data.username}")
    logger.debug(f"Login request from IP: {request.client.host}")
    
    try:
        # 验证用户凭据
        logger.debug("Authenticating user credentials...")
        user = authenticate_user(db, user_data.username, user_data.password)
        if not user:
            logger.warning(f"Authentication failed for username: {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"Authentication successful for user: {user.username} (ID: {user.id})")
        
        # 更新最后登录时间
        logger.debug("Updating last login time...")
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        # 创建访问令牌
        logger.debug("Creating access token...")
        access_token = create_access_token(
            data={"user_id": user.id, "username": user.username, "role": user.role}
        )
        
        # 构造响应
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            role=user.role,
            loginTime=user.last_login_at,
            createdAt=user.created_at
        )
        
        response_data = {
            "success": True,
            "data": {
                "token": access_token,
                "user": user_response
            }
        }
        
        logger.info(f"Login successful for user: {user.username}")
        return response_data
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during login: {str(e)}")
        logger.error(f"Database error details: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during login: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/register", response_model=dict)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """User registration"""
    logger.info(f"Registration attempt for username: {user_data.username}")
    
    try:
        # 检查用户名是否已存在
        logger.debug(f"Checking if username {user_data.username} already exists...")
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            logger.warning(f"Username {user_data.username} already exists - user ID: {existing_user.id}")
            return {
                "success": False,
                "error": "Validation failed",
                "message": "Username already exists",
                "details": {
                    "field": "username",
                    "code": "DUPLICATE_USERNAME"
                }
            }
        
        logger.debug("Username is unique, creating new user...")
        
        # 创建新用户
        new_user = User(
            username=user_data.username,
            password=user_data.password,  # 明文存储
            role="user"  # 默认角色
        )
        
        logger.debug("Adding new user to database session...")
        db.add(new_user)
        
        logger.debug("Committing transaction...")
        db.commit()
        
        logger.debug("Refreshing user to get generated ID...")
        db.refresh(new_user)
        
        logger.info(f"Successfully created user with ID: {new_user.id}")
        
        response_data = {
            "success": True,
            "message": "Registration successful",
            "data": {
                "id": new_user.id,
                "username": new_user.username,
                "role": new_user.role,
                "createdAt": new_user.created_at
            }
        }
        
        logger.info(f"Registration successful for user: {new_user.username}")
        return response_data
        
    except IntegrityError as e:
        logger.error(f"Integrity error during registration: {str(e)}")
        logger.error(f"Integrity error details: {traceback.format_exc()}")
        db.rollback()
        return {
            "success": False,
            "error": "Validation failed",
            "message": "Username already exists",
            "details": {
                "field": "username",
                "code": "DUPLICATE_USERNAME"
            }
        }
    except SQLAlchemyError as e:
        logger.error(f"Database error during registration: {str(e)}")
        logger.error(f"Database error details: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during registration: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/logout", response_model=dict)
async def logout(current_user: User = Depends(get_current_user)):
    """User logout"""
    # 简化版登出，只返回成功消息
    # 在实际应用中，可以将token加入黑名单
    return {
        "success": True,
        "message": "Logout successful"
    } 