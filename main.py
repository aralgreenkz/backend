from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys
from datetime import datetime
import traceback

from config import settings
from database import engine, Base, test_database_connection
from routers import auth, data, logs

# 配置详细的日志记录
def setup_logging():
    """Configure application logging"""
    # 创建日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # 配置SQLAlchemy日志
    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_logger.setLevel(logging.INFO)
    
    # 配置应用日志
    app_logger = logging.getLogger('ecometrics')
    app_logger.setLevel(logging.INFO)
    
    return app_logger

# 设置日志
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    logger.info("=== EcoMetrics API Starting ===")
    logger.info(f"Environment: {settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else 'development'}")
    logger.info(f"Database URL: {settings.DATABASE_URL.replace(settings.MYSQL_PASSWORD, '***') if settings.MYSQL_PASSWORD else settings.DATABASE_URL}")
    logger.info(f"Frontend URL: {settings.FRONTEND_URL}")
    logger.info(f"JWT Secret: {'***' if settings.JWT_SECRET else 'NOT SET'}")
    
    # 测试数据库连接
    try:
        logger.info("Testing database connection...")
        connection_info = test_database_connection()
        logger.info(f"Database connection successful: {connection_info}")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        logger.error(f"Database connection error details: {traceback.format_exc()}")
        # 不要在连接失败时退出，让应用继续运行以便调试
    
    logger.info("Application started successfully")
    yield
    
    # 关闭时清理资源
    logger.info("=== EcoMetrics API Shutting Down ===")

# 创建FastAPI应用
app = FastAPI(
    title="EcoMetrics API",
    description="Backend API for Water and Electricity Monitoring and Efficiency Analysis Platform",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(logs.router, prefix="/api")

# 全局异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP exception handler"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    logger.warning(f"Request URL: {request.url}")
    logger.warning(f"Request method: {request.method}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    logger.error(f"Unexpected error [{error_id}]: {str(exc)}")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request method: {request.method}")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception details: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )

# 健康检查端点
@app.get("/")
async def root():
    """Root path health check"""
    return {
        "success": True,
        "message": "EcoMetrics API is running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check"""
    # 测试数据库连接
    db_status = "unknown"
    db_info = {}
    
    try:
        db_info = test_database_connection()
        db_status = "connected"
        logger.info(f"Health check - Database status: {db_status}")
    except Exception as e:
        db_status = "disconnected"
        db_info = {"error": str(e)}
        logger.error(f"Health check - Database connection failed: {str(e)}")
    
    return {
        "success": True,
        "status": "healthy",
        "message": "API is running normally",
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "status": db_status,
            "info": db_info
        }
    }

@app.get("/debug/database")
async def debug_database():
    """Database debug information"""
    from database import get_db_info
    
    logger.info("Database debug information requested")
    
    try:
        # 获取配置信息
        config_info = settings.get_config_info()
        config_warnings = settings.validate_config()
        
        # 获取数据库详细信息
        db_info = get_db_info()
        
        # 获取连接信息
        connection_info = test_database_connection()
        
        debug_info = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": config_info,
            "config_warnings": config_warnings,
            "database_info": db_info,
            "connection_test": connection_info
        }
        
        logger.info("Database debug information collected successfully")
        return debug_info
        
    except Exception as e:
        logger.error(f"Error collecting database debug info: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": settings.get_config_info() if hasattr(settings, 'get_config_info') else {},
            "config_warnings": settings.validate_config() if hasattr(settings, 'validate_config') else []
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        log_level="info"
    ) 