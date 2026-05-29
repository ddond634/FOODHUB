#!/usr/bin/env python3
"""Insert users/sellers/products into Supabase for existing Auth users.
This script finds auth users by email via the Admin users endpoint, then
inserts rows into `users`, `sellers`, and `products` using PostgREST.
"""
import os, sys, time
from dotenv import load_dotenv
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, '.env'))

SUPA_URL = os.getenv('Supabase_URL') or os.getenv('SUPABASE_URL')
SERVICE_ROLE = os.getenv('Supabase_Service_role_key') or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
if not SUPA_URL or not SERVICE_ROLE:
    print('Missing Supabase URL or service role key')
    sys.exit(1)

HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json'
}

def find_auth_user(email):
    url = SUPA_URL.rstrip('/') + '/auth/v1/admin/users'
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        print('Failed to fetch users list:', r.status_code, r.text)
        return None
    users = r.json()
    # Supabase may return {'users': [...], 'aud': 'authenticated'}
    if isinstance(users, dict) and 'users' in users:
        users = users['users']
    import json
    for u in users:
        try:
            if isinstance(u, dict):
                ue = u.get('email','')
            elif isinstance(u, str):
                parsed = json.loads(u)
                ue = parsed.get('email','')
                u = parsed
            else:
                ue = ''
        except Exception:
            ue = ''
        if ue and ue.lower() == email.lower():
            return u
    return None

def insert_row(table, payload):
    url = SUPA_URL.rstrip('/') + f'/rest/v1/{table}'
    h = HEADERS.copy(); h['Prefer']='return=representation'
    r = requests.post(url, headers=h, json=payload)
    if r.status_code in (200,201):
        return r.json()
    print('Insert failed', table, r.status_code, r.text)
    return None

def main():
    emails = [ 'admin@example.com','buyer@example.com','rider@example.com',
               'seller1@example.com','seller2@example.com','seller3@example.com','seller4@example.com','seller5@example.com']

    products_by_seller = {
        'seller1@example.com': [ { 'title':'Organic Lettuce Bundle','description':'Crisp organic lettuce','price':120.00,'stock':20,'img_url':'/uploads/products/fresh-greens-lettuce.jpg','category':'Produce'} ],
        'seller2@example.com': [ { 'title':'Crunchy Nacho Chips','description':'Salted nacho chips','price':95.00,'stock':50,'img_url':'/uploads/products/metro-snacks-nachos.jpg','category':'Snacks'} ],
        'seller3@example.com': [ { 'title':'Classic Chicken Adobo','description':'Hearty chicken adobo meal','price':220.00,'stock':18,'img_url':'/uploads/products/daily-bites-adobo.jpg','category':'Prepared Meals'} ],
        'seller4@example.com': [ { 'title':'Iced Lemon Tea','description':'Refreshing iced tea','price':95.00,'stock':30,'img_url':'/uploads/products/picnic-pantry-lemon-tea.jpg','category':'Beverages'} ],
        'seller5@example.com': [ { 'title':'Chocolate Chip Muffin','description':'Warm muffin','price':95.00,'stock':35,'img_url':'/uploads/products/bakers-corner-muffin.jpg','category':'Bakery'} ]
    }

    for email in emails:
        print('\nProcessing', email)
        a = find_auth_user(email)
        if not a:
            print('Auth user not found for', email)
            continue
        auth_uid = a['id']
        # Insert into users table (let DB assign integer id)
        user_payload = {
            'email': a.get('email'),
            'password_hash': 'supabase',
            'first_name': a.get('user_metadata',{}).get('first_name') or '',
            'last_name': a.get('user_metadata',{}).get('last_name') or '',
            'role': 'seller' if email.startswith('seller') else ('rider' if email.startswith('rider') else ('admin' if email.startswith('admin') else 'customer')),
            'is_verified': 1
        }
        user_resp = insert_row('users', user_payload)
        if not user_resp:
            print('Skipping seller/products because user insert failed for', email)
            continue
        # PostgREST returns an array representation
        if isinstance(user_resp, list):
            created_user = user_resp[0]
        else:
            created_user = user_resp
        created_user_id = created_user.get('id')
        print('created user id', created_user_id)
        # If seller, add seller row and products referencing integer id
        if email.startswith('seller'):
            seller_payload = {'user_id': created_user_id, 'business_name': email.split('@')[0], 'verified': 1, 'shop_status': 'active'}
            sresp = insert_row('sellers', seller_payload)
            for p in products_by_seller.get(email, []):
                p_payload = { 'title': p['title'], 'description': p['description'], 'price': p['price'], 'stock': p['stock'], 'seller_id': created_user_id, 'category': p['category'], 'img_url': p['img_url'] }
                insert_row('products', p_payload)

    print('\nUpsert finished')

if __name__=='__main__':
    main()
