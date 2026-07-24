"""Final verification — all new endpoints."""
import requests, sys
BASE = "http://localhost:8000"

def check(name, r, expected=200):
    ok = r.status_code == expected
    print(f"  {'✓' if ok else '✗'} {name}: {r.status_code} {'OK' if ok else r.text[:80]}")
    if not ok: return False
    return True

# Login
r = requests.post(f"{BASE}/api/token", json={"username":"admin","password":"admin123"}, timeout=5)
assert r.status_code == 200
token = r.json()["access_token"]
H = {"Authorization": f"Bearer {token}"}
print("✓ Login as admin")

# Admin pages
check("GET /admin", requests.get(f"{BASE}/admin/", headers=H, timeout=5))
check("GET /admin/books", requests.get(f"{BASE}/admin/books", headers=H, timeout=5))
check("GET /admin/users", requests.get(f"{BASE}/admin/users", headers=H, timeout=5))
check("GET /admin/catalog", requests.get(f"{BASE}/admin/catalog", headers=H, timeout=5))
check("GET /admin/stats", requests.get(f"{BASE}/admin/stats", headers=H, timeout=5))

# Auth guards
check("GET /admin (no auth)", requests.get(f"{BASE}/admin/", timeout=5), 401)

# User-facing login page
check("GET /login", requests.get(f"{BASE}/login", timeout=5))

# Stats API
r = requests.get(f"{BASE}/api/stats/summary", timeout=5)
check("GET /api/stats/summary", r)
assert "total_downloads" in r.json()

# Rebuild
r = requests.post(f"{BASE}/admin/rebuild", headers=H, timeout=30)
check("POST /admin/rebuild", r)

# Download flow
r = requests.get(f"{BASE}/api/download/1?format=txt", headers=H, allow_redirects=False, timeout=5)
check("GET /api/download/1", r, 302)

# Existing endpoints still work
r = requests.get(f"{BASE}/api/books?status=published", timeout=5)
check("GET /api/books", r)
assert len(r.json()) == 7

print("\n🎉 ALL CHECKS PASSED")
