# 🚀 Quick Start Guide

Get your distributed web crawler running in under 5 minutes!

## Step 1: Start the Services

```bash
docker compose up --build
```

Wait for all services to start (about 30-60 seconds). You should see:
- ✅ Redis running on port 6379
- ✅ MongoDB running on port 27017  
- ✅ FastAPI API on port 8000
- ✅ 2 Celery workers ready

## Step 2: Test the API

Open your browser to: **http://localhost:8000/docs**

You'll see the interactive API documentation (Swagger UI).

## Step 3: Submit Your First Crawl

### Option A: Using the Web UI (Easiest)

1. Go to http://localhost:8000/docs
2. Find the `POST /crawl` endpoint
3. Click "Try it out"
4. Enter:
   ```json
   {
     "url": "https://example.com",
     "max_depth": 1
   }
   ```
5. Click "Execute"
6. Copy the `task_id` from the response

### Option B: Using curl

```bash
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_depth": 1}'
```

You'll get a response like:
```json
{
  "task_id": "abc123-def456-...",
  "status": "queued",
  "message": "Crawl task submitted for https://example.com"
}
```

## Step 4: Check Task Status

Replace `TASK_ID` with your actual task ID:

```bash
curl http://localhost:8000/task/TASK_ID
```

Wait until `"status": "SUCCESS"`, then proceed!

## Step 5: View Results

```bash
curl http://localhost:8000/results/example.com
```

You'll see the crawled page data including:
- URL, title, and content
- Links found on the page
- Timestamp of when it was crawled

## 🎉 That's It!

Your crawler is now running. Here are some next steps:

### Crawl a Real Website

```bash
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://python.org",
    "max_depth": 2
  }'
```

### Crawl an Entire Domain

```bash
curl -X POST http://localhost:8000/crawl/domain \
  -H "Content-Type: application/json" \
  -d '{
    "domain_url": "https://example.com",
    "max_depth": 2,
    "max_pages": 50
  }'
```

### View Statistics

```bash
curl http://localhost:8000/stats
```

### List All Crawled Domains

```bash
curl http://localhost:8000/domains
```

## 🛠️ Useful Commands

Using the included Makefile:

```bash
make up          # Start all services
make down        # Stop all services
make logs        # View all logs
make logs-api    # View API logs only
make logs-worker # View worker logs only
make test        # Run a test crawl
make health      # Check service health
make stats       # View statistics
make clean       # Stop and remove all data
```

Or run the test script:

```bash
./test_crawler.sh
```

## 📊 Monitoring

### View Worker Activity

```bash
docker compose logs -f worker
```

You'll see real-time logs of pages being crawled.

### View API Requests

```bash
docker compose logs -f api
```

### Monitor Resource Usage

```bash
docker stats
```

## 🔧 Common Issues

### Port Already in Use

If port 8000, 6379, or 27017 is already in use:

```bash
# Stop all services
docker compose down

# Find what's using the port
lsof -i :8000

# Kill the process or change ports in docker-compose.yml
```

### Services Not Starting

```bash
# Rebuild from scratch
docker compose down -v
docker compose up --build
```

### No Results Found

Make sure to wait for the task to complete before querying results:

1. Submit crawl and get `task_id`
2. Check status: `curl http://localhost:8000/task/TASK_ID`
3. Wait for `"status": "SUCCESS"`
4. Then query results

## 🎓 Learn More

- Full documentation: See [README.md](README.md)
- API docs: http://localhost:8000/docs
- Interactive API: http://localhost:8000/redoc

---

**Happy Crawling! 🕷️**

