import asyncio
import httpx
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Fallback to local URL if deployed without env var
API_URL = os.getenv("SAKHI_API_URL", "http://localhost:8000/api/v1")
PING_INTERVAL = int(os.getenv("PING_INTERVAL_SECONDS", "600")) # 10 minutes

async def keep_alive():
    logger.info(f"Starting keep-alive script targeting {API_URL}/health every {PING_INTERVAL}s")
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                logger.info(f"Pinging {API_URL}/health...")
                response = await client.get(f"{API_URL}/health", timeout=10.0)
                
                if response.status_code == 200:
                    logger.info("Health check passed.")
                else:
                    logger.warning(f"Health check failed with status code: {response.status_code}")
                    
            except httpx.RequestError as exc:
                logger.error(f"An error occurred while requesting {exc.request.url!r}: {exc}")
                
            await asyncio.sleep(PING_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(keep_alive())
    except KeyboardInterrupt:
        logger.info("Keep-alive script stopped.")
