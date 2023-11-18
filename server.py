import asyncio
import datetime
import logging
import argparse
from threading import Thread
from dataclasses import dataclass
from datetime import datetime as dt
from time import sleep
from typing import Optional, Self, Callable

from settings import Settings
from utils import CancellationToken, MaxSizeList

logger = logging.getLogger()


@dataclass
class UserData:
    settings: Settings
    peer_name: tuple[str, int]
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    user_name: str
    history: MaxSizeList
    reports: list[Self]
    delayed_messages_tokens: list[CancellationToken]
    ban_until: Optional[dt] = None
    spam_period_end: Optional[dt] = None
    messages_in_spam_period: int = 0

    def __repr__(self):
        return f"{str(self.peer_name)} -> {self.user_name}"

    @property
    def reports_amount(self):
        return len(self.reports)

    @property
    def is_banned(self):
        if self.ban_until is None:
            return False
        return self.ban_until > dt.now()

    def inc_message_counter_and_check_if_spam(self) -> bool:
        now: dt = dt.now()
        if self.spam_period_end is None or now > self.spam_period_end:
            self.messages_in_spam_period = 0
            self.spam_period_end = now + datetime.timedelta(seconds=self.settings.spam_period)

        self.messages_in_spam_period = self.messages_in_spam_period + 1
        return self.messages_in_spam_period > self.settings.messages_limit_in_spam_period

