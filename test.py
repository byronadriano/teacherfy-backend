import requests
import json
import os

def test_outline_generation():
    """Test the outline generation endpoint"""
    url = "http://localhost:5000/outline"
    
    # Test payload
    payload = {
        "grade_level": "5th Grade",
        "subject_focus": "Science",
        "lesson_topic": "Solar System",
        "district": "Test District",
        "language": "English",
        "custom_prompt": "",
        "num_slides": 3
    }
    
    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Origin': 'http://localhost:5000'
    }
    
    # Make the request
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print("\n=== Outline Generation Test ===")
        print(f"Status Code: {response.status_code}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error generating outline: {e}")
        if hasattr(e.response, 'text'):
            print(f"Error response: {e.response.text}")
        return None

def test_presentation_generation(outline_data):
    """Test the presentation generation endpoint"""
    url = "http://localhost:5000/generate"
    
    if not outline_data:
        print("No outline data available for presentation generation")
        return
    
    # Prepare payload
    payload = {
        "lesson_outline": outline_data["messages"][0],
        "structured_content": outline_data["structured_content"],
        "language": "English"
    }
    
    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Origin': 'http://localhost:5000'
    }
    
    # Make the request
    try:
        print("\n=== Presentation Generation Test ===")
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Check content type
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        # Save the presentation if received
        if response.headers.get('Content-Type') == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
            with open('test_presentation.pptx', 'wb') as f:
                f.write(response.content)
            print("Presentation saved as 'test_presentation.pptx'")
        else:
            print("Response content:", response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Error generating outline: {e}")
        if hasattr(e.response, 'text'):
            print(f"Error response: {e.response.text}")

def main():
    print("Starting test sequence...")
    
    # First test outline generation
    outline_data = test_outline_generation()
    
    # Then test presentation generation with the outline
    if outline_data:
        test_presentation_generation(outline_data)
    
    print("\nTest sequence completed.")

if __name__ == "__main__":
    main()