from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, asc
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import json
import csv
import io
import logging
import traceback
from fastapi.responses import StreamingResponse

from database import get_db
from models import User, EcoRecord
from schemas import (
    EcoRecordCreate, EcoRecordUpdate, EcoRecordResponse, 
    EcoRecordImport, ClearDataRequest, SuccessResponse
)
from auth import get_current_user, log_operation

# 获取日志记录器
logger = logging.getLogger('ecometrics.data')

router = APIRouter(prefix="/data", tags=["Data Management"])

def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

def calculate_efficiency_and_cost(record: EcoRecord) -> tuple:
    """Calculate efficiency and daily cost"""
    total_water = float(record.drinking_water + record.irrigation_water)
    efficiency = float(record.power_consumption) / total_water if total_water > 0 else 0
    daily_cost = float(record.power_consumption * record.electricity_price)
    return round(efficiency, 6), round(daily_cost, 2)

def format_record_response(record: EcoRecord) -> dict:
    """Format record response"""
    efficiency, daily_cost = calculate_efficiency_and_cost(record)
    
    return {
        "id": record.id,
        "date": record.date,
        "powerConsumption": float(record.power_consumption),
        "drinkingWater": float(record.drinking_water),
        "irrigationWater": float(record.irrigation_water),
        "electricityPrice": float(record.electricity_price),
        "efficiency": efficiency,
        "dailyCost": daily_cost,
        "createdBy": record.created_by,
        "createdByName": record.creator.username if record.creator else None,
        "updatedBy": record.updated_by,
        "updatedByName": record.updater.username if record.updater else None,
        "createdAt": record.created_at,
        "updatedAt": record.updated_at
    }

@router.get("", response_model=dict)
async def get_all_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
    sortBy: str = Query("date", regex="^(date|powerConsumption|drinkingWater|irrigationWater|electricityPrice)$"),
    sortOrder: str = Query("desc", regex="^(asc|desc)$")
):
    """Get all data records"""
    logger.info(f"Getting all data - User: {current_user.username}, Page: {page}, Limit: {limit}")
    logger.debug(f"Query parameters - startDate: {startDate}, endDate: {endDate}, sortBy: {sortBy}, sortOrder: {sortOrder}")
    
    try:
        # 构建查询
        logger.debug("Building database query...")
        query = db.query(EcoRecord)
        
        # 日期筛选
        if startDate:
            query = query.filter(EcoRecord.date >= startDate)
            logger.debug(f"Applied start date filter: {startDate}")
        if endDate:
            query = query.filter(EcoRecord.date <= endDate)
            logger.debug(f"Applied end date filter: {endDate}")
        
        # 排序
        sort_column = getattr(EcoRecord, sortBy.replace("powerConsumption", "power_consumption")
                                              .replace("drinkingWater", "drinking_water")
                                              .replace("irrigationWater", "irrigation_water")
                                              .replace("electricityPrice", "electricity_price"))
        if sortOrder == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        logger.debug(f"Applied sorting: {sortBy} {sortOrder}")
        
        # 总数
        logger.debug("Counting total records...")
        total = query.count()
        logger.info(f"Total records found: {total}")
        
        # 分页
        if limit:
            offset = (page - 1) * limit
            logger.debug(f"Applying pagination - offset: {offset}, limit: {limit}")
            records = query.offset(offset).limit(limit).all()
            pages = (total + limit - 1) // limit
        else:
            logger.debug("No pagination - fetching all records")
            records = query.all()
            pages = 1
        
        logger.info(f"Retrieved {len(records)} records")
        
        # 格式化响应
        logger.debug("Formatting response data...")
        formatted_records = [format_record_response(record) for record in records]
        
        # 日期范围
        date_range = {}
        if records:
            dates = [record.date for record in records]
            date_range = {
                "start": min(dates).isoformat(),
                "end": max(dates).isoformat()
            }
            logger.debug(f"Date range: {date_range}")
        
        response_data = {
            "success": True,
            "data": {
                "records": formatted_records,
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "pages": pages
                },
                "summary": {
                    "totalRecords": total,
                    "dateRange": date_range
                }
            }
        }
        
        logger.info("Successfully retrieved data")
        return response_data
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_all_data: {str(e)}")
        logger.error(f"Database error details: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_all_data: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve data: {str(e)}"
        )

