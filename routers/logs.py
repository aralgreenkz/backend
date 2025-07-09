from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from datetime import date
import logging
import traceback

from database import get_db
from models import User, OperationLog
from schemas import OperationLogResponse
from auth import get_current_admin_user

# 获取日志记录器
logger = logging.getLogger('ecometrics.logs')

router = APIRouter(prefix="/logs", tags=["Operation Logs"])

@router.get("", response_model=dict)
async def get_operation_logs(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    startDate: Optional[date] = None,
    endDate: Optional[date] = None,
    userId: Optional[int] = None,
    action: Optional[str] = Query(None, regex="^(CREATE|UPDATE|DELETE)$")
):
    """Get operation logs (admin only)"""
    logger.info(f"Getting operation logs - Admin: {current_admin.username}, Page: {page}, Limit: {limit}")
    logger.debug(f"Query parameters - startDate: {startDate}, endDate: {endDate}, userId: {userId}, action: {action}")
    
    try:
        # 构建查询
        logger.debug("Building database query for operation logs...")
        query = db.query(OperationLog).join(User, OperationLog.user_id == User.id)
        
        # 筛选条件
        if startDate:
            query = query.filter(OperationLog.created_at >= startDate)
            logger.debug(f"Applied start date filter: {startDate}")
        if endDate:
            query = query.filter(OperationLog.created_at <= endDate)
            logger.debug(f"Applied end date filter: {endDate}")
        if userId:
            query = query.filter(OperationLog.user_id == userId)
            logger.debug(f"Applied user ID filter: {userId}")
        if action:
            query = query.filter(OperationLog.action == action)
            logger.debug(f"Applied action filter: {action}")
        
        # 排序
        query = query.order_by(desc(OperationLog.created_at))
        logger.debug("Applied ordering by created_at DESC")
        
        # 总数
        logger.debug("Counting total operation logs...")
        total = query.count()
        logger.info(f"Total operation logs found: {total}")
        
        # 分页
        offset = (page - 1) * limit
        logger.debug(f"Applying pagination - offset: {offset}, limit: {limit}")
        logs = query.offset(offset).limit(limit).all()
        
        # 计算分页信息
        total_pages = (total + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        logger.info(f"Retrieved {len(logs)} operation logs")
        
        # 格式化日志
        logger.debug("Formatting operation logs...")
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "id": log.id,
                "userId": log.user_id,
                "username": log.user.username,
                "action": log.action,
                "tableName": log.table_name,
                "recordId": log.record_id,
                "oldData": log.old_data,
                "newData": log.new_data,
                "description": log.description,
                "ipAddress": log.ip_address,
                "createdAt": log.created_at
            })
        
        response_data = {
            "success": True,
            "data": {
                "logs": formatted_logs,
                "pagination": {
                    "currentPage": page,
                    "totalPages": total_pages,
                    "totalCount": total,
                    "hasNext": has_next,
                    "hasPrev": has_prev
                }
            }
        }
        
        logger.info("Successfully retrieved operation logs")
        return response_data
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_operation_logs: {str(e)}")
        logger.error(f"Database error details: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_operation_logs: {str(e)}")
        logger.error(f"Error details: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve operation logs: {str(e)}"
        ) 