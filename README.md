# Distributed Web Crawler

A distributed web crawler using FastAPI, Celery, Redis, and MongoDB. Basically you submit URLs via REST API, workers crawl them in parallel, and everything gets stored in MongoDB.

## How it works

The API (FastAPI) accepts crawl requests and queues them in Redis. Celery workers pick up tasks, fetch the pages, parse links, and store everything in MongoDB. You can scale workers independently to handle more load.

```
FastAPI ─────> Redis ◀───── Celery Workers
   │                              │
   └──────────> MongoDB <─────────┘
```

What you get:
- REST API to submit crawl jobs and query results
- Distributed workers that crawl in parallel
- Rate limiting (1 sec between requests per domain)
- Depth-based crawling (follow links up to N levels deep)
- Retry logic when requests fail
- Everything runs in Docker containers

## Quick Start

### With Docker (easiest)

```bash
docker compose up --build
```

Wait 30 seconds for everything to start. You'll get:
- API at http://localhost:8000
- MongoDB on localhost:27017
- Redis on localhost:6379
- 2 worker processes

Check if it's working:
```bash
curl http://localhost:8000/health

# Or run the full test suite
./run_tests.sh
```

### Local Development

If you want to run things locally without Docker:

```bash
# Install deps
pip install -r requirements.txt

# Start Redis and MongoDB (still using Docker for these)
docker run -d -p 6379:6379 redis:7-alpine
docker run -d -p 27017:27017 mongo:7

# Start API
cd src
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Start workers (separate terminal)
cd src
celery -A worker.tasks worker --loglevel=info --concurrency=4
```

## Using the API

### Crawl a single URL

```bash
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "max_depth": 2}'
```

Response:
```json
{
  "task_id": "abc123-def456-...",
  "status": "queued",
  "message": "Crawl task submitted for https://example.com"
}
```

### Crawl an entire domain

```bash
curl -X POST http://localhost:8000/crawl/domain \
  -H "Content-Type: application/json" \
  -d '{
    "domain_url": "https://example.com",
    "max_depth": 2,
    "max_pages": 50
  }'
```

### Check task status

```bash
curl http://localhost:8000/task/abc123-def456-...
```

Keep polling until `status` is `SUCCESS`.

### Get results for a domain

```bash
curl http://localhost:8000/results/example.com?limit=10
```

### Get a specific page

```bash
curl "http://localhost:8000/page?url=https://example.com"
```

### List all crawled domains

```bash
curl http://localhost:8000/domains
```

### Get stats

```bash
curl http://localhost:8000/stats
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information and available endpoints |
| GET | `/health` | Health check for all services |
| POST | `/crawl` | Submit a single URL crawl task |
| POST | `/crawl/domain` | Submit a domain crawl task |
| GET | `/task/{task_id}` | Get task status and results |
| GET | `/results/{domain}` | Get all pages for a domain |
| GET | `/page?url={url}` | Get specific page details |
| GET | `/domains` | List all crawled domains |
| GET | `/stats` | Get crawler statistics |

## Project Structure

```
src/
├── api/main.py           # FastAPI REST API
├── worker/tasks.py       # Celery crawling tasks
└── db/mongo.py          # MongoDB operations

docker-compose.yml        # Runs everything
Dockerfile.api           # API container
Dockerfile.worker        # Worker container
```

## Configuration

Environment variables (all have defaults):
- `REDIS_URL` - Redis connection (default: `redis://redis:6379/0`)
- `MONGODB_URI` - MongoDB URI (default: `mongodb://mongodb:27017/`)
- `MONGODB_DATABASE` - Database name (default: `web_crawler`)

Crawl parameters:
- `max_depth` (0-5) - How deep to follow links
- `max_pages` (1-1000) - Max pages per domain crawl

Scale workers:
```bash
docker compose up --scale worker=4
```

## Testing

Run the comprehensive test suite:
```bash
./run_tests.sh
```

This tests:
- Health checks
- Crawl submission and task processing
- Result retrieval
- Domain listing
- Statistics

Or use the Makefile:
```bash
make test        # Run full test suite
make test-quick  # Quick health check only
```

## Development

Watch logs:
```bash
docker compose logs -f worker   # Worker logs
docker compose logs -f api      # API logs
```

Access MongoDB:
```bash
docker exec -it crawler-mongodb mongosh
use web_crawler
db.pages.find().limit(5)
```

Access Redis:
```bash
docker exec -it crawler-redis redis-cli
KEYS *
```

Or just use the Makefile:
```bash
make logs-worker
make shell-mongo
make shell-redis
```

## Data Model

MongoDB stores two collections:

**pages** - Individual crawled pages
```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "html": "<html>...</html>",
  "text_content": "...",
  "links": ["https://example.com/about", ...],
  "domain": "example.com",
  "status_code": 200,
  "fetched_at": "2025-11-12T10:30:00"
}
```

**domains** - Domain metadata
```json
{
  "name": "example.com",
  "last_crawled": "2025-11-12T10:30:00",
  "crawl_depth": 2
}
```

## Notes

**Rate limiting**: Minimum 1 second between requests to the same domain. Don't be an asshole to other people's servers.

**Scaling**: Need more throughput? Add more workers with `docker compose up --scale worker=N`. Each worker can handle 4 concurrent requests by default.

**Memory**: Workers store a simple in-memory rate limiter. If you restart workers, rate limits reset. For production you'd want Redis-backed rate limiting.

## Troubleshooting

Workers not picking up tasks:
```bash
docker compose logs redis
docker compose restart worker
```

MongoDB issues:
```bash
docker compose logs mongodb
docker compose restart mongodb
```

Nuclear option (deletes all data):
```bash
docker compose down -v
docker compose up --build
```

## License

MIT - do whatever you want with it.