class Server:
    def __init__(self, settings: Settings) -> None:
        self._users: list[UserData] = []
        self._settings: Settings = settings
        self._server: Optional[asyncio.Server] = None
        self._history: MaxSizeList = MaxSizeList(settings.history_size)
        self._default_names_counter: int = 1

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()

    async def start(self) -> None:
        logger.info("Start server %s:%s", self._host, self._port)
        self._server = await asyncio.start_server(self._handle_connection, self._host, self._port)
        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        if self._server is None:
            return

        logger.info("Stop server %s:%s", self._host, self._port)
        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer_name: tuple[str, int] = writer.get_extra_info("peername")
        default_user_name: str = f"{self._settings.default_name}_{self._default_names_counter}"
        self._default_names_counter: int = self._default_names_counter + 1

        history: MaxSizeList = MaxSizeList(self._settings.history_size)
        for history_message in self._history.data:
            history.add(history_message)

        user: UserData = UserData(self._settings, peer_name, reader, writer, default_user_name, history,
                                  list[UserData](), list[CancellationToken]())
        self._users.append(user)

        while True:
            try:
                request_data: bytes = await reader.read(1024)
                if request_data == b'':
                    # Connection closed by user
                    break

                request: str = bytes.decode(request_data)
                logger.info("{%s}: Request: %s", user, request)

                try:
                    self._handle_request(user, request)
                except:
                    self._send_message(user, "Internal Server Error")
                    logger.warning("{%s}: Error while handling request: %s", user, request)

            except ConnectionError:
                logger.info("{%s}: Connection error", user)
                break

        for cancellation_token in user.delayed_messages_tokens:
            cancellation_token.cancel()

        self._users.remove(user)
        self._send_message_to_all(f"{user.user_name} left the chat")
        writer.close()
        logger.info("{%s}: Disconnected", user)

    @property
    def _host(self) -> str:
        return self._settings.host

    @property
    def _port(self) -> int:
        return self._settings.port

    def _send_message_to_all(self, message: str, do_not_send_to: Optional[UserData] = None,
                             add_to_history: bool = False) -> str:
        full_message = ""
        for user in self._users:
            if do_not_send_to is None or do_not_send_to is not user:
                full_message = self._send_message(user, message, add_to_history)

        return full_message

    def _send_message(self, user: UserData, message: str, add_to_history: bool = False, show_time: bool = True) -> str:
        logger.info("{%s}: Send message: %s", user, message)

        if show_time:
            message: str = f"{self._time_to_str(dt.now())} {message}"

        if add_to_history:
            user.history.add(message)

        response_data: bytes = str.encode(message) + b"\n"
        user.writer.write(response_data)

        return message

    def _handle_request(self, user: UserData, request: str) -> None:
        match request.split():
            case [command, *tail]:
                command = command.upper()
                logger.info("Command %s:%s", command, tail)
                if command == "INTRODUCE":
                    user_name = ' '.join(tail)
                    self._introduce(user, user_name)
                if command == "RENAME":
                    user_name = ' '.join(tail)
                    self._rename(user, user_name)
                elif command == "USERS":
                    self._return_users_list(user)
                elif command == "SEND":
                    parser = argparse.ArgumentParser()

                    parser.add_argument("-d", "--delay", dest="delay", default=0, type=int)
                    parser.add_argument("-r", "--recipient", dest="recipient", default=None, type=str)

                    results, rest = parser.parse_known_args(tail)
                    message = ' '.join(rest)

                    self._send(user, message, delay_in_seconds=results.delay, recipient_name=results.recipient)
                elif command == "CANCEL":
                    self._cancel(user)
                elif command == "HISTORY":
                    self._show_user_history(user)
                elif command == "REPORT":
                    user_name = ' '.join(tail)
                    self._report(user, user_name)

    def _introduce(self, sender: UserData, user_name: str) -> None:
        is_name_correct, user_name, error = self._check_name(user_name)
        if is_name_correct:
            self._rename(sender, user_name, True)

        for history_message in self._history.data:
            self._send_message(sender, history_message, show_time=False)

        self._send_message_to_all(f"{sender.user_name} joined chat", sender)
        self._send_message(sender, f"{sender.user_name}, {self._settings.greeting_message}")

    def _rename(self, sender: UserData, user_name: str, is_silent: bool = False) -> None:
        is_name_correct, user_name, error = self._check_name(user_name)

        if not is_name_correct:
            if not is_silent:
                self._send_message(sender, error)
            return

        if not is_silent:
            self._send_message_to_all(f"{sender.user_name} changed name to {user_name}", sender)
            self._send_message(sender, f"Your name was changed to {user_name}")

        sender.user_name = user_name

    def _return_users_list(self, sender: UserData) -> None:
        self._send_system_block_message(sender, "USERS", self._users, lambda e: e.user_name)

    def _send(self, sender: UserData, message: str,
              recipient_name: Optional[str] = None, delay_in_seconds: int = 0) -> None:
        if sender.is_banned:
            ban_message: str = f"You are banned till {self._time_to_str(sender.ban_until)}"
            self._send_message(sender, ban_message)
            return

        if delay_in_seconds > 0:
            def send_async():
                sleep(delay_in_seconds)
                sender.delayed_messages_tokens.remove(cancellation_token)
                if cancellation_token.is_active:
                    self._send(sender, message, recipient_name)

            cancellation_token = CancellationToken()
            sender.delayed_messages_tokens.append(cancellation_token)
            self._send_message(sender, f"Your message will be send after {delay_in_seconds} seconds")
            thread = Thread(target=send_async)
            thread.start()
            return

        if message == '' or message is None:
            self._send_message(sender, "Empty messages are restricted")
            return

        is_spam: bool = sender.inc_message_counter_and_check_if_spam()
        if is_spam:
            spam_message: str = f"You are spamming to much. Wait until {self._time_to_str(sender.spam_period_end)}"
            self._send_message(sender, spam_message)
            return

        if recipient_name is None:
            sent_message = self._send_message_to_all(f"{sender.user_name}: {message}", add_to_history=True)
            self._history.add(sent_message)
        else:
            recipient = self._get_user_by_name(recipient_name)
            if recipient is None:
                self._send_message(sender, f"There is not user with name {recipient_name}", show_time=False)
            else:
                whisper_message: str = f"{sender.user_name}->{recipient.user_name}: {message}"
                self._send_message(sender, whisper_message, add_to_history=True)
                self._send_message(recipient, whisper_message, add_to_history=True)

    def _cancel(self, sender: UserData) -> None:
        if len(sender.delayed_messages_tokens) == 0:
            self._send_message(sender, "You have no delayed messages")
            return

        cancellation_token = sender.delayed_messages_tokens.pop()
        cancellation_token.cancel()
        self._send_message(sender, "You last delayed message was removed")

    def _show_user_history(self, sender: UserData) -> None:
        self._send_system_block_message(sender, "HISTORY", sender.history.data)

    def _report(self, sender: UserData, user_name: str) -> None:
        user_to_report: Optional[UserData] = self._get_user_by_name(user_name)

        if user_to_report is None:
            self._send_message(sender, f"There is not user with name {user_name}", show_time=False)
        elif user_to_report == sender:
            self._send_message(sender, "You can't report yourself", show_time=False)
        elif sender in user_to_report.reports:
            self._send_message(sender, f"{user_name} was already reported by you", show_time=False)
        elif user_to_report.is_banned:
            self._send_message(sender, f"{user_name} is already banned", show_time=False)
        else:
            user_to_report.reports.append(sender)
            self._send_message_to_all(f"User {user_name} was reported by {sender.user_name}. "
                                      f"Reports count: {user_to_report.reports_amount}")

            if user_to_report.reports_amount >= self._settings.reports_for_ban:
                self._ban(user_to_report)

    def _ban(self, user: UserData) -> None:
        user.reports.clear()
        user.ban_until = dt.now() + datetime.timedelta(seconds=self._settings.ban_duration)

        self._send_message_to_all(f"User {user.user_name} was banned until {self._time_to_str(user.ban_until)}")

    def _check_name(self, user_name: str) -> (bool, str, str):
        user_name = user_name.strip()

        if user_name == '' or user_name is None:
            return False, user_name, "Empty names are restricted"

        if " " in user_name:
            return False, user_name, "Empty spaces are restricted in names"

        for user in self._users:
            if user.user_name is not None and user.user_name == user_name:
                return False, user_name, "Already have user with that name"

        return True, user_name, None

    def _send_system_block_message(self, sender: UserData, block_name: str, data: list,
                                   worker: Callable[[object], str] = None) -> None:
        rows: list[str] = [f"*** {block_name} ***\n"]
        if len(data) == 0:
            rows.append("EMPTY\n")
        else:
            for element in data:
                if worker is not None:
                    element = worker(element)
                rows.append(element)
                rows.append("\n")

        message: str = "".join(rows)
        self._send_message(sender, message, show_time=False)

    def _get_user_by_name(self, user_name: str) -> Optional[UserData]:
        for user in self._users:
            if user.user_name == user_name:
                return user
        return None

    @staticmethod
    def _time_to_str(time: dt) -> str:
        return f"[{time.strftime("%Y-%m-%d %H:%M:%S")}]"
