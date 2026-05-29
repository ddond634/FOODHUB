from dotenv import load_dotenv
import os, requests
load_dotenv('.env')
SUPA_URL=os.getenv('Supabase_URL')
SERVICE=os.getenv('Supabase_Service_role_key')
print('SUPA_URL', SUPA_URL)
print('SERVICE present', bool(SERVICE))
headers={'apikey':SERVICE,'Authorization':'Bearer '+SERVICE}
url=SUPA_URL.rstrip('/')+'/auth/v1/admin/users'
resp = requests.get(url, headers=headers)
print('status', resp.status_code)
try:
    j=resp.json()
    print('json type', type(j))
    if isinstance(j, list):
        print('count', len(j))
        if len(j)>0:
            print('first item type', type(j[0]))
            print('first item keys' , (j[0].keys() if isinstance(j[0], dict) else 'not dict'))
            print('sample email', (j[0].get('email') if isinstance(j[0], dict) else str(j[0])[:200]))
    else:
        print('resp json', j)
except Exception as e:
    print('json error', e)
    print(resp.text[:1000])
