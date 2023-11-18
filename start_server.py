import asyncio

from server import Server
from settings import Settings
from log_settings import init_full_logs as init_logging


if __name__ == "__main__":
    init_logging("server")

    settings: Settings = Settings()

    async def main():
        async with Server(settings) as server:
            await server.start()

    asyncio.run(main())
