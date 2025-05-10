from pydantic import BaseModel
from typing import List, Dict, Tuple

class Problem(BaseModel):
    contest_id: int
    index: str
    name: str
    rating: int
    tags: List[str]

class Submission(BaseModel):
    submit_id: int
    contest_id: int
    creation_time: int
    relative_time: int
    problem: Problem
    language: str
    verdict: str
    in_contest: bool

class ContestParticipation(BaseModel):
    contest_id: int
    name: str
    old_rating: int
    new_rating: int
    rank: int
    date_time: str

class UserStats(BaseModel):
    attempted: int
    solved: int
    avg_difficulty: int
    problems: List[Problem]
    freq_tags: Dict[str, int]
    freq_days: Dict[str, int]
    num_contests: int
    contest_result: List[ContestParticipation]

class User(BaseModel):
    handle: str
    stats: UserStats


