from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple, Literal
from datetime import date

class Problem(BaseModel):
    contestId: int
    index: str
    name: str
    rating: Optional[int] = 0
    tags: List[str]

class Submission(BaseModel):
    id: int
    contestId: int
    creationTimeSeconds: int
    relativeTimeSeconds: int
    problem: Problem
    programmingLanguage: str
    verdict: Optional[str] = ""
    inContest: bool

class ContestParticipation(BaseModel):
    contestId: int
    contestName: str
    rank: int
    oldRating: int
    newRating: int
    timestamp: int

