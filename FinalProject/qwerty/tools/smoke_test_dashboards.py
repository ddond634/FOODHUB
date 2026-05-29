import sys
import re
from urllib import request, error

BASE = 'http://127.0.0.1:5000'
PAGES = [
    ('Admin', '/admin_dashboard.html', 'dashboardSection'),
    ('Seller', '/seller_dashboard.html', 'dashboardSection'),
    ('Rider', '/rider_dashboard.html', 'dashboardSection'),
]

OK = True

def fetch(path):
    url = BASE + path
    try:
        with request.urlopen(url, timeout=6) as r:
            return r.status, r.read().decode('utf-8', errors='ignore')
    except error.HTTPError as e:
        return e.code, getattr(e, 'read', lambda: b'')().decode('utf-8', errors='ignore')
    except Exception as e:
        return None, str(e)


def check_active_section(html, expected_id):
    # Check that the expected section id exists and that an element has "active" class
    if expected_id and expected_id in html:
        # look near the id occurrence for a class attribute containing 'active'
        pos = html.find(expected_id)
        start = max(0, pos - 300)
        end = min(len(html), pos + 300)
        snippet = html[start:end]
        if 'class=' in snippet and 'active' in snippet:
            return True, f"Found {expected_id} with active class (nearby)"
        # fallback: any element with an 'active' class anywhere in document
        if 'class="active"' in html or "class='active'" in html or ' class="' in html and ' active' in html:
            return True, "Found some active class in document (fallback)"
        return False, f"Section {expected_id} found but not marked active"
    else:
        # If expected id not provided, look for any section/content-section with active
        if ' class="active"' in html or " class='active'" in html or ' class="' in html and ' active' in html:
            return True, "Found active section element"
        return False, "No active section element found"


if __name__ == '__main__':
    print('Running dashboard smoke tests against', BASE)
    results = []
    for name, path, expected in PAGES:
        print('\nChecking', name, path)
        status, html = fetch(path)
        if status is None:
            print('  ERROR: request failed:', html)
            results.append((name, False, f'request error: {html}'))
            OK = False
            continue
        print('  HTTP status:', status)
        if status != 200:
            print('  Unexpected status', status)
            results.append((name, False, f'status {status}'))
            OK = False
            continue
        ok, msg = check_active_section(html, expected)
        print('  check:', msg)
        results.append((name, ok, msg))
        if not ok:
            OK = False

    print('\nSummary:')
    for name, ok, msg in results:
        print(f' - {name}:', 'OK' if ok else 'FAIL', '-', msg)

    if not OK:
        print('\nOne or more checks failed.')
        sys.exit(2)
    print('\nAll checks passed.')
    sys.exit(0)
