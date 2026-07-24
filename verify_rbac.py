import requests; BASE='http://localhost:8000'
r=requests.post(f'{BASE}/api/token',json={'username':'admin','password':'admin123'},timeout=5);t=r.json()['access_token'];H={'Authorization':f'Bearer {t}'}
r=requests.get(f'{BASE}/api/me/permissions',headers=H,timeout=5);d=r.json()
assert'book.create'in d['permissions'];assert'system.config'in d['permissions'];print(f"Admin: {len(d['permissions'])} perms, roles={[r['name'] for r in d['roles']]}")
r=requests.post(f'{BASE}/api/token',json={'username':'alice','password':'alice123'},timeout=5);t2=r.json()['access_token'];H2={'Authorization':f'Bearer {t2}'}
r=requests.get(f'{BASE}/api/me/permissions',headers=H2,timeout=5);d2=r.json()
assert'book.create'not in d2['permissions'];print(f"Alice: {len(d2['permissions'])} perms, roles={[r['name'] for r in d2['roles']]}")
r=requests.post(f'{BASE}/api/books',json={'title':'unauthorized test'},headers=H2,timeout=5)
assert r.status_code==403;print("Alice create book → 403 ✓")
r=requests.post(f'{BASE}/api/books',json={'title':'admin test'},headers=H,timeout=5)
assert r.status_code==201;print("Admin create book → 201 ✓")
r=requests.get(f'{BASE}/api/roles',headers=H,timeout=5);print(f"Roles: {[r['name'] for r in r.json()]}")
r=requests.get(f'{BASE}/admin/roles',headers=H,timeout=5);assert'权限管理'in r.text;print("Admin roles page loads ✓")
print("ALL RBAC TESTS PASSED")
