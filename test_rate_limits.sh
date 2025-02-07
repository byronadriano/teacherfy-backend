#!/bin/bash

# Base URL
BASE_URL="http://localhost:5000"

# Test directory for downloads
TEST_DIR="test_downloads"
mkdir -p $TEST_DIR

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Testing rate limits for outline generation...${NC}"

# Test 4 outline generations (3 should work, 1 should fail)
for i in {1..4}
do
    echo -e "\n${GREEN}Test generation $i:${NC}"
    response=$(curl -X POST "$BASE_URL/outline" \
        -H "Content-Type: application/json" \
        -d '{
            "custom_prompt":"Create a math lesson about addition for elementary students, including clear learning objectives, engaging activities, and assessment strategies"
        }' \
        -s)
    
    echo $response | python3 -m json.tool
    sleep 1
done

echo -e "\n${GREEN}Testing download limit...${NC}"
for i in {1..2}
do
    echo -e "\n${GREEN}Test download $i:${NC}"
    SAMPLE_CONTENT='{
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
    
    curl -X POST "$BASE_URL/generate" \
        -H "Content-Type: application/json" \
        -d "$SAMPLE_CONTENT" \
        --output "$TEST_DIR/presentation_$i.pptx"
    
    if [ -f "$TEST_DIR/presentation_$i.pptx" ]; then
        echo -e "${GREEN}Successfully downloaded presentation $i${NC}"
        # Check file size to verify it's not empty
        size=$(stat -f%z "$TEST_DIR/presentation_$i.pptx")
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