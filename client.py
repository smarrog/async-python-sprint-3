import asyncio
import logging
import shutil
import sys
from typing import Self
from aioconsole import ainput

from settings import Settings

HELP_FILE = "help.txt"
SERVER_SIDE_COMMANDS = [
    "RENAME",
    "USERS",
    "SEND",
    "CANCEL",
    "HISTORY",
    "REPORT"
]

logger = logging.getLogger(__name__)


class Client:
    def __init__(self, settings: Settings, client_name: str = None) -> None:
        self._settings: Settings = settings
        self._client_name: str = client_name

    async def __aenter__(self) -> Self:
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        logger.info("Connected to %s:%s", self._host, self._port)
        self._receiver = asyncio.ensure_future(self._receive())
        if self._client_name is None:
            await self._send(f"introduce")
        else:
            await self._send(f"introduce {self._client_name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._receiver.cancel()
        self._writer.close()
        await self._writer.wait_closed()
        logger.info("Connection to %s:%s is closed", self._host, self._port)

    async def start(self) -> None:
        while True:
            request: str = await ainput()
            print("\033[A                             \033[A")  # clear last line

            match request.split():
                case [command_name, *tail]:
                    command_name = command_name.upper()
                    if command_name in SERVER_SIDE_COMMANDS:
                        await self._send(request)
                        continue

                    if command_name == "EXIT":
                        break
                    elif command_name == "HELP":
                        with open(HELP_FILE, 'r', encoding='utf-8') as f:
                            shutil.copyfileobj(f, sys.stdout)
                    else:
                        logger.info(f"Unknown command: \"{command_name}\"")
                        print(f"Unknown command: \"{command_name}\". Type \"help\" to see list of available commands")

                case _:
                    # empty request
                    continue

    @property
    def _host(self) -> str:
        return self._settings.host

    @property
    def _port(self) -> int:
        return self._settings.port

    async def _send(self, request: str) -> None:
        logger.info("Send: %s", request)
        request_in_bytes: bytes = str.encode(request)
        self._writer.write(request_in_bytes)
        await self._writer.drain()

    async def _receive(self) -> None:
        while True:
            try:
                response_in_bytes: bytes = await self._reader.readline()
                if response_in_bytes == b'':
                    # Connection closed by server
                    print("Server shutdown")
                    break

                response: str = response_in_bytes.decode().strip()
                logger.info(f"Response: {response}")
                print(response)
            except ConnectionError:
                break
