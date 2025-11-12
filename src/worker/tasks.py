"""
Celery Worker Tasks
Handles distributed crawling tasks
"""
from celery import Celery
from celery.utils.log import get_task_logger
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
import time
import os
from typing import List, Dict, Any, Optional
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from db.mongo import mongo_handler

logger = get_task_logger(__name__)

# Initialize Celery
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery(
    "web_crawler",
    broker=redis_url,
    backend=redis_url
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Connect to MongoDB when worker starts
mongo_handler.connect()


class RateLimiter:
    """Simple in-memory rate limiter for domains"""
    
    def __init__(self):
        self.last_request_time = {}
        self.min_delay = 1.0  # Minimum 1 second between requests to same domain
    
    def wait_if_needed(self, domain: str):
        """Wait if necessary to respect rate limits"""
        now = time.time()
        if domain in self.last_request_time:
            elapsed = now - self.last_request_time[domain]
            if elapsed < self.min_delay:
                sleep_time = self.min_delay - elapsed
                logger.info(f"Rate limiting {domain}: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self.last_request_time[domain] = time.time()


rate_limiter = RateLimiter()


def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    parsed = urlparse(url)
    return parsed.netloc


def extract_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Extract all links from a page"""
    links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        # Convert relative URLs to absolute
        absolute_url = urljoin(base_url, href)
        links.append(absolute_url)
    return links


def fetch_page(url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Fetch a web page and extract content
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with page data or None on failure
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; DistributedWebCrawler/1.0)'
        }
        
        logger.info(f"Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else "No title"
        
        # Extract text content (remove scripts and styles)
        for script in soup(["script", "style"]):
            script.decompose()
        text_content = soup.get_text(separator=' ', strip=True)
        
        # Extract links
        links = extract_links(soup, url)
        
        # Get domain
        domain = extract_domain(url)
        
        page_data = {
            "url": url,
            "title": title,
            "html": str(soup),
            "text_content": text_content[:10000],  # Limit text content size
            "links": links[:100],  # Limit number of links stored
            "domain": domain,
            "status_code": response.status_code,
            "fetched_at": datetime.utcnow(),
            "content_length": len(response.content)
        }
        
        logger.info(f"Successfully fetched: {url} (status: {response.status_code}, links: {len(links)})")
        return page_data
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return None


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def crawl_url(self, url: str, depth: int = 0, max_depth: int = 2) -> Dict[str, Any]:
    """
    Crawl a single URL and optionally follow links
    
    Args:
        url: URL to crawl
        depth: Current crawl depth
        max_depth: Maximum depth to crawl
    
    Returns:
        Dictionary with crawl results
    """
    try:
        logger.info(f"Crawling URL: {url} (depth: {depth}/{max_depth})")
        
        # Extract domain and apply rate limiting
        domain = extract_domain(url)
        rate_limiter.wait_if_needed(domain)
        
        # Fetch the page
        page_data = fetch_page(url)
        
        if not page_data:
            return {
                "status": "failed",
                "url": url,
                "error": "Failed to fetch page"
            }
        
        # Store in MongoDB
        mongo_handler.insert_page(page_data)
        
        # Update domain info
        mongo_handler.update_domain(domain, crawl_depth=depth)
        
        # Optionally crawl linked pages (if within depth limit and same domain)
        crawled_links = []
        if depth < max_depth:
            same_domain_links = [
                link for link in page_data['links']
                if extract_domain(link) == domain and link != url
            ]
            
            # Limit number of links to follow
            links_to_crawl = same_domain_links[:10]
            
            logger.info(f"Following {len(links_to_crawl)} links from {url}")
            
            # Queue subtasks for linked pages
            for link in links_to_crawl:
                crawl_url.apply_async(
                    args=[link, depth + 1, max_depth],
                    countdown=5  # Delay to avoid overwhelming
                )
                crawled_links.append(link)
        
        return {
            "status": "success",
            "url": url,
            "title": page_data['title'],
            "links_found": len(page_data['links']),
            "links_crawled": len(crawled_links),
            "depth": depth
        }
        
    except Exception as exc:
        logger.error(f"Error crawling {url}: {exc}")
        # Retry the task
        raise self.retry(exc=exc)


@celery_app.task(bind=True)
def crawl_domain(self, domain_url: str, max_depth: int = 2, max_pages: int = 50) -> Dict[str, Any]:
    """
    Crawl an entire domain starting from the given URL
    
    Args:
        domain_url: Starting URL for the domain
        max_depth: Maximum crawl depth
        max_pages: Maximum number of pages to crawl
    
    Returns:
        Dictionary with crawl summary
    """
    try:
        logger.info(f"Starting domain crawl: {domain_url} (max_depth: {max_depth}, max_pages: {max_pages})")
        
        # Start with the main URL
        result = crawl_url.apply_async(args=[domain_url, 0, max_depth])
        
        return {
            "status": "started",
            "domain_url": domain_url,
            "task_id": result.id,
            "max_depth": max_depth,
            "max_pages": max_pages
        }
        
    except Exception as e:
        logger.error(f"Error starting domain crawl for {domain_url}: {e}")
        return {
            "status": "failed",
            "domain_url": domain_url,
            "error": str(e)
        }


@celery_app.task
def health_check() -> Dict[str, Any]:
    """Health check task to verify worker is functioning"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "worker": "celery"
    }

