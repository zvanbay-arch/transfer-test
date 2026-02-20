# app/routers/drivers.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List
import shutil
from datetime import datetime
from pathlib import Path

from app import models, auth
from app.auth import get_db, require_driver
from app.config import settings

router = APIRouter()

@router.get("/profile")
async def get_driver_profile(
    request: Request,
    current_user: models.User = Depends(require_driver),
    db: Session = Depends(get_db)
):
    """Получение профиля водителя"""
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == current_user.id
    ).first()
    
    documents = []
    cars = []
    
    if profile:
        documents = db.query(models.DriverDocument).filter(
            models.DriverDocument.driver_profile_id == profile.id
        ).all()
        cars = db.query(models.Car).filter(
            models.Car.driver_profile_id == profile.id
        ).all()
    
    # Преобразуем документы в словари для JSON
    docs_list = []
    for doc in documents:
        docs_list.append({
            "id": doc.id,
            "document_type": doc.document_type,
            "file_path": doc.file_path,
            "side": doc.side,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at
        })
    
    # Преобразуем машины в словари
    cars_list = []
    for car in cars:
        cars_list.append({
            "id": car.id,
            "make": car.make,
            "model": car.model,
            "year": car.year,
            "color": car.color,
            "license_plate": car.license_plate,
            "capacity": car.capacity,
            "has_air_conditioning": car.has_air_conditioning,
            "has_wifi": car.has_wifi
        })
    
    profile_dict = None
    if profile:
        profile_dict = {
            "id": profile.id,
            "phone": profile.phone,
            "experience_years": profile.experience_years,
            "bio": profile.bio,
            "documents_status": profile.documents_status,
            "is_verified": profile.is_verified,
            "rating": profile.rating,
            "total_trips": profile.total_trips
        }
    
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "created_at": current_user.created_at
        },
        "profile": profile_dict,
        "documents": docs_list,
        "cars": cars_list
    }

@router.post("/profile/update")
async def update_driver_profile(
    request: Request,
    phone: str = Form(...),
    experience_years: int = Form(...),
    bio: str = Form(None),
    current_user: models.User = Depends(require_driver),
    db: Session = Depends(get_db)
):
    """Обновление профиля водителя"""
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        profile = models.DriverProfile(user_id=current_user.id)
        db.add(profile)
    
    profile.phone = phone
    profile.experience_years = experience_years
    profile.bio = bio
    
    db.commit()
    
    return {"message": "Profile updated successfully"}

@router.post("/cars/add")
async def add_car(
    request: Request,
    make: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    color: str = Form(...),
    license_plate: str = Form(...),
    capacity: int = Form(...),
    has_air_conditioning: bool = Form(True),
    has_wifi: bool = Form(False),
    current_user: models.User = Depends(require_driver),
    db: Session = Depends(get_db)
):
    """Добавление автомобиля"""
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Driver profile not found. Please update your profile first.")
    
    # Check if license plate already exists
    existing_car = db.query(models.Car).filter(
        models.Car.license_plate == license_plate
    ).first()
    
    if existing_car:
        raise HTTPException(status_code=400, detail="License plate already registered")
    
    car = models.Car(
        driver_profile_id=profile.id,
        make=make,
        model=model,
        year=year,
        color=color,
        license_plate=license_plate,
        capacity=capacity,
        has_air_conditioning=has_air_conditioning,
        has_wifi=has_wifi
    )
    
    db.add(car)
    db.commit()
    
    return {"message": "Car added successfully", "car_id": car.id}

@router.post("/documents/upload")
async def upload_documents(
    request: Request,
    current_user: models.User = Depends(require_driver),
    db: Session = Depends(get_db),
    car_photos: List[UploadFile] = File(..., description="4 photos of the car"),
    tech_passport_front: UploadFile = File(..., description="Technical passport front"),
    tech_passport_back: UploadFile = File(..., description="Technical passport back"),
    license_front: UploadFile = File(..., description="Driver's license front"),
    license_back: UploadFile = File(..., description="Driver's license back"),
    selfie: UploadFile = File(..., description="Selfie with license")
):
    """Загрузка документов для верификации"""
    # Validate number of car photos
    if len(car_photos) != 4:
        raise HTTPException(status_code=400, detail="Please upload exactly 4 car photos")
    
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        profile = models.DriverProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    # Create user-specific directory
    user_upload_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
    user_upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Function to save file
    async def save_file(file: UploadFile, subdir: str, filename: str) -> str:
        # Create subdirectory
        file_dir = user_upload_dir / subdir
        file_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = file_dir / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return relative path from upload directory
        relative_path = Path(str(current_user.id)) / subdir / filename
        return str(relative_path)
    
    # Save car photos
    for i, photo in enumerate(car_photos):
        file_path = await save_file(photo, "car_photos", f"car_photo_{i+1}.jpg")
        document = models.DriverDocument(
            driver_profile_id=profile.id,
            document_type="car_photo",
            file_path=file_path,
            side=None,
            status="pending"
        )
        db.add(document)
    
    # Save tech passport
    tech_front_path = await save_file(tech_passport_front, "tech_passport", "front.jpg")
    document = models.DriverDocument(
        driver_profile_id=profile.id,
        document_type="tech_passport",
        file_path=tech_front_path,
        side="front",
        status="pending"
    )
    db.add(document)
    
    tech_back_path = await save_file(tech_passport_back, "tech_passport", "back.jpg")
    document = models.DriverDocument(
        driver_profile_id=profile.id,
        document_type="tech_passport",
        file_path=tech_back_path,
        side="back",
        status="pending"
    )
    db.add(document)
    
    # Save license
    license_front_path = await save_file(license_front, "license", "front.jpg")
    document = models.DriverDocument(
        driver_profile_id=profile.id,
        document_type="license",
        file_path=license_front_path,
        side="front",
        status="pending"
    )
    db.add(document)
    
    license_back_path = await save_file(license_back, "license", "back.jpg")
    document = models.DriverDocument(
        driver_profile_id=profile.id,
        document_type="license",
        file_path=license_back_path,
        side="back",
        status="pending"
    )
    db.add(document)
    
    # Save selfie
    selfie_path = await save_file(selfie, "selfie", "selfie.jpg")
    document = models.DriverDocument(
        driver_profile_id=profile.id,
        document_type="selfie",
        file_path=selfie_path,
        side=None,
        status="pending"
    )
    db.add(document)
    
    # Update profile status
    profile.documents_status = "pending"
    
    db.commit()
    
    return {"message": "Documents uploaded successfully. Waiting for admin approval."}

