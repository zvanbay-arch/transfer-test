# app/main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

from app import models
from app import auth
from app.routers import auth as auth_router, clients, drivers, admin, orders
from app.config import settings

# Create upload directory if it doesn't exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Transfer Service API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth_router.router, prefix="/api/auth", tags=["authentication"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(drivers.router, prefix="/api/drivers", tags=["drivers"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])

# Web routes
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/client/dashboard")
async def client_dashboard(request: Request):
    return templates.TemplateResponse("client/dashboard.html", {"request": request})

@app.get("/driver/dashboard")
async def driver_dashboard(request: Request):
    return templates.TemplateResponse("driver/dashboard.html", {"request": request})

@app.get("/driver/upload-documents")
async def driver_upload_documents(request: Request):
    return templates.TemplateResponse("driver/upload_documents.html", {"request": request})

@app.get("/admin/dashboard")
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})

# Create default admin user on startup
@app.on_event("startup")
def create_admin_user():
    print("Проверка наличия администратора...")
    db = next(auth.get_db())
    try:
        admin_email = "admin@transferservice.com"
        admin = db.query(models.User).filter(models.User.email == admin_email).first()
        if not admin:
            print("Администратор не найден. Создаю нового...")
            from app.auth import get_password_hash
            admin = models.User(
                email=admin_email,
                hashed_password=get_password_hash("admin123"),
                full_name="System Administrator",
                role="admin",
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("✓ Администратор успешно создан!")
            print("  Email: admin@transferservice.com")
            print("  Password: admin123")
        else:
            print("✓ Администратор уже существует")
    except Exception as e:
        print(f"✗ Ошибка при создании администратора: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)