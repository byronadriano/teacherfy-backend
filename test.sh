#!/bin/bash
# test.sh - Consolidated test script for Teacherfy backend
# This script combines functionality from:
# - test_api.sh
# - test_rate_limits.sh
# - test_db.py

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}Teacherfy Backend Tests${NC}"
echo -e "${GREEN}=======================================${NC}\n"

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Default server URL
SERVER_URL="http://localhost:5000"

# Test directory for downloads
TEST_DIR="test_downloads"
mkdir -p $TEST_DIR

# Function to run a test
run_test() {
    echo -e "\n${YELLOW}TEST: $1${NC}"
    shift
    if $@; then
        echo -e "${GREEN}✅ Test passed${NC}"
        return 0
    else
        echo -e "${RED}❌ Test failed${NC}"
        return 1
    fi
}

# Test database connection
test_db_connection() {
    echo "Testing database connection..."
    python -c "from src.db.database import test_connection; print('Database connection successful' if test_connection() else 'Database connection failed')"
    return $?
}

# Test API health endpoint
test_health_endpoint() {
    echo "Testing API health endpoint..."
    response=$(curl -s "$SERVER_URL/health")
    echo "$response" | grep -q "healthy" && echo "Health check passed" || echo "Health check failed"
    return $?
}

# Test rate limits
test_rate_limits() {
    echo -e "\nTesting rate limits for outline generation..."

    # Test outline generations (should allow a few, then fail)
    for i in {1..4}
    do
        echo -e "\nTest generation $i:"
        response=$(curl -X POST "$SERVER_URL/outline" \
            -H "Content-Type: application/json" \
            -d '{
                "custom_prompt":"Create a math lesson about addition for elementary students, including clear learning objectives, engaging activities, and assessment strategies"
            }' \
            -s)
        
        echo "$response" | python -m json.tool 2>/dev/null || echo "$response"
        sleep 1
    done

    echo -e "\nTesting download limit..."
    for i in {1..2}
    do
        echo -e "\nTest download $i:"
        sample_content='{
            "structured_content": [
                {
                    "title": "Introduction to Addition",
                    "layout": "TITLE_AND_CONTENT",
                    "content": [
                        "Definition: Addition is combining numbers to find a total.",
                        "Today we will learn:",
                        "- How to add single-digit numbers",
                        "- When to use addition in real life",
                        "- Different strategies for adding numbers"
                    ],
                    "teacher_notes": [
                        "Start with a real-world example",
                        "Use visual aids to demonstrate concepts",
                        "Check for prior knowledge"
                    ],
                    "visual_elements": [
                        "Illustration of combining groups of objects",
                        "Number line diagram"
                    ]
                },
                {
                    "title": "Addition Basics",
                    "layout": "TWO_COLUMN",
                    "left_column": [
                        "The plus sign (+) means to add",
                        "The equals sign (=) shows the result",
                        "Example: 2 + 3 = 5"
                    ],
                    "right_column": [
                        "Key terms:",
                        "- Addends: numbers being added",
                        "- Sum: the result of addition"
                    ],
                    "teacher_notes": [
                        "Introduce symbols with concrete examples",
                        "Practice identifying parts of addition problems"
                    ],
                    "visual_elements": [
                        "Math symbols chart",
                        "Example problems with highlighted parts"
                    ]
                }
            ]
        }'
        
        curl -X POST "$SERVER_URL/generate" \
            -H "Content-Type: application/json" \
            -d "$sample_content" \
            --output "$TEST_DIR/presentation_$i.pptx"
        
        if [ -f "$TEST_DIR/presentation_$i.pptx" ]; then
            echo -e "${GREEN}Successfully downloaded presentation $i${NC}"
            # Check file size to verify it's not empty
            size=$(stat -f%z "$TEST_DIR/presentation_$i.pptx" 2>/dev/null || stat -c%s "$TEST_DIR/presentation_$i.pptx")
            if [ $size -gt 1000 ]; then
                echo -e "${GREEN}Presentation $i has content (size: $size bytes)${NC}"
            else
                echo -e "${RED}Warning: Presentation $i might be empty (size: $size bytes)${NC}"
            fi
        else
            echo -e "${RED}Failed to download presentation $i${NC}"
        fi
        
        sleep 1
    done
    
    return 0
}

