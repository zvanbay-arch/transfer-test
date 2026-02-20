# app/routers/orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app import models, auth
from app.auth import get_db, require_client, require_driver

router = APIRouter()

@router.post("/create")
async def create_order(
    order_data: dict,
    current_user: models.User = Depends(require_client),
    db: Session = Depends(get_db)
):
    db_order = models.Order(
        client_id=current_user.id,
        pickup_location=order_data.get("pickup_location"),
        dropoff_location=order_data.get("dropoff_location"),
        pickup_time=datetime.fromisoformat(order_data.get("pickup_time")),
        passengers_count=order_data.get("passengers_count"),
        luggage_count=order_data.get("luggage_count"),
        client_price=order_data.get("client_price"),
        status="pending"
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@router.get("/driver/my-orders")
async def get_driver_orders(
    current_user: models.User = Depends(require_driver),
    db: Session = Depends(get_db)
):
    orders = db.query(models.Order).filter(
        models.Order.driver_id == current_user.id
    ).order_by(models.Order.created_at.desc()).all()
    return orders

@router.get("/{order_id}")
async def get_order(
    order_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if current_user.role == "client" and order.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    
    if current_user.role == "driver" and order.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    
    return order

@router.post("/{order_id}/complete")
async def complete_order(
    order_id: int,
    current_user: models.User = Depends(require_driver),
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your order")
    
    if order.status != "accepted":
        raise HTTPException(status_code=400, detail="Order cannot be completed")
    
    order.status = "completed"
    order.completed_at = datetime.now()
    order.final_price = order.client_price
    
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == current_user.id
    ).first()
    if profile:
        profile.total_trips += 1
    
    db.commit()
    
    return {"message": "Order completed successfully"}

@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    current_user: models.User = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if current_user.role == "client" and order.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
    
    if current_user.role == "driver" and order.driver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
    
    if order.status in ["completed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Order already completed or cancelled")
    
    order.status = "cancelled"
    
    db.commit()
    
    return {"message": "Order cancelled successfully"}