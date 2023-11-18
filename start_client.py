import asyncio
import sys

from settings import Settings
from client import Client
from typing import Optional
from log_settings import init_console_only as init_logging


if __name__ == "__main__":
    init_logging()

    settings: Settings = Settings()
    client_name: Optional[str] = None
    if len(sys.argv) > 1:
        client_name = sys.argv[1]

    async def main():
        async with Client(settings, client_name) as client:
            await client.start()

    asyncio.run(main())