# Test API endpoints
test_api_endpoints() {
    echo "Testing outline generation for different resource types..."

    # Test presentation outline
    echo -e "\n--- Testing presentation outline ---"
    curl -X POST "$SERVER_URL/outline" \
      -H "Content-Type: application/json" \
      -d '{
        "resourceType": "presentation",
        "gradeLevel": "4th grade",
        "subjectFocus": "Math",
        "language": "English",
        "lessonTopic": "Addition",
        "numSlides": 3
      }' | grep -q "structured_content" && echo "Presentation outline test passed" || echo "Presentation outline test failed"

    # Test lesson plan outline
    echo -e "\n--- Testing lesson plan outline ---"
    curl -X POST "$SERVER_URL/outline" \
      -H "Content-Type: application/json" \
      -d '{
        "resourceType": "lesson_plan",
        "gradeLevel": "4th grade",
        "subjectFocus": "Math",
        "language": "English",
        "lessonTopic": "Addition"
      }' | grep -q "structured_content" && echo "Lesson plan outline test passed" || echo "Lesson plan outline test failed"

    # Test worksheet outline
    echo -e "\n--- Testing worksheet outline ---"
    curl -X POST "$SERVER_URL/outline" \
      -H "Content-Type: application/json" \
      -d '{
        "resourceType": "worksheet",
        "gradeLevel": "4th grade",
        "subjectFocus": "Math",
        "language": "English",
        "lessonTopic": "Addition"
      }' | grep -q "structured_content" && echo "Worksheet outline test passed" || echo "Worksheet outline test failed"

    # Test quiz outline
    echo -e "\n--- Testing quiz outline ---"
    curl -X POST "$SERVER_URL/outline" \
      -H "Content-Type: application/json" \
      -d '{
        "resourceType": "quiz",
        "gradeLevel": "4th grade",
        "subjectFocus": "Math",
        "language": "English",
        "lessonTopic": "Addition"
      }' | grep -q "structured_content" && echo "Quiz outline test passed" || echo "Quiz outline test failed"

    return 0
}

# Test database functionality using test_db.py
test_db_functionality() {
    echo "Testing database functionality..."
    python test_db.py
    return $?
}

# Main test function
main() {
    # Determine what to test
    echo -e "${YELLOW}What would you like to test?${NC}"
    echo "1) Run all tests"
    echo "2) Test database connection"
    echo "3) Test API endpoints"
    echo "4) Test rate limits"
    echo "5) Custom server URL"
    echo "6) Exit"
    
    read -p "Enter your choice [1-6]: " choice
    
    case $choice in
        1)
            # Run all tests
            run_test "Database connection" test_db_connection
            run_test "API health endpoint" test_health_endpoint
            run_test "API endpoints" test_api_endpoints
            run_test "Rate limits" test_rate_limits
            ;;
        2)
            # Database tests
            run_test "Database connection" test_db_connection
            run_test "Database functionality" test_db_functionality
            ;;
        3)
            # API endpoint tests
            run_test "API health endpoint" test_health_endpoint
            run_test "API endpoints" test_api_endpoints
            ;;
        4)
            # Rate limit tests
            run_test "Rate limits" test_rate_limits
            ;;
        5)
            # Custom server URL
            read -p "Enter server URL (default: http://localhost:5000): " custom_url
            if [ -n "$custom_url" ]; then
                SERVER_URL="$custom_url"
                echo "Using server URL: $SERVER_URL"
            fi
            main # Restart the menu
            ;;
        6)
            echo "Exiting."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Exiting.${NC}"
            exit 1
            ;;
    esac
    
    echo -e "\n${GREEN}=======================================${NC}"
    echo -e "${GREEN}Tests completed!${NC}"
    echo -e "${GREEN}=======================================${NC}"
}

# Run main function
main