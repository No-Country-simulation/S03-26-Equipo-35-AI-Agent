import asyncio
from dotenv import load_dotenv
load_dotenv()

from core.rag.scraper import scrape_url
import httpx
import trafilatura

async def test():
    try:
        print("Testing httpx...")
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            resp = await client.get("https://aclo.org.bo/")
            print("HTTPX Staus:", resp.status_code)
            html = resp.text
            text = trafilatura.extract(html)
            print("Scraped length:", len(text) if text else 0)
    except Exception as e:
        print("Scrape failed:", e)

if __name__ == "__main__":
    asyncio.run(test())
