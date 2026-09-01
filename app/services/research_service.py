import hashlib
import ipaddress
import socket
from urllib.parse import urlparse
from datetime import datetime
from uuid import uuid4
import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.learning import ResearchSource

class ResearchService:
    def __init__(self, db: Session):
        self.db = db
        self.max_size = 5 * 1024 * 1024  # 5MB limit
        self.timeout = 10.0

    def _resolve_and_check_ssrf(self, url: str) -> None:
        """Prevent SSRF by blocking local and internal IPs."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise HTTPException(status_code=400, detail="Invalid URL scheme. Only HTTP and HTTPS are allowed.")
        
        hostname = parsed.hostname
        if not hostname:
            raise HTTPException(status_code=400, detail="Invalid URL hostname.")
        
        try:
            ip = socket.gethostbyname(hostname)
        except socket.gaierror:
            raise HTTPException(status_code=400, detail="Could not resolve hostname.")
        
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
            raise HTTPException(status_code=403, detail="Access to internal/private IPs is forbidden.")

    async def fetch_and_extract(self, url: str) -> dict:
        self._resolve_and_check_ssrf(url)
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Check size before reading entire content if Content-Length is provided
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > self.max_size:
                    raise HTTPException(status_code=413, detail="Response too large.")
                
                content = response.content
                if len(content) > self.max_size:
                    raise HTTPException(status_code=413, detail="Response too large.")
                    
                text_content = content.decode("utf-8", errors="ignore")
                
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {str(e)}")

        soup = BeautifulSoup(text_content, "html.parser")
        
        # Extract metadata
        title = soup.title.string if soup.title else None
        if title:
            title = title.strip()
            
        canonical_tag = soup.find("link", rel="canonical")
        canonical_url = canonical_tag["href"] if canonical_tag and canonical_tag.has_attr("href") else url
        
        parsed_url = urlparse(url)
        domain = parsed_url.hostname or "unknown"
        
        # Extract text content
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        raw_text = soup.get_text(separator=" ", strip=True)
        
        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        
        return {
            "url": url,
            "canonical_url": canonical_url,
            "domain": domain,
            "title": title,
            "publisher": domain,  # Simplified publisher
            "raw_content": raw_text,
            "content_hash": content_hash
        }

    async def ingest_url(self, url: str) -> ResearchSource:
        """Fetch, extract, check duplicates, and store the ResearchSource."""
        extracted = await self.fetch_and_extract(url)
        
        # Check for duplicates
        existing = self.db.execute(
            select(ResearchSource).where(
                (ResearchSource.canonical_url == extracted["canonical_url"]) |
                (ResearchSource.content_hash == extracted["content_hash"])
            )
        ).scalars().first()
        
        if existing:
            raise HTTPException(status_code=409, detail="This content has already been ingested.")
        
        source = ResearchSource(
            id=str(uuid4()),
            url=extracted["url"],
            canonical_url=extracted["canonical_url"],
            domain=extracted["domain"],
            title=extracted["title"],
            publisher=extracted["publisher"],
            source_type="INTERNET",
            raw_content=extracted["raw_content"],
            content_hash=extracted["content_hash"],
            extracted_facts={}  # Placeholder for Phase N AI extraction
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def list_sources(self, skip: int = 0, limit: int = 50):
        return self.db.execute(
            select(ResearchSource).order_by(ResearchSource.created_at.desc()).offset(skip).limit(limit)
        ).scalars().all()
    
    def get_source(self, source_id: str) -> ResearchSource:
        source = self.db.execute(
            select(ResearchSource).where(ResearchSource.id == source_id)
        ).scalars().first()
        if not source:
            raise HTTPException(status_code=404, detail="Research source not found.")
        return source
