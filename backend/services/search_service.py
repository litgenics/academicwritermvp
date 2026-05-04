import requests
import xml.etree.ElementTree as ET
from typing import List, Optional
from pydantic import BaseModel
import os
from scholarly import scholarly

class SearchResult(BaseModel):
    title: str
    authors: List[str]
    summary: str
    pdf_url: Optional[str]
    published: str
    source: str

def search_arxiv(query: str, max_results: int = 5) -> List[SearchResult]:
    base_url = "http://export.arxiv.org/api/query?"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results
    }
    try:
        response = requests.get(base_url, params=params, timeout=15)
        if response.status_code != 200:
            return []
        
        root = ET.fromstring(response.text)
        results = []
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', namespace):
            title = entry.find('atom:title', namespace).text.strip().replace('\n', ' ')
            authors = [author.find('atom:name', namespace).text for author in entry.findall('atom:author', namespace)]
            summary = entry.find('atom:summary', namespace).text.strip().replace('\n', ' ')
            published = entry.find('atom:published', namespace).text
            
            pdf_url = None
            for link in entry.findall('atom:link', namespace):
                if link.attrib.get('title') == 'pdf' or link.attrib.get('type') == 'application/pdf':
                    pdf_url = link.attrib.get('href')
                    
            results.append(SearchResult(
                title=title,
                authors=authors,
                summary=summary,
                pdf_url=pdf_url,
                published=published,
                source="arXiv"
            ))
        return results
    except Exception as e:
        print(f"ArXiv search error: {e}")
        return []

def search_scholarly(query: str, max_results: int = 5) -> List[SearchResult]:
    """
    Uses scholarly to find papers on Google Scholar.
    Implements the 'Option B' logic: only if an eprint/pdf URL is available.
    """
    try:
        print(f"Scholarly: Searching for '{query}'...")
        search_query = scholarly.search_pubs(query)
        results = []
        
        count = 0
        while count < max_results:
            try:
                pub = next(search_query)
                # 'pub' contains 'eprint_url' which is often the PDF link
                pdf_url = pub.get('eprint_url')
                
                if pdf_url:
                    bib = pub.get('bib', {})
                    results.append(SearchResult(
                        title=bib.get('title', 'Unknown Title'),
                        authors=bib.get('author', []),
                        summary=bib.get('abstract', ''),
                        pdf_url=pdf_url,
                        published=bib.get('pub_year', ''),
                        source="Google Scholar (Scraped)"
                    ))
                    count += 1
            except StopIteration:
                break
            except Exception as e:
                print(f"Error parsing scholarly result: {e}")
                continue
                
        return results
    except Exception as e:
        print(f"Scholarly was blocked or failed: {e}")
        return []

def search_serpapi_scholar(query: str, max_results: int = 5) -> List[SearchResult]:
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key or api_key == "your_serpapi_key_here":
        return []
    
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": api_key,
        "num": max_results
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = []
        for res in data.get("organic_results", []):
            resources = res.get("resources", [])
            pdf_url = None
            for resource in resources:
                if resource.get("file_format") == "PDF" or "pdf" in resource.get("link", "").lower():
                    pdf_url = resource.get("link")
                    break
            
            # If no resource link, try the main link if it looks like a PDF
            if not pdf_url and "pdf" in res.get("link", "").lower():
                pdf_url = res.get("link")

            if pdf_url:
                results.append(SearchResult(
                    title=res.get("title", "Unknown Title"),
                    authors=[a.get("name") for a in res.get("publication_info", {}).get("authors", [])],
                    summary=res.get("snippet", ""),
                    pdf_url=pdf_url,
                    published=res.get("publication_info", {}).get("summary", ""),
                    source="Google Scholar (via SerpAPI)"
                ))
        return results
    except Exception as e:
        print(f"SerpAPI search error: {e}")
        return []

def hybrid_search(query: str, target_count: int = 5) -> List[SearchResult]:
    # 1. Try SerpAPI first if available
    results = search_serpapi_scholar(query, max_results=target_count)
    
    # 2. Try Scholarly if SerpAPI failed or returned nothing
    if len(results) < target_count:
        print(f"SerpAPI only found {len(results)} PDFs. Trying Scholarly...")
        scholarly_results = search_scholarly(query, max_results=target_count - len(results))
        results.extend(scholarly_results)

    # 3. Fill gaps with ArXiv
    if len(results) < target_count:
        print(f"Scholar tools only found {len(results)} PDFs. Falling back to ArXiv...")
        arxiv_results = search_arxiv(query, max_results=target_count - len(results))
        results.extend(arxiv_results)
        
    return results[:target_count]
