#!/usr/bin/env python3
import requests
import jwt

JWT_SECRET = 'dev-jwt-secret-change-in-prod'

def make_token(user_id=4, role='customer', email='user@example.com'):
    from datetime import datetime, timedelta
    payload = {
        'user_id': user_id,
        'role': role,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

if __name__ == '__main__':
    token = make_token()
    headers = {'Authorization': f'Bearer {token}'}
    url = 'http://127.0.0.1:5000/api/wishlist'
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print('Status:', r.status_code)
        print('JSON:', r.json())
    except Exception as e:
        print('Error:', e)
