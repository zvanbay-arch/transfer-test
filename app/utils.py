from fastapi import Request

def get_token_from_request(request: Request) -> str:
    """Получить токен из cookie или заголовка"""
 
    token = request.cookies.get("access_token")
    if token:
        return token

    auth_header = request.headers.get("Authorization")
    if auth_header:
        return auth_header
    
    return None