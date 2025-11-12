"""
MongoDB Database Layer
Handles connections and operations for the web crawler
"""
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from datetime import datetime
import os
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MongoDBHandler:
    """Handles MongoDB operations for the web crawler"""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB connection string. If None, uses MONGODB_URI env var
        """
        self.connection_string = connection_string or os.getenv(
            "MONGODB_URI", 
            "mongodb://mongodb:27017/"
        )
        self.client = None
        self.db = None
        self.pages_collection = None
        self.domains_collection = None
        
    def connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            
            # Get database
            db_name = os.getenv("MONGODB_DATABASE", "web_crawler")
            self.db = self.client[db_name]
            
            # Get collections
            self.pages_collection = self.db["pages"]
            self.domains_collection = self.db["domains"]
            
            # Create indexes
            self._create_indexes()
            
            logger.info(f"Successfully connected to MongoDB: {db_name}")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def _create_indexes(self):
        """Create necessary indexes for collections"""
        # Index on URL for pages collection (unique)
        self.pages_collection.create_index([("url", ASCENDING)], unique=True)
        self.pages_collection.create_index([("domain", ASCENDING)])
        self.pages_collection.create_index([("fetched_at", DESCENDING)])
        
        # Index on domain name (unique)
        self.domains_collection.create_index([("name", ASCENDING)], unique=True)
        
        logger.info("Created MongoDB indexes")
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection")
    
    def insert_page(self, page_data: Dict[str, Any]) -> bool:
        """
        Insert a crawled page into the database
        
        Args:
            page_data: Dictionary containing page information
                - url: str (required)
                - title: str
                - html: str
                - text_content: str
                - links: List[str]
                - domain: str
                - status_code: int
                - fetched_at: datetime
        
        Returns:
            bool: True if inserted successfully, False otherwise
        """
        try:
            # Ensure fetched_at is set
            if "fetched_at" not in page_data:
                page_data["fetched_at"] = datetime.utcnow()
            
            self.pages_collection.insert_one(page_data)
            logger.info(f"Inserted page: {page_data['url']}")
            return True
            
        except DuplicateKeyError:
            logger.warning(f"Page already exists: {page_data.get('url')}")
            # Update existing page (remove _id if present to avoid immutable field error)
            update_data = {k: v for k, v in page_data.items() if k != "_id"}
            self.pages_collection.update_one(
                {"url": page_data["url"]},
                {"$set": update_data}
            )
            return True
            
        except Exception as e:
            logger.error(f"Error inserting page: {e}")
            return False
    
    def get_pages_by_domain(self, domain: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve pages for a specific domain
        
        Args:
            domain: Domain name to query
            limit: Maximum number of results to return
        
        Returns:
            List of page documents
        """
        try:
            pages = list(
                self.pages_collection.find(
                    {"domain": domain},
                    {"_id": 0, "html": 0}  # Exclude _id and html content
                )
                .sort("fetched_at", DESCENDING)
                .limit(limit)
            )
            return pages
        except Exception as e:
            logger.error(f"Error retrieving pages for domain {domain}: {e}")
            return []
    
    def get_page_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific page by URL
        
        Args:
            url: URL to query
        
        Returns:
            Page document or None
        """
        try:
            page = self.pages_collection.find_one(
                {"url": url},
                {"_id": 0}
            )
            return page
        except Exception as e:
            logger.error(f"Error retrieving page {url}: {e}")
            return None
    
    def update_domain(self, domain: str, crawl_depth: int = 1) -> bool:
        """
        Update or insert domain information
        
        Args:
            domain: Domain name
            crawl_depth: Depth of crawl
        
        Returns:
            bool: True if successful
        """
        try:
            self.domains_collection.update_one(
                {"name": domain},
                {
                    "$set": {
                        "last_crawled": datetime.utcnow(),
                        "crawl_depth": crawl_depth
                    }
                },
                upsert=True
            )
            logger.info(f"Updated domain: {domain}")
            return True
        except Exception as e:
            logger.error(f"Error updating domain {domain}: {e}")
            return False
    
    def get_domain_info(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a domain
        
        Args:
            domain: Domain name
        
        Returns:
            Domain document or None
        """
        try:
            domain_info = self.domains_collection.find_one(
                {"name": domain},
                {"_id": 0}
            )
            return domain_info
        except Exception as e:
            logger.error(f"Error retrieving domain info for {domain}: {e}")
            return None
    
    def get_all_domains(self) -> List[Dict[str, Any]]:
        """
        Get all crawled domains
        
        Returns:
            List of domain documents
        """
        try:
            domains = list(
                self.domains_collection.find(
                    {},
                    {"_id": 0}
                ).sort("last_crawled", DESCENDING)
            )
            return domains
        except Exception as e:
            logger.error(f"Error retrieving all domains: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get crawler statistics
        
        Returns:
            Dictionary with statistics
        """
        try:
            total_pages = self.pages_collection.count_documents({})
            total_domains = self.domains_collection.count_documents({})
            
            # Get recent pages
            recent_pages = self.pages_collection.count_documents({
                "fetched_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
            })
            
            return {
                "total_pages": total_pages,
                "total_domains": total_domains,
                "pages_today": recent_pages
            }
        except Exception as e:
            logger.error(f"Error retrieving stats: {e}")
            return {}


# Global instance
mongo_handler = MongoDBHandler()

