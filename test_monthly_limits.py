# test_monthly_limits.py - Updated to avoid expensive OpenAI calls
import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:5000"  # Change to your API URL
TEST_IP = "192.168.1.100"  # Test IP address

def make_outline_request(request_type="test", ip_override=None):
    """
    Make an outline generation request
    request_type: "example", "test", or "real"
    """
    
    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Override IP if specified
    if ip_override:
        headers['X-Forwarded-For'] = ip_override
    
    # Request data based on type
    if request_type == "example":
        # Example request (should not count against limits, no OpenAI call)
        data = {
            "resourceType": "Presentation",
            "gradeLevel": "4th grade",
            "subjectFocus": "Math", 
            "lessonTopic": "Equivalent Fractions",
            "language": "English",
            "numSlides": 5,
            "use_example": True  # Explicit example flag
        }
    elif request_type == "test":
        # Test request (counts against limits but no OpenAI call)
        data = {
            "resourceType": "Presentation",
            "gradeLevel": "5th grade",
            "subjectFocus": "Science",
            "lessonTopic": f"Test Topic {int(time.time())}",  # Unique topic
            "language": "English",
            "numSlides": 3,
            "customPrompt": "This is a test request for limit testing",  # This triggers test mode
            "test_limits": True  # Explicit test flag
        }
    else:  # real
        # Real request (counts against limits AND makes OpenAI call)
        data = {
            "resourceType": "Presentation",
            "gradeLevel": "6th grade",
            "subjectFocus": "History",
            "lessonTopic": f"Real Topic {int(time.time())}",
            "language": "English",
            "numSlides": 2,
            "customPrompt": "Create a real lesson plan"  # Real request
        }
    
    try:
        response = requests.post(
            f"{BASE_URL}/outline",
            headers=headers,
            json=data,
            timeout=30
        )
        
        return {
            'status_code': response.status_code,
            'data': response.json(),
            'headers': dict(response.headers),
            'request_type': request_type
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'status_code': 0,
            'error': str(e),
            'data': None,
            'request_type': request_type
        }

def test_monthly_limits():
    """Test the monthly limits system without expensive API calls"""
    
    print("🧪 Testing Monthly Limits System (No OpenAI API Calls)")
    print("=" * 60)
    
    # Test 1: Example request (should not count)
    print("\n1️⃣ Testing Example Request (should NOT count against limits)")
    result = make_outline_request(request_type="example")
    
    if result['status_code'] == 200:
        print("✅ Example request successful")
        title = result['data'].get('title', 'No title')
        print(f"   Title: {title}")
        usage = result['data'].get('usage_limits', {})
        if usage:
            print(f"   Generations left: {usage.get('generations_left', 'N/A')}")
        else:
            print("   No usage limits in response (expected for example)")
    else:
        print(f"❌ Example request failed: {result['status_code']}")
        if result.get('data'):
            print(f"   Error: {result['data'].get('error', 'Unknown error')}")
    
    time.sleep(1)
    
    # Test 2: Test requests (should count against limits but no OpenAI cost)
    print(f"\n2️⃣ Testing Limit Enforcement (NO OpenAI API calls)")
    print("Making 6 test requests to verify the 5-request limit...")
    
    for i in range(6):
        print(f"\n   Test Request {i+1}/6:")
        result = make_outline_request(request_type="test", ip_override=TEST_IP)
        
        if result['status_code'] == 200:
            print(f"   ✅ Request {i+1} successful (no OpenAI cost)")
            title = result['data'].get('title', 'No title')
            print(f"      Title: {title}")
            usage = result['data'].get('usage_limits', {})
            if usage:
                print(f"      Generations left: {usage.get('generations_left', 'N/A')}")
                print(f"      Current usage: {usage.get('current_usage', {})}")
        elif result['status_code'] == 403:
            print(f"   🚫 Request {i+1} blocked - LIMIT REACHED!")
            error_data = result.get('data', {})
            print(f"      Error: {error_data.get('error', 'Limit reached')}")
            print(f"      Generations used: {error_data.get('generations_used', 'N/A')}")
            print(f"      Reset time: {error_data.get('reset_time', 'N/A')}")
            break
        else:
            print(f"   ❌ Request {i+1} failed with status: {result['status_code']}")
            if result.get('data'):
                print(f"      Error: {result['data'].get('error', 'Unknown error')}")
        
        time.sleep(0.5)  # Small delay between requests
    
    # Test 3: Another example request after limit reached
    print(f"\n3️⃣ Testing Example Request After Limit Reached")
    result = make_outline_request(request_type="example")
    
    if result['status_code'] == 200:
        print("✅ Example request still works after limit reached")
        print("   (Examples never count against limits)")
    else:
        print(f"❌ Example request failed: {result['status_code']}")
    
    # Test 4: Different IP (should have fresh limits)
    print(f"\n4️⃣ Testing Different IP Address (should have fresh limits)")
    different_ip = "192.168.1.200"
    result = make_outline_request(request_type="test", ip_override=different_ip)
    
    if result['status_code'] == 200:
        print("✅ Different IP can make requests (has fresh limits)")
        usage = result['data'].get('usage_limits', {})
        if usage:
            print(f"   Generations left: {usage.get('generations_left', 'N/A')}")
    else:
        print(f"❌ Different IP request failed: {result['status_code']}")

