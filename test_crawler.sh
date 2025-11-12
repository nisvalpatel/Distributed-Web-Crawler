#!/bin/bash
# Test script for the distributed web crawler

set -e

API_URL="http://localhost:8000"

echo "==================================="
echo "Testing Distributed Web Crawler"
echo "==================================="
echo ""

# Check if API is running
echo "1. Checking API health..."
if curl -s "$API_URL/health" > /dev/null; then
    echo "   ✓ API is healthy"
else
    echo "   ✗ API is not responding"
    exit 1
fi
echo ""

# Submit a test crawl
echo "2. Submitting test crawl for example.com..."
RESPONSE=$(curl -s -X POST "$API_URL/crawl" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://example.com", "max_depth": 1}')

TASK_ID=$(echo $RESPONSE | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TASK_ID" ]; then
    echo "   ✓ Task submitted: $TASK_ID"
else
    echo "   ✗ Failed to submit task"
    echo "   Response: $RESPONSE"
    exit 1
fi
echo ""

# Wait for task to complete
echo "3. Waiting for task to complete (max 30 seconds)..."
for i in {1..30}; do
    STATUS=$(curl -s "$API_URL/task/$TASK_ID" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$STATUS" = "SUCCESS" ]; then
        echo "   ✓ Task completed successfully"
        break
    elif [ "$STATUS" = "FAILURE" ]; then
        echo "   ✗ Task failed"
        curl -s "$API_URL/task/$TASK_ID"
        exit 1
    else
        echo "   ⏳ Status: $STATUS (attempt $i/30)"
        sleep 1
    fi
done
echo ""

# Check results
echo "4. Fetching crawl results..."
RESULTS=$(curl -s "$API_URL/results/example.com")
PAGE_COUNT=$(echo $RESULTS | grep -o '"count":[0-9]*' | cut -d':' -f2)

if [ -n "$PAGE_COUNT" ] && [ "$PAGE_COUNT" -gt 0 ]; then
    echo "   ✓ Found $PAGE_COUNT page(s) for example.com"
else
    echo "   ✗ No results found"
    exit 1
fi
echo ""

# Check statistics
echo "5. Fetching statistics..."
STATS=$(curl -s "$API_URL/stats")
TOTAL_PAGES=$(echo $STATS | grep -o '"total_pages":[0-9]*' | cut -d':' -f2)
TOTAL_DOMAINS=$(echo $STATS | grep -o '"total_domains":[0-9]*' | cut -d':' -f2)

if [ -n "$TOTAL_PAGES" ]; then
    echo "   ✓ Total pages crawled: $TOTAL_PAGES"
    echo "   ✓ Total domains: $TOTAL_DOMAINS"
else
    echo "   ✗ Failed to fetch statistics"
fi
echo ""

echo "==================================="
echo "✓ All tests passed!"
echo "==================================="
echo ""
echo "Try these commands:"
echo "  - View all domains:    curl $API_URL/domains"
echo "  - View page details:   curl '$API_URL/page?url=https://example.com'"
echo "  - Check health:        curl $API_URL/health"
echo "  - API documentation:   Open http://localhost:8000/docs in your browser"

