# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta

from app import models
from app.auth import get_db, authenticate_user, create_access_token, get_password_hash
from app.config import settings

router = APIRouter()

@router.post("/register")
async def register(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("client"),
    db: Session = Depends(get_db)
):
    """Регистрация нового пользователя"""
    # Check if user exists
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = get_password_hash(password)
    
    user = models.User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # If driver, create driver profile
    if role == "driver":
        driver_profile = models.DriverProfile(user_id=user.id)
        db.add(driver_profile)
        db.commit()
    
    return {"message": "User created successfully", "user_id": user.id}

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Вход в систему"""
    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    # Redirect based on role
    response = RedirectResponse(url=f"/{user.role}/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@router.post("/logout")
async def logout():
    """Выход из системы"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response