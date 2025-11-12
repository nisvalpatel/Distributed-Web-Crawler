#!/bin/bash
# Test runner for the Distributed Web Crawler
# This script can be run from the host machine

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

API_URL="http://localhost:8000"

echo -e "\n${BOLD}${BLUE}🕷️  Distributed Web Crawler - Integration Tests${NC}"
echo -e "${BOLD}Testing API at: ${API_URL}${NC}\n"

# Check if services are running
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Checking if services are running...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

if ! docker ps | grep -q crawler-api; then
    echo -e "${RED}✗ Services are not running${NC}"
    echo -e "${YELLOW}Start services with: docker compose up -d${NC}\n"
    exit 1
fi

echo -e "${GREEN}✓ Docker containers are running${NC}\n"

# Test counter
PASSED=0
FAILED=0
TOTAL=0

# Helper function for tests
run_test() {
    local test_name="$1"
    local test_command="$2"
    TOTAL=$((TOTAL + 1))
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Test $TOTAL: ${test_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    if eval "$test_command"; then
        echo -e "\n${GREEN}✓ ${test_name}: PASSED${NC}\n"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "\n${RED}✗ ${test_name}: FAILED${NC}\n"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Test 1: Health Check
test_health() {
    echo "Checking API health..."
    HEALTH=$(curl -s "$API_URL/health")
    STATUS=$(echo "$HEALTH" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "error")
    
    if [ "$STATUS" = "healthy" ]; then
        echo "$HEALTH" | python3 -m json.tool
        return 0
    else
        echo "Health check failed: $HEALTH"
        return 1
    fi
}

# Test 2: API Info
test_api_info() {
    echo "Getting API information..."
    INFO=$(curl -s "$API_URL/")
    NAME=$(echo "$INFO" | python3 -c "import sys, json; print(json.load(sys.stdin).get('name', 'unknown'))" 2>/dev/null || echo "error")
    
    if [ "$NAME" != "error" ] && [ "$NAME" != "unknown" ]; then
        echo "$INFO" | python3 -m json.tool | head -15
        return 0
    else
        return 1
    fi
}

# Test 3: Submit Crawl
test_submit_crawl() {
    echo "Submitting crawl for https://example.com..."
    RESPONSE=$(curl -s -X POST "$API_URL/crawl" \
        -H "Content-Type: application/json" \
        -d '{"url": "https://example.com", "max_depth": 1}')
    
    TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('task_id', ''))" 2>/dev/null)
    
    if [ -n "$TASK_ID" ]; then
        echo "$RESPONSE" | python3 -m json.tool
        echo "$TASK_ID" > /tmp/crawler_task_id.txt
        return 0
    else
        echo "Failed to submit crawl: $RESPONSE"
        return 1
    fi
}

# Test 4: Check Task Status
test_task_status() {
    if [ ! -f /tmp/crawler_task_id.txt ]; then
        echo "No task ID found, skipping..."
        return 1
    fi
    
    TASK_ID=$(cat /tmp/crawler_task_id.txt)
    echo "Checking task status: $TASK_ID"
    echo "Waiting for task to complete (max 30 seconds)..."
    
    for i in {1..30}; do
        STATUS_RESPONSE=$(curl -s "$API_URL/task/$TASK_ID")
        STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)
        
        if [ "$STATUS" = "SUCCESS" ]; then
            echo ""
            echo "Task completed successfully!"
            echo "$STATUS_RESPONSE" | python3 -m json.tool
            return 0
        elif [ "$STATUS" = "FAILURE" ]; then
            echo ""
            echo "Task failed: $STATUS_RESPONSE"
            return 1
        else
            echo -ne "  Attempt $i/30 - Status: $STATUS\r"
            sleep 1
        fi
    done
    
    echo ""
    echo "Task did not complete within 30 seconds"
    return 1
}

# Test 5: Get Results
test_get_results() {
    echo "Getting crawl results for example.com..."
    RESULTS=$(curl -s "$API_URL/results/example.com?limit=5")
    COUNT=$(echo "$RESULTS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null || echo "0")
    
    if [ "$COUNT" -gt 0 ]; then
        echo "$RESULTS" | python3 -m json.tool
        return 0
    else
        echo "No results found"
        return 1
    fi
}

# Test 6: Get Specific Page
test_get_page() {
    echo "Getting page details for https://example.com..."
    PAGE=$(curl -s "$API_URL/page?url=https://example.com/")
    TITLE=$(echo "$PAGE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('title', ''))" 2>/dev/null)
    
    if [ -n "$TITLE" ]; then
        echo "$PAGE" | python3 -m json.tool | head -20
        return 0
    else
        echo "Page not found"
        return 1
    fi
}

# Test 7: List Domains
test_list_domains() {
    echo "Listing all crawled domains..."
    DOMAINS=$(curl -s "$API_URL/domains")
    COUNT=$(echo "$DOMAINS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null || echo "0")
    
    if [ "$COUNT" -ge 0 ]; then
        echo "$DOMAINS" | python3 -m json.tool
        return 0
    else
        return 1
    fi
}

# Test 8: Get Statistics
test_statistics() {
    echo "Getting crawler statistics..."
    STATS=$(curl -s "$API_URL/stats")
    TOTAL_PAGES=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin)['statistics'].get('total_pages', -1))" 2>/dev/null || echo "-1")
    
    if [ "$TOTAL_PAGES" -ge 0 ]; then
        echo "$STATS" | python3 -m json.tool
        return 0
    else
        return 1
    fi
}

# Run all tests
run_test "Health Check" "test_health"
run_test "API Information" "test_api_info"
run_test "Submit Crawl" "test_submit_crawl"
run_test "Task Status & Completion" "test_task_status"
run_test "Get Crawl Results" "test_get_results"
run_test "Get Specific Page" "test_get_page"
run_test "List Domains" "test_list_domains"
run_test "Statistics" "test_statistics"

# Print Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}Test Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${BOLD}Total:  $TOTAL${NC}\n"

# Cleanup
rm -f /tmp/crawler_task_id.txt

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}${BOLD}🎉 All tests passed! Crawler is working perfectly.${NC}\n"
    exit 0
else
    echo -e "${RED}${BOLD}⚠️  Some tests failed. Check the output above.${NC}\n"
    exit 1
fi

