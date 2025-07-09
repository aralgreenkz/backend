import os
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse

load_dotenv()

class Settings:
    # 环境配置
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # 直接使用提供的数据库URL
    DATABASE_URL: str = "mysql://root:IxryOmSUdhSzlDBgYgVyLiPXspsfFDIo@tramway.proxy.rlwy.net:46053/railway"
    
    # 从DATABASE_URL解析各个组件
    def __init__(self):
        parsed = urlparse(self.DATABASE_URL)
        self.MYSQL_HOST = parsed.hostname or "localhost"
        self.MYSQL_PORT = parsed.port or 3306
        self.MYSQL_USER = parsed.username or "root"
        self.MYSQL_PASSWORD = parsed.password or ""
        self.MYSQL_DATABASE = parsed.path.lstrip('/') or "railway"
        
        # 转换为PyMySQL格式的URL
        self.DATABASE_URL = f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
    
    # JWT配置
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
    
    # 应用配置
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    PORT: int = int(os.getenv("PORT", "3000"))
    
    # Railway特定配置
    RAILWAY_ENVIRONMENT: str = os.getenv("RAILWAY_ENVIRONMENT", "")
    RAILWAY_PROJECT_ID: str = os.getenv("RAILWAY_PROJECT_ID", "")
    RAILWAY_SERVICE_ID: str = os.getenv("RAILWAY_SERVICE_ID", "")
    
    def get_config_info(self) -> dict:
        """获取配置信息（隐藏敏感信息）"""
        return {
            "environment": self.ENVIRONMENT,
            "debug": self.DEBUG,
            "log_level": self.LOG_LEVEL,
            "database": {
                "host": self.MYSQL_HOST,
                "port": self.MYSQL_PORT,
                "user": self.MYSQL_USER,
                "database": self.MYSQL_DATABASE,
                "password_set": bool(self.MYSQL_PASSWORD),
                "url_template": f"mysql+pymysql://{self.MYSQL_USER}:***@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            },
            "jwt": {
                "algorithm": self.JWT_ALGORITHM,
                "expire_hours": self.JWT_EXPIRE_HOURS,
                "secret_set": bool(self.JWT_SECRET and self.JWT_SECRET != "your-super-secret-jwt-key-change-this-in-production")
            },
            "application": {
                "frontend_url": self.FRONTEND_URL,
                "port": self.PORT
            },
            "railway": {
                "environment": self.RAILWAY_ENVIRONMENT,
                "project_id": self.RAILWAY_PROJECT_ID,
                "service_id": self.RAILWAY_SERVICE_ID,
                "is_railway": bool(self.RAILWAY_ENVIRONMENT)
            }
        }
    
    def validate_config(self) -> list:
        """验证配置并返回警告列表"""
        warnings = []
        
        # 检查数据库配置
        if not self.MYSQL_PASSWORD:
            warnings.append("MYSQL_PASSWORD is not set")
        
        if not self.MYSQL_HOST:
            warnings.append("MYSQL_HOST is not set")
        
        if not self.MYSQL_DATABASE:
            warnings.append("MYSQL_DATABASE is not set")
        
        # 检查JWT配置
        if self.JWT_SECRET == "your-super-secret-jwt-key-change-this-in-production":
            warnings.append("JWT_SECRET is using default value - change this in production")
        
        # 检查生产环境配置
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                warnings.append("DEBUG is enabled in production environment")
            
            if self.LOG_LEVEL == "DEBUG":
                warnings.append("LOG_LEVEL is set to DEBUG in production environment")
        
        return warnings

settings = Settings()

# 配置日志级别
def setup_logging_level():
    """根据配置设置日志级别"""
    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    logging.getLogger().setLevel(log_level)
    
    # 如果是调试模式，启用更详细的日志
    if settings.DEBUG:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.INFO)
    else:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)

# 在模块加载时设置日志级别
setup_logging_level() 
