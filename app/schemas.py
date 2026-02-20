from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    CLIENT = "client"
    DRIVER = "driver"
    ADMIN = "admin"

class DocumentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class OrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.CLIENT

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Driver schemas
class DriverProfileBase(BaseModel):
    phone: str
    experience_years: int
    bio: Optional[str] = None

class DriverProfileCreate(DriverProfileBase):
    pass

class DriverProfileResponse(DriverProfileBase):
    id: int
    user_id: int
    documents_status: DocumentStatus
    is_verified: bool
    rating: float
    total_trips: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Car schemas
class CarBase(BaseModel):
    make: str
    model: str
    year: int
    color: str
    license_plate: str
    capacity: int
    has_air_conditioning: bool = True
    has_wifi: bool = False

class CarCreate(CarBase):
    pass

class CarResponse(CarBase):
    id: int
    driver_profile_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Order schemas
class OrderBase(BaseModel):
    pickup_location: str
    dropoff_location: str
    pickup_time: datetime
    passengers_count: int = Field(ge=1, le=8)
    luggage_count: int = Field(ge=0)
    client_price: float = Field(gt=0)

class OrderCreate(OrderBase):
    pass

class OrderResponse(OrderBase):
    id: int
    client_id: int
    driver_id: Optional[int] = None
    final_price: Optional[float] = None
    status: OrderStatus
    created_at: datetime
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Document schemas
class DocumentResponse(BaseModel):
    id: int
    document_type: str
    file_path: str
    side: Optional[str] = None
    uploaded_at: datetime
    status: DocumentStatus
    
    class Config:
        from_attributes = True

# Statistics schemas
class DriverStats(BaseModel):
    total_trips: int
    total_earnings: float
    average_rating: float
    completed_orders: int
    cancelled_orders: int
    pending_orders: int

class AdminStats(BaseModel):
    total_users: int
    total_clients: int
    total_drivers: int
    pending_drivers: int
    total_orders: int
    pending_orders: int
    completed_orders: int
    total_revenue: float