import requests
import json

BASE_URL = "http://localhost:5000"

print("Testing Reports API with JWT")
print("=" * 60)

# 1. Test reports endpoint
print("\n1. Testing /reports/test:")
r = requests.get(f"{BASE_URL}/reports/test")
print(f"   Status: {r.status_code}")
print(f"   Response: {r.json()}")

# 2. Login as citizen
print("\n2. Logging in as citizen...")
login_data = {"email": "citizen@tangamakuru.rw", "password": "Citizen@2024"}
r = requests.post(f"{BASE_URL}/auth/login", json=login_data)

if r.status_code == 200:
    token = r.json()['token']
    print(f"   ✅ Login successful")
    print(f"   Token: {token[:50]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Get user's reports
    print("\n3. Getting user's reports (/reports/my-reports):")
    r = requests.get(f"{BASE_URL}/reports/my-reports", headers=headers)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Success! User has {data['count']} reports")
        for report in data['reports']:
            print(f"     - {report['report_id']}: {report['title']}")
    else:
        print(f"   Response: {r.text}")
    
    # 4. Get specific report
    print("\n4. Getting specific report (/reports/1):")
    r = requests.get(f"{BASE_URL}/reports/1", headers=headers)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ Report details:")
        print(f"     ID: {data['report_id']}")
        print(f"     Title: {data['title']}")
        print(f"     Status: {data['status']}")
        print(f"     Location: {data['location']['district']}, {data['location']['sector']}")
    else:
        print(f"   Response: {r.text}")
        
else:
    print(f"   ❌ Login failed: {r.json()}")

print("\n" + "=" * 60)