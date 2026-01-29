#!/usr/bin/env python3
"""
Integration tests for the Distributed Web Crawler
Run with: python tests/test_crawler.py
"""
import requests
import time
import sys
from typing import Dict, Any

API_URL = "http://localhost:8000"

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")


def test_health_check() -> bool:
    """Test 1: Health Check"""
    print_header("Test 1: Health Check")
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("status") == "healthy":
            print_success("API is healthy")
            print_success(f"MongoDB: {data.get('mongodb')}")
            print_success(f"Celery: {data.get('celery')}")
            return True
        else:
            print_error(f"Health check failed: {data}")
            return False
            
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def test_ping() -> bool:
    """Lightweight ping check"""
    print_header("Ping: Lightweight Liveness Check")

    try:
        response = requests.get(f"{API_URL}/ping", timeout=5)
        data = response.json()

        if response.status_code == 200 and data.get("ping") == "pong":
            print_success("Ping endpoint responded with pong")
            return True
        else:
            print_error(f"Ping endpoint returned unexpected payload: {data}")
            return False
    except Exception as e:
        print_error(f"Ping endpoint failed: {e}")
        return False


def test_api_info() -> bool:
    """Test 2: API Information"""
    print_header("Test 2: API Information")
    
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        data = response.json()
        
        if response.status_code == 200:
            print_success(f"API Name: {data.get('name')}")
            print_success(f"Version: {data.get('version')}")
            print_success(f"Available endpoints: {len(data.get('endpoints', {}))}")
            return True
        else:
            print_error(f"API info failed: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"API info failed: {e}")
        return False


def test_crawl_single_url() -> Dict[str, Any]:
    """Test 3: Crawl a Single URL"""
    print_header("Test 3: Crawl Single URL")
    
    url = "https://example.com"
    print_info(f"Submitting crawl for: {url}")
    
    try:
        response = requests.post(
            f"{API_URL}/crawl",
            json={"url": url, "max_depth": 1},
            timeout=10
        )
        data = response.json()
        
        if response.status_code == 200 and data.get("task_id"):
            task_id = data["task_id"]
            print_success(f"Task submitted: {task_id}")
            print_info(f"Status: {data.get('status')}")
            return {"success": True, "task_id": task_id, "url": url}
        else:
            print_error(f"Crawl submission failed: {data}")
            return {"success": False}
            
    except Exception as e:
        print_error(f"Crawl submission failed: {e}")
        return {"success": False}


def test_task_status(task_id: str) -> bool:
    """Test 4: Check Task Status"""
    print_header("Test 4: Task Status & Completion")
    
    print_info(f"Checking task: {task_id}")
    print_info("Waiting for task to complete (max 30 seconds)...")
    
    for attempt in range(30):
        try:
            response = requests.get(f"{API_URL}/task/{task_id}", timeout=5)
            data = response.json()
            status = data.get("status")
            
            if status == "SUCCESS":
                result = data.get("result", {})
                print_success(f"Task completed successfully!")
                print_success(f"URL: {result.get('url')}")
                print_success(f"Title: {result.get('title')}")
                print_success(f"Links found: {result.get('links_found')}")
                print_success(f"Depth: {result.get('depth')}")
                return True
            elif status == "FAILURE":
                print_error(f"Task failed: {data.get('error')}")
                return False
            else:
                print(f"  Status: {status} (attempt {attempt + 1}/30)", end='\r')
                time.sleep(1)
                
        except Exception as e:
            print_error(f"Status check failed: {e}")
            return False
    
    print_error("Task did not complete within 30 seconds")
    return False


def test_get_results(domain: str) -> bool:
    """Test 5: Get Crawl Results"""
    print_header("Test 5: Retrieve Crawl Results")
    
    print_info(f"Getting results for domain: {domain}")
    
    try:
        response = requests.get(f"{API_URL}/results/{domain}?limit=10", timeout=5)
        data = response.json()
        
        if response.status_code == 200:
            count = data.get("count", 0)
            pages = data.get("pages", [])
            
            print_success(f"Found {count} page(s) for {domain}")
            
            for i, page in enumerate(pages[:3], 1):  # Show first 3
                print_success(f"  Page {i}:")
                print(f"    URL: {page.get('url')}")
                print(f"    Title: {page.get('title')}")
                print(f"    Status: {page.get('status_code')}")
                print(f"    Fetched: {page.get('fetched_at')}")
            
            return True
        else:
            print_error(f"Failed to get results: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Failed to get results: {e}")
        return False


def test_get_page(url: str) -> bool:
    """Test 6: Get Specific Page"""
    print_header("Test 6: Get Specific Page Details")
    
    print_info(f"Getting page details for: {url}")
    
    try:
        response = requests.get(f"{API_URL}/page", params={"url": url}, timeout=5)
        data = response.json()
        
        if response.status_code == 200:
            print_success(f"Page found!")
            print_success(f"  Title: {data.get('title')}")
            print_success(f"  Domain: {data.get('domain')}")
            print_success(f"  Status Code: {data.get('status_code')}")
            print_success(f"  Content Length: {data.get('content_length')} bytes")
            print_success(f"  Links: {len(data.get('links', []))}")
            return True
        else:
            print_error(f"Failed to get page: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Failed to get page: {e}")
        return False


def test_list_domains() -> bool:
    """Test 7: List All Domains"""
    print_header("Test 7: List All Crawled Domains")
    
    try:
        response = requests.get(f"{API_URL}/domains", timeout=5)
        data = response.json()
        
        if response.status_code == 200:
            count = data.get("count", 0)
            domains = data.get("domains", [])
            
            print_success(f"Found {count} domain(s)")
            
            for domain in domains:
                print_success(f"  {domain.get('name')}:")
                print(f"    Pages: {domain.get('page_count')}")
                print(f"    Last crawled: {domain.get('last_crawled')}")
                print(f"    Crawl depth: {domain.get('crawl_depth')}")
            
            return True
        else:
            print_error(f"Failed to list domains: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Failed to list domains: {e}")
        return False


def test_statistics() -> bool:
    """Test 8: Get Statistics"""
    print_header("Test 8: Crawler Statistics")
    
    try:
        response = requests.get(f"{API_URL}/stats", timeout=5)
        data = response.json()
        
        if response.status_code == 200:
            stats = data.get("statistics", {})
            print_success("Statistics retrieved:")
            print_success(f"  Total pages: {stats.get('total_pages')}")
            print_success(f"  Total domains: {stats.get('total_domains')}")
            print_success(f"  Pages today: {stats.get('pages_today')}")
            print_success(f"  Timestamp: {data.get('timestamp')}")
            return True
        else:
            print_error(f"Failed to get stats: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Failed to get stats: {e}")
        return False


def test_domain_crawl() -> bool:
    """Test 9: Domain Crawl (Optional - can be slow)"""
    print_header("Test 9: Domain Crawl (Multiple Pages)")
    
    print_info("Submitting domain crawl for example.com (max 5 pages)")
    
    try:
        response = requests.post(
            f"{API_URL}/crawl/domain",
            json={
                "domain_url": "https://example.com",
                "max_depth": 1,
                "max_pages": 5
            },
            timeout=10
        )
        data = response.json()
        
        if response.status_code == 200 and data.get("task_id"):
            print_success(f"Domain crawl submitted: {data['task_id']}")
            print_info("Note: This crawl may take longer to complete")
            return True
        else:
            print_error(f"Domain crawl failed: {data}")
            return False
            
    except Exception as e:
        print_error(f"Domain crawl failed: {e}")
        return False


def run_tests():
    """Run all tests"""
    print(f"\n{Colors.BOLD}🕷️  Distributed Web Crawler - Integration Tests{Colors.END}")
    print(f"{Colors.BOLD}Testing API at: {API_URL}{Colors.END}")
    
    results = []
    
    # Test 1: Health Check
    results.append(("Health Check", test_health_check()))

    # Optional: lightweight ping check (does not fail the suite)
    ping_ok = test_ping()
    results.append(("Ping (optional)", ping_ok))
    
    if not results[-1][1]:
        print_error("\n❌ Health check failed. Make sure all services are running:")
        print_info("  Run: docker compose up -d")
        sys.exit(1)
    
    # Test 2: API Info
    results.append(("API Info", test_api_info()))
    
    # Test 3: Submit Crawl
    crawl_result = test_crawl_single_url()
    results.append(("Submit Crawl", crawl_result["success"]))
    
    if crawl_result["success"]:
        # Test 4: Task Status
        task_id = crawl_result["task_id"]
        url = crawl_result["url"]
        results.append(("Task Status", test_task_status(task_id)))
        
        # Test 5: Get Results
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        results.append(("Get Results", test_get_results(domain)))
        
        # Test 6: Get Page
        results.append(("Get Page", test_get_page(url)))
    
    # Test 7: List Domains
    results.append(("List Domains", test_list_domains()))
    
    # Test 8: Statistics
    results.append(("Statistics", test_statistics()))
    
    # Test 9: Domain Crawl (optional)
    results.append(("Domain Crawl", test_domain_crawl()))
    
    # Print Summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All tests passed! Crawler is working perfectly.{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  Some tests failed. Check the output above.{Colors.END}\n")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrupted by user{Colors.END}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.END}\n")
        sys.exit(1)

