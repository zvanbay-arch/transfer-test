# create_admin.py
from app import models_final
from app.auth import get_db, get_password_hash

db = next(get_db())
try:
    admin = db.query(models_final.User).filter(models_final.User.email == "admin@transferservice.com").first()
    
    if not admin:
        admin = models_final.User(
            email="admin@transferservice.com",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        print("✓ Администратор успешно создан!")
    else:
        print("Администратор уже существует")
        
    from app.auth import verify_password
    if verify_password("admin123", admin.hashed_password):
        print("✓ Пароль правильный")
    else:
        print("✗ Пароль неправильный! Обновляем...")
        admin.hashed_password = get_password_hash("admin123")
        db.commit()
        print("Пароль обновлен")
        
except Exception as e:
    print(f"Ошибка: {e}")
    db.rollback()
finally:
    db.close()