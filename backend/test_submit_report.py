import requests
import json

BASE_URL = "http://localhost:5000"

print("Testing Report Submission")
print("=" * 60)

# 1. Login
print("\n1. Logging in...")
login_data = {"email": "citizen@tangamakuru.rw", "password": "Citizen@2024"}
r = requests.post(f"{BASE_URL}/auth/login", json=login_data)

if r.status_code != 200:
    print(f"   ❌ Login failed: {r.json()}")
    exit()

token = r.json()['token']
headers = {"Authorization": f"Bearer {token}"}
print(f"   ✅ Login successful")

# 2. Submit a report
print("\n2. Submitting new report...")
report_data = {
    "title": "Vandalism in the neighborhood",
    "description": "Public property was damaged last night",
    "category": "vandalism",
    "province": "Kigali City",
    "district": "Gasabo",
    "sector": "Kimihurura",
    "cell": "Kiyovu",
    "village": "Cyurusambu",
    "specific_location": "Near primary school",
    "priority": "medium",
    "is_anonymous": "false",
    "witness_info": "Security guard saw it happen",
    "evidence_details": "Broken fence pieces"
}

r = requests.post(
    f"{BASE_URL}/reports/submit",
    data=report_data,
    headers=headers
)

print(f"   Status: {r.status_code}")
if r.status_code == 201:
    data = r.json()
    print(f"   ✅ Report submitted successfully!")
    print(f"   Report ID: {data['report']['report_id']}")
    print(f"   Title: {data['report']['title']}")
    print(f"   Status: {data['report']['status']}")
else:
    print(f"   ❌ Error: {r.text}")

print("\n" + "=" * 60)