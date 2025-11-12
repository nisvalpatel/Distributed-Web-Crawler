# Testing Guide

This document explains how to test the Distributed Web Crawler.

## Quick Test

The easiest way to test everything:

```bash
./run_tests.sh
```

This runs a comprehensive test suite that validates all crawler functionality.

## What Gets Tested

The test suite verifies:

1. **Health Check** - All services (API, MongoDB, Celery) are running
2. **API Information** - API endpoints are available
3. **Submit Crawl** - Can submit crawl jobs successfully
4. **Task Status** - Tasks complete and return results
5. **Get Results** - Can retrieve crawled data from MongoDB
6. **Get Specific Page** - Can query individual pages
7. **List Domains** - Can list all crawled domains
8. **Statistics** - Can get crawler stats

## Using Makefile

```bash
make test        # Run full test suite
make test-quick  # Just check if API is responding
```

## Manual Testing

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected: `status: healthy`

### 2. Submit a Crawl

```bash
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_depth": 1}'
```

Expected: Returns a `task_id`

### 3. Check Task Status

```bash
curl http://localhost:8000/task/YOUR_TASK_ID_HERE
```

Expected: `status: SUCCESS` after a few seconds

### 4. Get Results

```bash
curl http://localhost:8000/results/example.com
```

Expected: JSON with crawled page data

### 5. View Statistics

```bash
curl http://localhost:8000/stats
```

Expected: Total pages, domains, etc.

## Interactive API Testing

Open your browser to:

```
http://localhost:8000/docs
```

This provides a Swagger UI where you can test all API endpoints interactively.

## Python Test File

For programmatic testing with detailed output:

```bash
python3 tests/test_crawler.py
```

Note: Requires `requests` library. If not installed:
```bash
pip3 install requests --user
```

## Expected Test Output

When all tests pass, you'll see:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Health Check: PASSED
✓ API Information: PASSED
✓ Submit Crawl: PASSED
✓ Task Status & Completion: PASSED
✓ Get Crawl Results: PASSED
✓ Get Specific Page: PASSED
✓ List Domains: PASSED
✓ Statistics: PASSED

Passed: 8
Failed: 0
Total:  8

🎉 All tests passed! Crawler is working perfectly.
```

## Troubleshooting Tests

### Tests fail with "API not responding"

Make sure services are running:
```bash
docker compose up -d
docker compose ps
```

All containers should show "Up" status.

### Tests timeout

Increase the wait time in `run_tests.sh` or restart workers:
```bash
docker compose restart worker
```

### Database conflicts

If you see duplicate key errors, clean the database:
```bash
docker compose down -v
docker compose up --build
```

This removes all data and starts fresh.

## Continuous Testing

During development, you can watch for changes and auto-test:

```bash
# In one terminal - watch logs
make logs-worker

# In another terminal - run tests
make test
```

## Performance Testing

To test with multiple concurrent crawls:

```bash
# Submit 10 crawls simultaneously
for i in {1..10}; do
  curl -X POST http://localhost:8000/crawl \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"https://example.com\", \"max_depth\": 1}" &
done
wait

# Check statistics
curl http://localhost:8000/stats
```

## Test Files

- `run_tests.sh` - Main test script (shell, no dependencies)
- `tests/test_crawler.py` - Python version with detailed output (requires `requests`)
- `test_crawler.sh` - Original simple test script

All three test the same functionality - pick whichever you prefer.

