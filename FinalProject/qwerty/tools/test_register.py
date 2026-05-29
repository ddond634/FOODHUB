import json
import urllib.request

url = 'http://127.0.0.1:5000/api/auth/register'
payload = {
    'email': 'testuser+otp@example.com',
    'password': 'TestPass123!',
    'first_name': 'Test',
    'last_name': 'User',
    'role': 'customer'
}
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print('Status:', resp.status)
        print(resp.read().decode())
except Exception as e:
    print('Request failed:', e)
