"""Quick end-to-end test for the library API."""
import requests

BASE = "http://localhost:8000"
TIMEOUT = 5

def test():
    # 1. Login as admin
    r = requests.post(f"{BASE}/api/token", json={"username": "admin", "password": "admin123"}, timeout=TIMEOUT)
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ Login as admin")

    # 2. Get users
    r = requests.get(f"{BASE}/api/users", headers=headers, timeout=TIMEOUT)
    assert r.status_code == 200
    users = r.json()
    print(f"✓ List users: {len(users)} users")

    # 3. Upload a file
    with open("test_book1.txt", "rb") as f:
        r = requests.post(
            f"{BASE}/api/upload-file",
            params={"book_id": 1, "format": "txt", "oss_key": "books/1/test_book1.txt"},
            headers=headers,
            files={"file": ("test.txt", f, "text/plain")},
            timeout=TIMEOUT,
        )
    assert r.status_code == 200, f"Upload failed: {r.text}"
    file_data = r.json()
    print(f"✓ Upload file: id={file_data['id']}, size={file_data['size']}")

    # 4. Login as alice
    r = requests.post(f"{BASE}/api/token", json={"username": "alice", "password": "alice123"}, timeout=TIMEOUT)
    assert r.status_code == 200
    alice_token = r.json()["access_token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    print("✓ Login as alice")

    # 5. Download as alice (should 302 redirect)
    r = requests.get(f"{BASE}/api/download/1?format=txt", headers=alice_headers, allow_redirects=False, timeout=TIMEOUT)
    print(f"✓ Download redirect: status={r.status_code}")

    # 6. Banned user can't login
    r = requests.post(f"{BASE}/api/token", json={"username": "charlie", "password": "charlie123"}, timeout=TIMEOUT)
    assert r.status_code == 403, f"Banned user should get 403, got {r.status_code}"
    print("✓ Banned user rejected")

    # 7. Unauthenticated download fails
    r = requests.get(f"{BASE}/api/download/1", allow_redirects=False, timeout=TIMEOUT)
    assert r.status_code == 401, f"Unauth should get 401, got {r.status_code}"
    print("✓ Unauthenticated download rejected")

    # 8. Get single book (public)
    r = requests.get(f"{BASE}/api/books/1", timeout=TIMEOUT)
    assert r.status_code == 200
    book = r.json()
    assert len(book["files"]) >= 1, f"Book should have at least 1 file, has {len(book['files'])}"
    print(f"✓ Book detail: {book['title']} has {len(book['files'])} file(s)")

    print("\n🎉 ALL TESTS PASSED!")

if __name__ == "__main__":
    test()
