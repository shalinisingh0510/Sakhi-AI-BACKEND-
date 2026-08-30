import asyncio
import httpx
from httpx_sse import aconnect_sse
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "http://localhost:8000/api/v1"

async def verify_e2e():
    async with httpx.AsyncClient() as client:
        # 1. Health check
        logger.info("Running health check...")
        health_resp = await client.get(f"{API_URL}/")
        assert health_resp.status_code == 200
        logger.info("Health check passed.")

        # 2. Register a test user
        logger.info("Registering test user...")
        user_data = {
            "email": "e2etest@example.com",
            "password": "testpassword123",
            "full_name": "E2E Test User",
            "role": "USER",
            "preferences": {"language": "hi"}
        }
        
        # Registration can be 201 or 400 if user exists, so let's ignore 400 for existing
        reg_resp = await client.post(f"{API_URL}/auth/register", json=user_data)
        if reg_resp.status_code not in (201, 400):
            logger.error(f"Failed to register user: {reg_resp.text}")
            return
            
        logger.info("Logging in...")
        login_data = {
            "username": "e2etest@example.com",
            "password": "testpassword123"
        }
        login_resp = await client.post(f"{API_URL}/auth/login", data=login_data)
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        logger.info("Login successful.")

        # 3. Fetch user profile
        logger.info("Fetching profile...")
        me_resp = await client.get(f"{API_URL}/auth/me", headers=headers)
        assert me_resp.status_code == 200
        logger.info("Profile fetched.")

        # 4. Trigger SSE chat stream
        logger.info("Testing SSE Chat Stream...")
        chat_payload = {
            "message": "Hello, how are you?",
            "language": "hi"
        }
        
        async with aconnect_sse(client, "POST", f"{API_URL}/chat/stream", json=chat_payload, headers=headers) as event_source:
            events_received = []
            async for sse in event_source.aiter_sse():
                events_received.append(sse.data)
                data = json.loads(sse.data)
                logger.info(f"Received SSE event type: {data.get('type')}")
                
            assert len(events_received) > 0
            logger.info("SSE chat stream passed successfully.")
            
        # 5. Clean up (mock for now as delete user endpoint might not exist)
        logger.info("E2E verification completed successfully.")

if __name__ == "__main__":
    asyncio.run(verify_e2e())
