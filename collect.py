import json
import requests
import os

def collect(handle, incremental = True):
    submissions = []
    try:
        with open(f"data/{handle}_submissions.json", "r") as f:
            submissions = json.load(f)
        print(f"Found {len(submissions)} submissions for {handle}")
    except FileNotFoundError:
        print(f"Found no existing submissions for {handle}")

    if incremental: 
        from_index = len(submissions) + 1
        count = 9999
    else:
        from_index = 1
        count = 9999
    url = f"https://codeforces.com/api/user.status?handle={handle}&from={from_index}&count={count}"
    response = requests.get(url)
    data = response.json()

    if data["status"] == "OK":
        if incremental:
            submissions.extend(data["result"])
        else:
            submissions = data["result"]
        print(f"Found {len(data["result"])} new submissions for {handle}")
        with open(f"data/{handle}_submissions.json", "w") as f:
            json.dump(submissions, f, indent=4)
    else:
        print("API Error: ", data)
        raise RuntimeError
    
    url = f"https://codeforces.com/api/user.rating?handle={handle}"

    response = requests.get(url)
    data = response.json()

    if data["status"] == "OK":
        print(f"Found {len(data["result"])} rating change stats for {handle}")
        with open(f"data/{handle}_rating.json", "w") as f:
            json.dump(data["result"], f, indent=4)
    else:
        print(f"API Error: ", data)
        raise RuntimeError
    

def fetch_contests():
    url = "https://codeforces.com/api/contest.list"
    response = requests.get(url)
    data = response.json()
    if data["status"] == "OK":
        print(f"Found {len(data["result"])} contests")
        with open("data/contests.json", "w") as f:
            json.dump(data["result"], f, indent=4)
    else:
        print(f"API Error: ", data)
        raise RuntimeError


if __name__ == "__main__":
    handles = []
    os.makedirs("data", exist_ok=True)
    with open("users.txt", "r") as f:
        handles = [line.split(',')[-1].strip() for line in f if line.strip()]
    fetch_contests()
    print(f"Fetching submissions for {len(handles)} handles")
    for handle in handles:
        collect(handle, incremental = False)