@router.post("", response_model=dict)
async def create_data(
    record_data: EcoRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create data record"""
    logger.info(f"Creating new data record - User: {current_user.username}, Date: {record_data.date}")
    logger.debug(f"Record data: {record_data}")
    
    try:
        # 检查日期是否已存在
        logger.debug(f"Checking if date {record_data.date} already exists...")
        existing_record = db.query(EcoRecord).filter(EcoRecord.date == record_data.date).first()
        if existing_record:
            logger.warning(f"Date {record_data.date} already exists - record ID: {existing_record.id}")
            return {
                "success": False,
                "error": "Validation failed",
                "message": "Date already exists",
                "details": {
                    "field": "date",
                    "code": "DUPLICATE_DATE"
                }
            }
        
        logger.debug("Date is unique, creating new record...")
        
        # 创建新记录
        new_record = EcoRecord(
            date=record_data.date,
            power_consumption=record_data.powerConsumption,
            drinking_water=record_data.drinkingWater,
            irrigation_water=record_data.irrigationWater,
            electricity_price=record_data.electricityPrice,
            created_by=current_user.id
        )
        
        logger.debug(f"Adding new record to database session...")
        db.add(new_record)
        
        logger.debug("Committing transaction...")
        db.commit()
        
        logger.debug("Refreshing record to get generated ID...")
        db.refresh(new_record)
        
        logger.info(f"Successfully created record with ID: {new_record.id}")
        
        # 记录操作日志 - 确保在新事务中记录
        try:
            logger.debug("Recording operation log...")
            # 转换数据为JSON可序列化格式
            new_data_serializable = {
                "date": record_data.date.isoformat(),
                "powerConsumption": float(record_data.powerConsumption),
                "drinkingWater": float(record_data.drinkingWater),
                "irrigationWater": float(record_data.irrigationWater),
                "electricityPrice": float(record_data.electricityPrice)
            }
            
            log_operation(
                db=db,
                user_id=current_user.id,
                action="CREATE",
                table_name="eco_records",
                record_id=new_record.id,
                new_data=new_data_serializable,
                description=f"Created water and electricity record ({record_data.date})",
                ip_address=get_client_ip(request)
            )
            logger.debug("Operation log recorded successfully")
        except Exception as log_error:
            # 日志记录失败不影响主业务，但要记录错误
            logger.error(f"Failed to log CREATE operation: {log_error}")
            logger.error(f"Log error details: {traceback.format_exc()}")
            logger.error(f"Record ID: {new_record.id}, User ID: {current_user.id}")
        
        response_data = {
            "success": True,
            "message": "Data record created successfully",
            "data": format_record_response(new_record)
        }
        
        logger.info("Data creation completed successfully")
        return response_data
        
    except IntegrityError as e:
        logger.error(f"Integrity error in create_data: {str(e)}")
        logger.error(f"Integrity error details: {traceback.format_exc()}")
        db.rollback()
        return {
            "success": False,
            "error": "Validation failed",
            "message": "Date already exists",
            "details": {
                "field": "date",
                "code": "DUPLICATE_DATE"
            }
        }
    except SQLAlchemyError as e:
        logger.error(f"Database error in create_data: {str(e)}")
        logger.error(f"Database error details: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in create_data: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create data record: {str(e)}"
        )

@router.put("/{record_id}", response_model=dict)
async def update_data(
    record_id: int,
    record_data: EcoRecordUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update data record"""
    try:
        # 查找记录
        record = db.query(EcoRecord).filter(EcoRecord.id == record_id).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found"
            )
        
        # 保存修改前的数据
        old_data = {
            "date": record.date.isoformat(),
            "powerConsumption": float(record.power_consumption),
            "drinkingWater": float(record.drinking_water),
            "irrigationWater": float(record.irrigation_water),
            "electricityPrice": float(record.electricity_price)
        }
        
        # 更新字段
        update_data = {}
        if record_data.powerConsumption is not None:
            record.power_consumption = record_data.powerConsumption
            update_data["powerConsumption"] = float(record_data.powerConsumption)
        if record_data.drinkingWater is not None:
            record.drinking_water = record_data.drinkingWater
            update_data["drinkingWater"] = float(record_data.drinkingWater)
        if record_data.irrigationWater is not None:
            record.irrigation_water = record_data.irrigationWater
            update_data["irrigationWater"] = float(record_data.irrigationWater)
        if record_data.electricityPrice is not None:
            record.electricity_price = record_data.electricityPrice
            update_data["electricityPrice"] = float(record_data.electricityPrice)
        
        record.updated_by = current_user.id
        record.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(record)
        
        # 记录操作日志
        log_operation(
            db=db,
            user_id=current_user.id,
            action="UPDATE",
            table_name="eco_records",
            record_id=record.id,
            old_data=old_data,
            new_data=update_data,
            description=f"Updated water and electricity record ({record.date})",
            ip_address=get_client_ip(request)
        )
        
        return {
            "success": True,
            "message": "Data record updated successfully",
            "data": format_record_response(record)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update data record"
        )

