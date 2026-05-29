#!/usr/bin/env python3
"""Seed Supabase: create Auth users and insert users/sellers/products rows.

WARNING: This uses the Supabase Service Role key from `.env` and will write
to your Supabase project. Run only when you intend to modify the remote DB.
"""
import os
import sys
import time
import json

try:
    from dotenv import load_dotenv
    import requests
except ImportError:
    print('Please install dependencies first: pip install python-dotenv requests')
    sys.exit(1)

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, '.env'))

SUPA_URL = os.getenv('Supabase_URL') or os.getenv('SUPABASE_URL')
SERVICE_ROLE = os.getenv('Supabase_Service_role_key') or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
if not SUPA_URL or not SERVICE_ROLE:
    print('Missing Supabase URL or service role key in .env')
    sys.exit(1)

HEADERS = {
    'apikey': SERVICE_ROLE,
    'Authorization': f'Bearer {SERVICE_ROLE}',
    'Content-Type': 'application/json'
}


def create_auth_user(email, password):
    url = SUPA_URL.rstrip('/') + '/auth/v1/admin/users'
    body = {'email': email, 'password': password, 'email_confirm': True}
    r = requests.post(url, headers=HEADERS, json=body)
    if r.status_code in (200, 201):
        return r.json()
    else:
        print(f'Auth create failed for {email}:', r.status_code, r.text)
        return None


def insert_row(table, payload):
    url = SUPA_URL.rstrip('/') + f'/rest/v1/{table}'
    h = HEADERS.copy()
    h['Prefer'] = 'return=representation'
    r = requests.post(url, headers=h, json=payload)
    if r.status_code in (200, 201):
        return r.json()
    else:
        print(f'Insert into {table} failed:', r.status_code, r.text)
        return None


def upsert_user_record(auth_user, first, last, role):
    # Insert into users table with id equal to auth user's id (uuid)
    payload = {
        'id': auth_user['id'],
        'email': auth_user['email'],
        'first_name': first,
        'last_name': last,
        'role': role,
        'is_verified': True,
    }
    return insert_row('users', payload)


def main():
    accounts = [
        ('admin@example.com', 'Admin123!', 'Admin', 'User', 'admin'),
        ('buyer@example.com', 'Buyer123!', 'Buyer', 'Customer', 'customer'),
        ('rider@example.com', 'Rider123!', 'Rider', 'Courier', 'rider')
    ]

    sellers = [
        ('seller1@example.com', 'Seller123!', 'Fresh', 'Greens', 'Fresh Greens Market'),
        ('seller2@example.com', 'Seller123!', 'Metro', 'Snacks', 'Metro Snacks Co.'),
        ('seller3@example.com', 'Seller123!', 'Daily', 'Bites', 'Daily Bites Kitchen'),
        ('seller4@example.com', 'Seller123!', 'Picnic', 'Pantry', 'Picnic Pantry'),
        ('seller5@example.com', 'Seller123!', 'Baker', 'Corner', "Baker's Corner")
    ]

    products_by_seller = {
        'seller1@example.com': [
            {'title':'Organic Lettuce Bundle','description':'Crisp organic lettuce','price':120.00,'stock':20,'img_url':'/uploads/products/fresh-greens-lettuce.jpg','category':'Produce'},
            {'title':'Cherry Tomato Pack','description':'Sweet cherry tomatoes','price':80.00,'stock':35,'img_url':'/uploads/products/fresh-greens-tomatoes.jpg','category':'Produce'},
        ],
        'seller2@example.com': [
            {'title':'Crunchy Nacho Chips','description':'Salted nacho chips','price':95.00,'stock':50,'img_url':'/uploads/products/metro-snacks-nachos.jpg','category':'Snacks'},
        ],
        'seller3@example.com': [
            {'title':'Classic Chicken Adobo','description':'Hearty chicken adobo meal','price':220.00,'stock':18,'img_url':'/uploads/products/daily-bites-adobo.jpg','category':'Prepared Meals'},
        ],
        'seller4@example.com': [
            {'title':'Iced Lemon Tea','description':'Refreshing iced tea','price':95.00,'stock':30,'img_url':'/uploads/products/picnic-pantry-lemon-tea.jpg','category':'Beverages'},
        ],
        'seller5@example.com': [
            {'title':'Chocolate Chip Muffin','description':'Warm muffin','price':95.00,'stock':35,'img_url':'/uploads/products/bakers-corner-muffin.jpg','category':'Bakery'},
        ]
    }

    created = {}

    # Create base accounts
    for email, pw, first, last, role in accounts:
        print('Creating', email)
        a = create_auth_user(email, pw)
        if not a:
            print('Skipping', email)
            continue
        time.sleep(0.2)
        inserted = upsert_user_record(a, first, last, role)
        created[email] = {'auth': a, 'row': inserted}
        print(' -> done', email)

    # Sellers
    for email, pw, first, last, business in sellers:
        print('Creating seller', email)
        a = create_auth_user(email, pw)
        if not a:
            print('Skipping seller', email)
            continue
        time.sleep(0.2)
        user_row = upsert_user_record(a, first, last, 'seller')
        # create sellers table row
        seller_payload = {'user_id': a['id'], 'business_name': business, 'verified': True, 'shop_status': 'active'}
        srow = insert_row('sellers', seller_payload)
        created[email] = {'auth': a, 'user': user_row, 'seller': srow}
        # products
        prods = products_by_seller.get(email, [])
        for p in prods:
            p_payload = {
                'title': p['title'], 'description': p['description'], 'price': p['price'], 'stock': p['stock'],
                'seller_id': a['id'], 'category': p.get('category','General'), 'img_url': p.get('img_url'),
            }
            insert_row('products', p_payload)
        print(' -> seller done', email)

    print('\nSeeding complete. Created accounts:')
    for k,v in created.items():
        print(' -', k, 'auth id=', v['auth']['id'])


if __name__ == '__main__':
    main()
