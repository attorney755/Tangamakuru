import requests
import json

BASE_URL = "http://localhost:5000"

print("Testing TANGAMAKURU Authentication API - FIXED VERSION")
print("=" * 60)

def test_endpoint(url, method="GET", data=None, headers=None, expect_json=True):
    """Test an API endpoint"""
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            if headers is None:
                headers = {'Content-Type': 'application/json'}
            elif 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'
                
            response = requests.post(url, json=data, headers=headers)
        
        print(f"URL: {url}")
        print(f"Status: {response.status_code}")
        
        if expect_json:
            try:
                print(f"Response: {response.json()}")
            except json.JSONDecodeError:
                print(f"Response (non-JSON): {response.text[:100]}...")
        else:
            print(f"Response: {response.text[:100]}...")
            
        print("-" * 40)
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None

# 1. Test home page (now should return JSON)
print("\n1. Testing home page (should be JSON):")
test_endpoint(f"{BASE_URL}/")

# 2. Test auth test endpoint
print("\n2. Testing auth test endpoint:")
test_endpoint(f"{BASE_URL}/auth/test")

# 3. Test login with wrong credentials
print("\n3. Testing login with wrong credentials:")
test_endpoint(
    f"{BASE_URL}/auth/login",
    method="POST",
    data={"email": "wrong@email.com", "password": "wrong"}
)

# 4. Test login with admin credentials
print("\n4. Testing login with admin credentials:")
response = test_endpoint(
    f"{BASE_URL}/auth/login",
    method="POST", 
    data={"email": "admin@tangamakuru.rw", "password": "Admin@2024"}
)

token = None
if response and response.status_code == 200:
    data = response.json()
    token = data.get('token')
    print(f"   ✅ Token received: {token[:50]}...")

# 5. Test new JWT-protected profile endpoint
if token:
    print("\n5. Testing /auth/profile with JWT token:")
    headers = {'Authorization': f'Bearer {token}'}
    test_endpoint(f"{BASE_URL}/auth/profile", method="GET", headers=headers)

# 6. Test without token (should fail)
print("\n6. Testing /auth/profile without token (should fail):")
test_endpoint(f"{BASE_URL}/auth/profile", method="GET")

# 7. Test registration
print("\n7. Testing user registration:")
test_endpoint(
    f"{BASE_URL}/auth/register",
    method="POST",
    data={
        "email": "newcitizen@tangamakuru.rw",
        "password": "Citizen123!",
        "first_name": "New",
        "last_name": "Citizen",
        "phone": "0785555555",
        "province": "Kigali City",
        "district": "Kicukiro",
        "sector": "Gikondo"
    }
)

print("\n" + "=" * 60)
print("Testing Complete!")
print("\nSummary of endpoints:")
print("  GET  /              - API status (JSON)")
print("  GET  /auth/test     - Auth test")
print("  POST /auth/login    - Login (returns JWT)")
print("  GET  /auth/profile  - Get user profile (requires JWT)")
print("  POST /auth/register - Register new user")
print("=" * 60)