"""
FastAPI Service
REST API for the distributed web crawler
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import sys
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import Celery from worker tasks
from celery import Celery

# Initialize MongoDB
from db.mongo import mongo_handler

# Create Celery app client for API
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery(
    "web_crawler",
    broker=redis_url,
    backend=redis_url
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Distributed Web Crawler API",
    description="API for managing distributed web crawling tasks",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class CrawlRequest(BaseModel):
    """Request model for crawling a single URL"""
    url: HttpUrl
    max_depth: Optional[int] = Field(default=1, ge=0, le=5, description="Maximum crawl depth (0-5)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "max_depth": 2
            }
        }


class DomainCrawlRequest(BaseModel):
    """Request model for crawling an entire domain"""
    domain_url: HttpUrl
    max_depth: Optional[int] = Field(default=2, ge=0, le=5, description="Maximum crawl depth")
    max_pages: Optional[int] = Field(default=50, ge=1, le=1000, description="Maximum pages to crawl")
    
    class Config:
        json_schema_extra = {
            "example": {
                "domain_url": "https://example.com",
                "max_depth": 2,
                "max_pages": 100
            }
        }


class TaskResponse(BaseModel):
    """Response model for task submission"""
    task_id: str
    status: str
    message: str


class PageResponse(BaseModel):
    """Response model for page data"""
    url: str
    title: str
    domain: str
    status_code: int
    fetched_at: datetime
    links: List[str]
    text_content: Optional[str] = None


class DomainResponse(BaseModel):
    """Response model for domain info"""
    name: str
    last_crawled: datetime
    crawl_depth: int
    page_count: Optional[int] = None


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    logger.info("Starting FastAPI application...")
    mongo_handler.connect()
    logger.info("Connected to MongoDB")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down FastAPI application...")
    mongo_handler.close()


# API Routes
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Distributed Web Crawler API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "crawl": "/crawl",
            "domain_crawl": "/crawl/domain",
            "results": "/results/{domain}",
            "page": "/page",
            "domains": "/domains",
            "stats": "/stats",
            "task_status": "/task/{task_id}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        mongo_handler.db.command('ping')
        
        # Check Celery worker
        worker_health = celery_app.send_task('src.worker.tasks.health_check')
        worker_result = worker_health.get(timeout=5)
        
        return {
            "status": "healthy",
            "mongodb": "connected",
            "celery": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/crawl", response_model=TaskResponse)
async def submit_crawl_task(request: CrawlRequest):
    """
    Submit a crawl task for a single URL
    
    Args:
        request: CrawlRequest with URL and optional max_depth
    
    Returns:
        TaskResponse with task_id and status
    """
    try:
        url = str(request.url)
        logger.info(f"Received crawl request for: {url}")
        
        # Submit task to Celery
        task = celery_app.send_task(
            'src.worker.tasks.crawl_url',
            args=[url, 0, request.max_depth]
        )
        
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Crawl task submitted for {url}"
        )
        
    except Exception as e:
        logger.error(f"Error submitting crawl task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")


@app.post("/crawl/domain", response_model=TaskResponse)
async def submit_domain_crawl_task(request: DomainCrawlRequest):
    """
    Submit a crawl task for an entire domain
    
    Args:
        request: DomainCrawlRequest with domain URL, max_depth, and max_pages
    
    Returns:
        TaskResponse with task_id and status
    """
    try:
        domain_url = str(request.domain_url)
        logger.info(f"Received domain crawl request for: {domain_url}")
        
        # Submit task to Celery
        task = celery_app.send_task(
            'src.worker.tasks.crawl_domain',
            args=[domain_url, request.max_depth, request.max_pages]
        )
        
        return TaskResponse(
            task_id=task.id,
            status="queued",
            message=f"Domain crawl task submitted for {domain_url}"
        )
        
    except Exception as e:
        logger.error(f"Error submitting domain crawl task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")


@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of a crawl task
    
    Args:
        task_id: Celery task ID
    
    Returns:
        Task status information
    """
    try:
        task_result = celery_app.AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": task_result.status,
            "ready": task_result.ready(),
            "successful": task_result.successful() if task_result.ready() else None
        }
        
        if task_result.ready():
            if task_result.successful():
                response["result"] = task_result.result
            else:
                response["error"] = str(task_result.info)
        
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving task status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve task status: {str(e)}")


@app.get("/results/{domain}")
async def get_results_by_domain(domain: str, limit: int = 100):
    """
    Get crawl results for a specific domain
    
    Args:
        domain: Domain name to query
        limit: Maximum number of results (default: 100)
    
    Returns:
        List of crawled pages
    """
    try:
        logger.info(f"Retrieving results for domain: {domain}")
        pages = mongo_handler.get_pages_by_domain(domain, limit)
        
        if not pages:
            raise HTTPException(status_code=404, detail=f"No results found for domain: {domain}")
        
        return {
            "domain": domain,
            "count": len(pages),
            "pages": pages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")


@app.get("/page")
async def get_page_by_url(url: str):
    """
    Get details for a specific page by URL
    
    Args:
        url: URL to query (query parameter)
    
    Returns:
        Page details
    """
    try:
        logger.info(f"Retrieving page: {url}")
        page = mongo_handler.get_page_by_url(url)
        
        if not page:
            raise HTTPException(status_code=404, detail=f"Page not found: {url}")
        
        return page
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving page: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve page: {str(e)}")


@app.get("/domains")
async def get_all_domains():
    """
    Get list of all crawled domains
    
    Returns:
        List of domains with metadata
    """
    try:
        logger.info("Retrieving all domains")
        domains = mongo_handler.get_all_domains()
        
        # Enrich with page counts
        for domain in domains:
            pages = mongo_handler.get_pages_by_domain(domain['name'], limit=1)
            # Get actual count
            domain['page_count'] = mongo_handler.pages_collection.count_documents(
                {"domain": domain['name']}
            )
        
        return {
            "count": len(domains),
            "domains": domains
        }
        
    except Exception as e:
        logger.error(f"Error retrieving domains: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve domains: {str(e)}")


@app.get("/stats")
async def get_stats():
    """
    Get crawler statistics
    
    Returns:
        Statistics about crawled data
    """
    try:
        stats = mongo_handler.get_stats()
        return {
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

