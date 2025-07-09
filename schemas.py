from pydantic import BaseModel, validator
from typing import Optional, List, Any
from datetime import date, datetime
from decimal import Decimal

# 用户相关模型
class UserLogin(BaseModel):
    username: str
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if not v.startswith('@'):
            raise ValueError('Username must start with @')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class UserRegister(BaseModel):
    username: str
    password: str
    confirmPassword: str
    
    @validator('username')
    def validate_username(cls, v):
        if not v.startswith('@'):
            raise ValueError('Username must start with @')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v
    
    @validator('confirmPassword')
    def validate_confirm_password(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    loginTime: Optional[datetime] = None
    createdAt: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    token: str
    user: UserResponse

# 水电记录相关模型
class EcoRecordCreate(BaseModel):
    date: date
    powerConsumption: Decimal
    drinkingWater: Decimal
    irrigationWater: Decimal
    electricityPrice: Decimal
    
    @validator('powerConsumption', 'drinkingWater', 'irrigationWater', 'electricityPrice')
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError('Value must be positive')
        return v

class EcoRecordUpdate(BaseModel):
    powerConsumption: Optional[Decimal] = None
    drinkingWater: Optional[Decimal] = None
    irrigationWater: Optional[Decimal] = None
    electricityPrice: Optional[Decimal] = None
    
    @validator('powerConsumption', 'drinkingWater', 'irrigationWater', 'electricityPrice')
    def validate_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError('Value must be positive')
        return v

class EcoRecordResponse(BaseModel):
    id: int
    date: date
    powerConsumption: Decimal
    drinkingWater: Decimal
    irrigationWater: Decimal
    electricityPrice: Decimal
    efficiency: Optional[Decimal] = None
    dailyCost: Optional[Decimal] = None
    createdBy: int
    createdByName: Optional[str] = None
    updatedBy: Optional[int] = None
    updatedByName: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    
    class Config:
        from_attributes = True

class EcoRecordImport(BaseModel):
    records: List[EcoRecordCreate]
    overwriteExisting: bool = False

class EcoRecordExportParams(BaseModel):
    format: str  # json, csv
    startDate: Optional[date] = None
    endDate: Optional[date] = None
    filename: Optional[str] = None

# 操作日志相关模型
class OperationLogResponse(BaseModel):
    id: int
    userId: int
    username: str
    action: str
    tableName: str
    recordId: Optional[int] = None
    oldData: Optional[dict] = None
    newData: Optional[dict] = None
    description: Optional[str] = None
    ipAddress: Optional[str] = None
    createdAt: datetime
    
    class Config:
        from_attributes = True

# 通用响应模型
class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    details: Optional[dict] = None

class PaginationInfo(BaseModel):
    currentPage: int
    totalPages: int
    totalCount: int
    hasNext: bool
    hasPrev: bool

class DataListResponse(BaseModel):
    success: bool = True
    data: dict
    
class LogListResponse(BaseModel):
    success: bool = True
    data: dict

class ClearDataRequest(BaseModel):
    confirm: bool
    
    @validator('confirm')
    def validate_confirm(cls, v):
        if not v:
            raise ValueError('Confirm must be true to delete all data')
        return v 