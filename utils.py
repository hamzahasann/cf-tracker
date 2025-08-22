import json
from datetime import datetime
from typing import List, Tuple, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

def dict_to_model(model_cls: Type[T], data: dict) -> T:
    valid_keys = set(model_cls.model_fields.keys())
    filtered = {k: v for k, v in data.items() if k in valid_keys}
    return model_cls(**filtered)

def convert_to_unix_time(time: str, timezone) -> int:
    dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
    return timezone.localize(dt).timestamp()

def load_users(file: str = "users.txt") -> Tuple[List[str], List[str]]:
    with open(file, "r") as f:
        real_names_with_handles = [line.strip().split(',') for line in f if line.strip()]
    real_names = [name.strip() for name, _ in real_names_with_handles]
    handles = [handle.strip() for _, handle in real_names_with_handles]
    return real_names, handles

def get_contest_timestamp(contest_id: int) -> str:
    with open("data/contests.json", "r") as f:
        contests = json.load(f)
    for contest in contests:
        if contest["id"] == contest_id:
            timestamp = contest["startTimeSeconds"]
            return timestamp
    raise ValueError(f"Contest ID {contest_id} not found in contests.json")
