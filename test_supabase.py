import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

from db.client import get_client

async def test():
    client = get_client()
    try:
        result = (
            client.table("stories")
            .select("id, title, content, story_type, status, credits_used, llm_provider, created_at")
            .eq("org_id", "demo-org-999")
            .order("created_at", desc=True)
            .range(0, 19)
            .execute()
        )
        print("Success:", result)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
