from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserRole(str, enum.Enum):
    CLIENT = "client"
    DRIVER = "driver"
    ADMIN = "admin"

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default=UserRole.CLIENT.value)  
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DriverProfile(Base):
    __tablename__ = "driver_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    phone = Column(String)
    experience_years = Column(Integer)
    bio = Column(Text)
    documents_status = Column(String, default=DocumentStatus.PENDING.value)
    is_verified = Column(Boolean, default=False)
    rating = Column(Float, default=0.0)
    total_trips = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class DriverDocument(Base):
    __tablename__ = "driver_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    driver_profile_id = Column(Integer, ForeignKey("driver_profiles.id"))
    document_type = Column(String)
    file_path = Column(String)
    side = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default=DocumentStatus.PENDING.value)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

class Car(Base):
    __tablename__ = "cars"
    
    id = Column(Integer, primary_key=True, index=True)
    driver_profile_id = Column(Integer, ForeignKey("driver_profiles.id"))
    make = Column(String)
    model = Column(String)
    year = Column(Integer)
    color = Column(String)
    license_plate = Column(String, unique=True)
    capacity = Column(Integer)
    has_air_conditioning = Column(Boolean, default=True)
    has_wifi = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"))
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    pickup_location = Column(String)
    dropoff_location = Column(String)
    pickup_time = Column(DateTime)
    passengers_count = Column(Integer)
    luggage_count = Column(Integer)
    
    client_price = Column(Float)
    final_price = Column(Float, nullable=True)
    
    status = Column(String, default=OrderStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class DriverReview(Base):
    __tablename__ = "driver_reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("driver_profiles.id"))
    client_id = Column(Integer, ForeignKey("users.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    rating = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminAction(Base):
    __tablename__ = "admin_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"))
    action_type = Column(String)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)