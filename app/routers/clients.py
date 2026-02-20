from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.orm import Session
from datetime import datetime

from app import schemas, models, auth
from app.auth import get_db, require_client

router = APIRouter()

@router.get("/profile", response_model=schemas.UserResponse)
async def get_client_profile(
    current_user: models.User = Depends(require_client),
    db: Session = Depends(get_db)
):
    return current_user

@router.get("/orders")
async def get_client_orders(
    current_user: models.User = Depends(require_client),
    db: Session = Depends(get_db)
):
    orders = db.query(models.Order).filter(
        models.Order.client_id == current_user.id
    ).order_by(models.Order.created_at.desc()).all()
    return orders

@router.post("/orders/create")
async def create_order_web(
    request: Request,
    pickup_location: str = Form(...),
    dropoff_location: str = Form(...),
    pickup_time: str = Form(...),
    passengers_count: int = Form(...),
    luggage_count: int = Form(...),
    client_price: float = Form(...),
    current_user: models.User = Depends(require_client),
    db: Session = Depends(get_db)
):
    pickup_datetime = datetime.fromisoformat(pickup_time)
    
    order = models.Order(
        client_id=current_user.id,
        pickup_location=pickup_location,
        dropoff_location=dropoff_location,
        pickup_time=pickup_datetime,
        passengers_count=passengers_count,
        luggage_count=luggage_count,
        client_price=client_price,
        status=models.OrderStatus.PENDING
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    return {"message": "Order created successfully", "order_id": order.id}

@router.get("/stats")
async def get_client_stats(
    current_user: models.User = Depends(require_client),
    db: Session = Depends(get_db)
):
    total_orders = db.query(models.Order).filter(
        models.Order.client_id == current_user.id
    ).count()
    
    completed_orders = db.query(models.Order).filter(
        models.Order.client_id == current_user.id,
        models.Order.status == models.OrderStatus.COMPLETED
    ).count()
    
    pending_orders = db.query(models.Order).filter(
        models.Order.client_id == current_user.id,
        models.Order.status == models.OrderStatus.PENDING
    ).count()
    
    total_spent = db.query(models.Order).filter(
        models.Order.client_id == current_user.id,
        models.Order.status == models.OrderStatus.COMPLETED
    ).with_entities(models.Order.final_price).all()
    
    total_spent_sum = sum([order[0] or 0 for order in total_spent])
    
    return {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "total_spent": total_spent_sum
    }