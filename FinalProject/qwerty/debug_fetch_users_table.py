from dotenv import load_dotenv
import os, requests
load_dotenv('.env')
SUPA=os.getenv('Supabase_URL')
SKEY=os.getenv('Supabase_Service_role_key')
headers={'apikey':SKEY,'Authorization':'Bearer '+SKEY}
url=SUPA.rstrip('/')+'/rest/v1/users?select=*'
resp=requests.get(url, headers=headers)
print('status', resp.status_code)
print(resp.text[:2000])
