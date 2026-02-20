# app/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import models
from app.config import settings

# Настройка для bcrypt
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def verify_password(plain_password, hashed_password):
    """Проверка пароля"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def get_password_hash(password):
    """Хеширование пароля"""
    if isinstance(password, str):
        password = password.encode('utf-8')
    if len(password) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def authenticate_user(db: Session, email: str, password: str):
    """Аутентификация пользователя"""
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание JWT токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_token_from_request(request: Request) -> str:
    """Получить токен из cookie или заголовка"""
    # Пробуем получить из cookie
    token = request.cookies.get("access_token")
    if token:
        return token
    
    # Пробуем получить из заголовка Authorization
    auth_header = request.headers.get("Authorization")
    if auth_header:
        return auth_header
    
    return None

async def get_current_user(request: Request, db: Session = Depends(lambda: next(get_db()))):
    """Получение текущего пользователя по токену"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Получаем токен из запроса
    token = get_token_from_request(request)
    if not token:
        raise credentials_exception
    
    try:
        if token.startswith("Bearer "):
            token = token[7:]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    """Проверка активности пользователя"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Role-based dependencies
def require_client(current_user: models.User = Depends(get_current_active_user)):
    """Требуется роль клиента"""
    if current_user.role != models.UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

def require_driver(current_user: models.User = Depends(get_current_active_user)):
    """Требуется роль водителя"""
    if current_user.role != models.UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

def require_admin(current_user: models.User = Depends(get_current_active_user)):
    """Требуется роль администратора"""
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

# Database dependency
def get_db():
    """Получение сессии базы данных"""
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()