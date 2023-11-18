from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    host: str = os.getenv("SERVER_HOST")
    port: int = os.getenv("SERVER_PORT")
    default_name: str = "Anonymous"
    greeting_message: str = "Welcome to Test Server"
    history_size: int = 20
    reports_for_ban: int = 2
    ban_duration: int = 600  # in seconds
    messages_limit_in_spam_period: int = 5
    spam_period: int = 10  # in seconds
