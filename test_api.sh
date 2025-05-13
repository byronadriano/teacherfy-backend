#!/bin/bash
# test_api.sh

SERVER="http://localhost:5000"

echo "Testing outline generation for different resource types..."

# Test presentation outline
echo -e "\n--- Testing presentation outline ---"
curl -X POST "$SERVER/outline" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "presentation",
    "gradeLevel": "4th grade",
    "subjectFocus": "Math",
    "language": "English",
    "lessonTopic": "Addition",
    "numSlides": 3
  }' | jq .resource_type

# Test lesson plan outline
echo -e "\n--- Testing lesson plan outline ---"
curl -X POST "$SERVER/outline" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "lesson_plan",
    "gradeLevel": "4th grade",
    "subjectFocus": "Math",
    "language": "English",
    "lessonTopic": "Addition"
  }' | jq .resource_type

# Test worksheet outline
echo -e "\n--- Testing worksheet outline ---"
curl -X POST "$SERVER/outline" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "worksheet",
    "gradeLevel": "4th grade",
    "subjectFocus": "Math",
    "language": "English",
    "lessonTopic": "Addition"
  }' | jq .resource_type

# Test quiz outline
echo -e "\n--- Testing quiz outline ---"
curl -X POST "$SERVER/outline" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "quiz",
    "gradeLevel": "4th grade",
    "subjectFocus": "Math",
    "language": "English",
    "lessonTopic": "Addition"
  }' | jq .resource_type

echo -e "\nTests completed."