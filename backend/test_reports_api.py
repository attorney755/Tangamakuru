import requests
import json

BASE_URL = "http://localhost:5000"

print("Testing Reports API")
print("=" * 60)

# 1. Test reports endpoint
print("\n1. Testing /reports/test:")
try:
    r = requests.get(f"{BASE_URL}/reports/test")
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")
except:
    print("   ❌ Endpoint not available")

# 2. Login
print("\n2. Logging in...")
login_data = {"email": "citizen@tangamakuru.rw", "password": "Citizen@2024"}
r = requests.post(f"{BASE_URL}/auth/login", json=login_data)

if r.status_code == 200:
    token = r.json()['token']
    print(f"   ✅ Login successful")
    
    # 3. Get user's reports
    print("\n3. Getting user's reports:")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/reports/my-reports", headers=headers)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ User has {data['count']} reports")
    else:
        print(f"   Response: {r.text}")
else:
    print(f"   ❌ Login failed: {r.json()}")

print("\n" + "=" * 60)