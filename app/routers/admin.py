from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app import schemas, models, auth
from app.auth import get_db, require_admin

router = APIRouter()

@router.get("/dashboard")
async def admin_dashboard(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # Get counts
    total_users = db.query(models.User).count()
    total_clients = db.query(models.User).filter(
        models.User.role == models.UserRole.CLIENT
    ).count()
    total_drivers = db.query(models.User).filter(
        models.User.role == models.UserRole.DRIVER
    ).count()
    
    pending_drivers = db.query(models.DriverProfile).filter(
        models.DriverProfile.documents_status == models.DocumentStatus.PENDING
    ).count()
    
    total_orders = db.query(models.Order).count()
    pending_orders = db.query(models.Order).filter(
        models.Order.status == models.OrderStatus.PENDING
    ).count()
    completed_orders = db.query(models.Order).filter(
        models.Order.status == models.OrderStatus.COMPLETED
    ).count()
    
    # Calculate revenue
    completed_trips = db.query(models.Order).filter(
        models.Order.status == models.OrderStatus.COMPLETED
    ).all()
    total_revenue = sum([trip.final_price or 0 for trip in completed_trips])
    
    return {
        "stats": {
            "total_users": total_users,
            "total_clients": total_clients,
            "total_drivers": total_drivers,
            "pending_drivers": pending_drivers,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "completed_orders": completed_orders,
            "total_revenue": total_revenue
        }
    }

@router.get("/users")
async def get_all_users(
    role: Optional[str] = None,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role)
    
    users = query.all()
    return users

@router.get("/drivers/pending")
async def get_pending_drivers(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    pending_profiles = db.query(models.DriverProfile).filter(
        models.DriverProfile.documents_status == models.DocumentStatus.PENDING
    ).all()
    
    result = []
    for profile in pending_profiles:
        user = db.query(models.User).filter(models.User.id == profile.user_id).first()
        documents = db.query(models.DriverDocument).filter(
            models.DriverDocument.driver_profile_id == profile.id
        ).all()
        
        result.append({
            "profile_id": profile.id,
            "user": user,
            "documents": documents,
            "submitted_at": profile.created_at
        })
    
    return result

@router.post("/drivers/{driver_id}/approve")
async def approve_driver(
    driver_id: int,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == driver_id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    # Update all documents
    documents = db.query(models.DriverDocument).filter(
        models.DriverDocument.driver_profile_id == profile.id
    ).all()
    
    for doc in documents:
        doc.status = models.DocumentStatus.APPROVED
        doc.reviewed_by = current_user.id
        doc.reviewed_at = datetime.now()
    
    profile.documents_status = models.DocumentStatus.APPROVED
    profile.is_verified = True
    
    # Log admin action
    admin_action = models.AdminAction(
        admin_id=current_user.id,
        action_type="approve_driver",
        target_user_id=driver_id,
        details="Driver approved"
    )
    db.add(admin_action)
    
    db.commit()
    
    return {"message": "Driver approved successfully"}

@router.post("/drivers/{driver_id}/reject")
async def reject_driver(
    driver_id: int,
    reason: str = Form(...),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == driver_id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    # Update all documents
    documents = db.query(models.DriverDocument).filter(
        models.DriverDocument.driver_profile_id == profile.id
    ).all()
    
    for doc in documents:
        doc.status = models.DocumentStatus.REJECTED
        doc.reviewed_by = current_user.id
        doc.reviewed_at = datetime.now()
        doc.rejection_reason = reason
    
    profile.documents_status = models.DocumentStatus.REJECTED
    profile.is_verified = False
    
    # Log admin action
    admin_action = models.AdminAction(
        admin_id=current_user.id,
        action_type="reject_driver",
        target_user_id=driver_id,
        details=f"Driver rejected: {reason}"
    )
    db.add(admin_action)
    
    db.commit()
    
    return {"message": "Driver rejected"}

@router.get("/orders/all")
async def get_all_orders(
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(models.Order)
    
    if status:
        query = query.filter(models.Order.status == status)
    
    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.filter(models.Order.created_at >= start)
    
    if end_date:
        end = datetime.fromisoformat(end_date)
        query = query.filter(models.Order.created_at <= end)
    
    orders = query.order_by(models.Order.created_at.desc()).all()
    
    result = []
    for order in orders:
        client = db.query(models.User).filter(models.User.id == order.client_id).first()
        driver = None
        if order.driver_id:
            driver = db.query(models.User).filter(models.User.id == order.driver_id).first()
        
        result.append({
            "order": order,
            "client": client,
            "driver": driver
        })
    
    return result

@router.get("/statistics/full")
async def get_full_statistics(
    period: str = "month",  # day, week, month, year
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    now = datetime.now()
    
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = now - timedelta(days=30)
    
    # Get orders in period
    orders = db.query(models.Order).filter(
        models.Order.created_at >= start_date
    ).all()
    
    # User registrations in period
    new_users = db.query(models.User).filter(
        models.User.created_at >= start_date
    ).count()
    
    new_clients = db.query(models.User).filter(
        models.User.role == models.UserRole.CLIENT,
        models.User.created_at >= start_date
    ).count()
    
    new_drivers = db.query(models.User).filter(
        models.User.role == models.UserRole.DRIVER,
        models.User.created_at >= start_date
    ).count()
    
    # Order statistics
    total_orders = len(orders)
    completed_orders = sum(1 for o in orders if o.status == models.OrderStatus.COMPLETED)
    cancelled_orders = sum(1 for o in orders if o.status == models.OrderStatus.CANCELLED)
    
    # Revenue
    revenue = sum(o.final_price or 0 for o in orders if o.status == models.OrderStatus.COMPLETED)
    
    # Average order value
    avg_order_value = revenue / completed_orders if completed_orders > 0 else 0
    
    return {
        "period": period,
        "start_date": start_date,
        "end_date": now,
        "new_users": new_users,
        "new_clients": new_clients,
        "new_drivers": new_drivers,
        "orders": {
            "total": total_orders,
            "completed": completed_orders,
            "cancelled": cancelled_orders,
            "pending": total_orders - completed_orders - cancelled_orders
        },
        "revenue": revenue,
        "average_order_value": avg_order_value
    }