@router.get("/documents/status")
async def get_documents_status(
    request: Request,
    current_user: models.User = Depends(require_driver),
    db: Session = Depends(get_db)
):
    """Получение статуса документов"""
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        return {"status": "not_found", "message": "Profile not found"}
    
    documents = db.query(models.DriverDocument).filter(
        models.DriverDocument.driver_profile_id == profile.id
    ).all()
    
    return {
        "status": profile.documents_status,
        "is_verified": profile.is_verified,
        "documents_count": len(documents),
        "documents": documents
    }

@router.get("/available-orders")
async def get_available_orders(
    request: Request,
    current_user: models.User = Depends(require_driver),
    db: Session = Depends(get_db)
):
    """Получение доступных заказов"""
    # Check if driver is verified
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == current_user.id
    ).first()
    
    if not profile or profile.documents_status != "approved":
        raise HTTPException(status_code=403, detail="Your account is not verified yet")
    
    # Get pending orders
    orders = db.query(models.Order).filter(
        models.Order.status == "pending",
        models.Order.pickup_time >= datetime.now()
    ).order_by(models.Order.created_at.desc()).all()
    
    # Преобразуем в словари для JSON
    orders_list = []
    for order in orders:
        orders_list.append({
            "id": order.id,
            "pickup_location": order.pickup_location,
            "dropoff_location": order.dropoff_location,
            "pickup_time": order.pickup_time,
            "passengers_count": order.passengers_count,
            "luggage_count": order.luggage_count,
            "client_price": order.client_price,
            "status": order.status,
            "created_at": order.created_at
        })
    
    return orders_list

@router.post("/orders/{order_id}/accept")
async def accept_order(
    request: Request,
    order_id: int,
    current_user: models.User = Depends(require_driver),
    db: Session = Depends(get_db)
):
    """Принятие заказа водителем"""
    # Check if driver is verified
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == current_user.id
    ).first()
    
    if not profile or profile.documents_status != "approved":
        raise HTTPException(status_code=403, detail="Your account is not verified yet")
    
    # Get order
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status != "pending":
        raise HTTPException(status_code=400, detail="Order is not available")
    
    # Accept order
    order.driver_id = current_user.id
    order.status = "accepted"
    order.accepted_at = datetime.now()
    
    db.commit()
    
    return {"message": "Order accepted successfully"}

@router.get("/stats")
async def get_driver_stats(
    request: Request,
    current_user: models.User = Depends(require_driver),
    db: Session = Depends(get_db)
):
    """Получение статистики водителя"""
    profile = db.query(models.DriverProfile).filter(
        models.DriverProfile.user_id == current_user.id
    ).first()
    
    # Get order statistics
    total_orders = db.query(models.Order).filter(
        models.Order.driver_id == current_user.id
    ).count()
    
    completed_orders = db.query(models.Order).filter(
        models.Order.driver_id == current_user.id,
        models.Order.status == "completed"
    ).count()
    
    cancelled_orders = db.query(models.Order).filter(
        models.Order.driver_id == current_user.id,
        models.Order.status == "cancelled"
    ).count()
    
    pending_orders = db.query(models.Order).filter(
        models.Order.driver_id == current_user.id,
        models.Order.status == "accepted"
    ).count()
    
    # Calculate earnings
    completed_trips = db.query(models.Order).filter(
        models.Order.driver_id == current_user.id,
        models.Order.status == "completed"
    ).all()
    
    total_earnings = sum([trip.final_price or trip.client_price or 0 for trip in completed_trips])
    
    return {
        "total_trips": total_orders,
        "completed_trips": completed_orders,
        "cancelled_trips": cancelled_orders,
        "pending_trips": pending_orders,
        "total_earnings": total_earnings,
        "rating": profile.rating if profile else 0,
        "verification_status": profile.documents_status if profile else "not_found"
    }