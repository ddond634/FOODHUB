"""Ensure Supabase storage bucket exists using the Storage REST API.

Usage:
  python -m scripts.ensure_supabase_storage --bucket hub_uploads
"""
from dotenv import load_dotenv
import os
import argparse

load_dotenv('.env')

try:
    import requests
except Exception:
    requests = None


def ensure_bucket(bucket_name):
    url = os.getenv('Supabase_URL')
    key = os.getenv('Supabase_Service_role_key')
    if not url or not key:
        raise RuntimeError('Supabase_URL and Supabase_Service_role_key must be set in .env')

    api = url.rstrip('/') + '/storage/v1/bucket'
    headers = {'Authorization': f'Bearer {key}', 'apikey': key, 'Content-Type': 'application/json'}

    # Check existing buckets
    resp = requests.get(url.rstrip('/') + '/storage/v1/buckets', headers=headers)
    if resp.status_code == 200:
        buckets = [b.get('name') for b in resp.json()]
        if bucket_name in buckets:
            print('Bucket already exists:', bucket_name)
            return 0

    # Create bucket
    resp = requests.post(api, headers=headers, json={'name': bucket_name, 'public': False})
    if resp.status_code in (200, 201):
        print('Created bucket:', bucket_name)
        return 0
    else:
        print('Failed to create bucket:', resp.status_code, resp.text)
        return 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', required=True)
    args = parser.parse_args()

    if requests is None:
        print('requests is not installed')
        return 3

    return ensure_bucket(args.bucket)


if __name__ == '__main__':
    raise SystemExit(main())
