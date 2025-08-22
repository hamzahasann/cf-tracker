from datetime import datetime
import pytz
import json
from structs import Submission, Problem, User, ContestParticipation, UserStats
from typing import List

pakistan_tz = pytz.timezone("Asia/Karachi")

def load_submissions(handle, start_time, end_time) -> List[Submission]:
    with open(f"data/{handle}_submissions.json") as f:
        submissions = json.load(f)
    
    result = []
    for submission in submissions:
        if not (start_time <= submission["creationTimeSeconds"] < end_time):
            continue

        problem = submission["problem"]
        p = Problem(
            contest_id=problem["contestId"],
            index=problem["index"],
            name=problem["name"],
            rating=problem.get("rating", 0),
            tags=problem["tags"]
        )
        if "verdict" not in submission:
            # unjudged due to cf system testing, skip
            continue
        s = Submission(
            submit_id=submission["id"],
            contest_id=submission["contestId"],
            creation_time=submission["creationTimeSeconds"],
            relative_time=submission["relativeTimeSeconds"],
            problem=p,
            language=submission["programmingLanguage"],
            verdict=submission["verdict"],
            in_contest=submission["author"]["participantType"] == "CONTESTANT"
        )
        result.append(s)
    return result

def get_contest_timestamp(contest_id: int) -> str:
    with open("data/contests.json", "r") as f:
        contests = json.load(f)
    for contest in contests:
        if contest["id"] == contest_id:
            timestamp = contest["startTimeSeconds"]
            return datetime.fromtimestamp(timestamp, tz=pakistan_tz).strftime("%b %d %H:%M")
    return 0

def load_contest_data(handle) -> List[ContestParticipation]:
    with open(f"data/{handle}_rating.json", "r") as f:
        contest_participations = json.load(f)

    result = []
    for contest in contest_participations:
        c = ContestParticipation(
            contest_id=contest["contestId"],
            name=contest["contestName"],
            old_rating=contest["oldRating"],
            new_rating=contest["newRating"],
            rank=contest["rank"],
            date_time=get_contest_timestamp(contest["contestId"])
        )
        result.append(c)
    return result
    
def process(submissions: List[Submission], contest_data: List[ContestParticipation]) -> UserStats:
    num_solved = 0
    sum_difficulty = 0
    problems_calculated = 0
    solved_problems = []
    freq_tags = dict()
    freq_days = dict()
    contests = set()
    for submission in submissions:
        if submission.verdict == "OK":
            num_solved += 1
            sum_difficulty += submission.problem.rating
            if submission.problem.rating > 0:
                problems_calculated += 1
            solved_problems.append(submission.problem)
            day = datetime.fromtimestamp(submission.creation_time, tz=pakistan_tz).strftime("%d %m")
            if day not in freq_days:
                freq_days[day] = 0
            freq_days[day] += 1
            for tag in submission.problem.tags:
                if tag not in freq_tags:
                    freq_tags[tag] = 0
                freq_tags[tag] += 1
            if submission.in_contest:
                contests.add(submission.contest_id)
    
    if problems_calculated == 0:
        avg_difficulty = 0
    else:
        avg_difficulty = sum_difficulty / problems_calculated
    avg_difficulty = round(avg_difficulty / 50) * 50
    
    contest_data = [c for c in contest_data if c.contest_id in contests]

    stats = UserStats(
        attempted=len(submissions),
        solved=num_solved,
        avg_difficulty=avg_difficulty,
        problems=solved_problems,
        freq_tags=freq_tags,
        freq_days=freq_days,
        num_contests=len(contests),
        contest_result=contest_data
    )
    return stats

def convert_to_unix_time(time: str) -> int:
    dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
    local_dt = pakistan_tz.localize(dt)
    return local_dt.timestamp()