@router.delete("/{record_id}", response_model=dict)
async def delete_data(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete data record"""
    try:
        # 查找记录
        record = db.query(EcoRecord).filter(EcoRecord.id == record_id).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Record not found"
            )
        
        # 保存删除前的数据
        old_data = {
            "date": record.date.isoformat(),
            "powerConsumption": float(record.power_consumption),
            "drinkingWater": float(record.drinking_water),
            "irrigationWater": float(record.irrigation_water),
            "electricityPrice": float(record.electricity_price)
        }
        
        # 删除记录
        db.delete(record)
        db.commit()
        
        # 记录操作日志
        log_operation(
            db=db,
            user_id=current_user.id,
            action="DELETE",
            table_name="eco_records",
            record_id=record_id,
            old_data=old_data,
            description=f"Deleted water and electricity record ({old_data['date']})",
            ip_address=get_client_ip(request)
        )
        
        return {
            "success": True,
            "message": "Data record deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete data record"
        )

@router.delete("", response_model=dict)
async def clear_all_data(
    clear_request: ClearDataRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear all data"""
    try:
        # 获取要删除的记录数
        count = db.query(EcoRecord).count()
        
        # 删除所有记录
        db.query(EcoRecord).delete()
        db.commit()
        
        # 记录操作日志
        log_operation(
            db=db,
            user_id=current_user.id,
            action="DELETE",
            table_name="eco_records",
            description=f"Cleared all data ({count} records)",
            ip_address=get_client_ip(request)
        )
        
        return {
            "success": True,
            "message": "All data records deleted successfully",
            "data": {
                "deletedCount": count,
                "warning": "All system data has been permanently deleted"
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear all data"
        )

@router.post("/import", response_model=dict)
async def import_data(
    import_data: EcoRecordImport,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Batch import data"""
    try:
        imported = 0
        updated = 0
        skipped = 0
        errors = []
        
        for record_data in import_data.records:
            try:
                # 检查是否已存在
                existing_record = db.query(EcoRecord).filter(EcoRecord.date == record_data.date).first()
                
                if existing_record:
                    if import_data.overwriteExisting:
                        # 更新现有记录
                        existing_record.power_consumption = record_data.powerConsumption
                        existing_record.drinking_water = record_data.drinkingWater
                        existing_record.irrigation_water = record_data.irrigationWater
                        existing_record.electricity_price = record_data.electricityPrice
                        existing_record.updated_by = current_user.id
                        existing_record.updated_at = datetime.utcnow()
                        updated += 1
                    else:
                        skipped += 1
                        continue
                else:
                    # 创建新记录
                    new_record = EcoRecord(
                        date=record_data.date,
                        power_consumption=record_data.powerConsumption,
                        drinking_water=record_data.drinkingWater,
                        irrigation_water=record_data.irrigationWater,
                        electricity_price=record_data.electricityPrice,
                        created_by=current_user.id
                    )
                    db.add(new_record)
                    imported += 1
                    
            except Exception as e:
                errors.append(f"Error importing record for {record_data.date}: {str(e)}")
                continue
        
        db.commit()
        
        # 记录操作日志
        log_operation(
            db=db,
            user_id=current_user.id,
            action="CREATE",
            table_name="eco_records",
            description=f"Batch imported data (imported: {imported}, updated: {updated}, skipped: {skipped})",
            ip_address=get_client_ip(request)
        )
        
        return {
            "success": True,
            "message": "Data imported successfully",
            "data": {
                "imported": imported,
                "updated": updated,
                "skipped": skipped,
                "errors": errors
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import data"
        )

@router.get("/export", response_model=dict)
async def export_data(
    format: str = Query(..., regex="^(json|csv)$"),
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
    filename: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export data"""
    try:
        # 构建查询
        query = db.query(EcoRecord)
        
        if startDate:
            query = query.filter(EcoRecord.date >= startDate)
        if endDate:
            query = query.filter(EcoRecord.date <= endDate)
        
        records = query.order_by(EcoRecord.date).all()
        
        if format == "json":
            # JSON格式导出
            formatted_records = [format_record_response(record) for record in records]
            
            return {
                "success": True,
                "data": {
                    "records": formatted_records,
                    "metadata": {
                        "exportDate": datetime.utcnow().isoformat(),
                        "totalRecords": len(records),
                        "format": "json"
                    }
                }
            }
        
        elif format == "csv":
            # CSV格式导出
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入标题行
            writer.writerow([
                "Date", "Power Consumption (kWh)", "Drinking Water (L)", 
                "Irrigation Water (L)", "Electricity Price (KZT/kWh)", 
                "Efficiency", "Daily Cost (KZT)", "Created By", "Updated By"
            ])
            
            # 写入数据行
            for record in records:
                efficiency, daily_cost = calculate_efficiency_and_cost(record)
                writer.writerow([
                    record.date.isoformat(),
                    float(record.power_consumption),
                    float(record.drinking_water),
                    float(record.irrigation_water),
                    float(record.electricity_price),
                    efficiency,
                    daily_cost,
                    record.creator.username if record.creator else "",
                    record.updater.username if record.updater else ""
                ])
            
            output.seek(0)
            
            # 设置文件名
            if not filename:
                filename = f"ecometrics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            elif not filename.endswith('.csv'):
                filename += '.csv'
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export data"
        ) 