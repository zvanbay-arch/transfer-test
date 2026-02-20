from app import models_final
from app.auth import get_db

db = next(get_db())
try:
    # Проверяем всех пользователей
    users = db.query(models_final.User).all()
    print(f"Всего пользователей в базе: {len(users)}")
    
    for user in users:
        print(f"ID: {user.id}, Email: {user.email}, Role: {user.role}, Name: {user.full_name}")
    
    # Проверяем конкретно админа
    admin = db.query(models_final.User).filter(models_final.User.email == "admin@transferservice.com").first()
    if admin:
        print("\n✓ Администратор найден!")
    else:
        print("\n✗ Администратор НЕ найден в базе данных")
        
except Exception as e:
    print(f"Ошибка: {e}")
finally:
    db.close()