def offer_real_api_test():
    """Offer to test with real API calls (costs money)"""
    print(f"\n5️⃣ Real OpenAI API Test (Optional - Costs Money)")
    print("⚠️  This will make an actual OpenAI API call and cost money!")
    
    response = input("Do you want to test with a real API call? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        print("Making real OpenAI API call...")
        result = make_outline_request(request_type="real")
        
        if result['status_code'] == 200:
            print("✅ Real API call successful")
            title = result['data'].get('title', 'No title')
            print(f"   Title: {title}")
            usage = result['data'].get('usage_limits', {})
            if usage:
                print(f"   Generations left after real call: {usage.get('generations_left', 'N/A')}")
        else:
            print(f"❌ Real API call failed: {result['status_code']}")
    else:
        print("Skipped real API test (good choice to save money!)")

def check_database_usage():
    """Check the database for current usage"""
    print(f"\n6️⃣ Database Usage Check")
    print("To check database directly, run this SQL query:")
    print(f"""
    SELECT 
        COALESCE(user_id::text, 'Anonymous') as user_type,
        ip_address,
        generations_used,
        downloads_used,
        last_reset,
        CASE 
            WHEN EXTRACT(MONTH FROM last_reset) = EXTRACT(MONTH FROM CURRENT_TIMESTAMP)
              AND EXTRACT(YEAR FROM last_reset) = EXTRACT(YEAR FROM CURRENT_TIMESTAMP)
              THEN 'Current Month'
            ELSE 'Old Month (should reset)'
        END as reset_status
    FROM user_usage_limits 
    WHERE ip_address IN ('{TEST_IP}', '192.168.1.200')
    ORDER BY last_reset DESC;
    """)

def main():
    """Main test function"""
    print("🚀 Starting Monthly Limits Test (Cost-Effective Version)")
    print(f"Testing against: {BASE_URL}")
    print(f"Test IP: {TEST_IP}")
    print("💰 This version avoids expensive OpenAI API calls for testing!")
    
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"⚠️  Server health check failed: {response.status_code}")
        else:
            print("✅ Server is running")
    except:
        print("❌ Cannot connect to server. Make sure it's running!")
        sys.exit(1)
    
    # Run the tests
    test_monthly_limits()
    offer_real_api_test()
    check_database_usage()
    
    print("\n" + "=" * 60)
    print("🏁 Test Complete!")
    print("\n💡 What to check:")
    print("   ✅ Example requests should never count against limits")
    print("   ✅ Test requests should count but not call OpenAI API")
    print("   ✅ Regular requests should be blocked after 5 attempts")
    print("   ✅ Different IPs should have separate limits")
    print("   💰 Only real requests should cost money (OpenAI API calls)")

if __name__ == "__main__":
    main()