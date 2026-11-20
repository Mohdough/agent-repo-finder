"""
find_agent_repos.py

Searches GitHub for public projects built with AI agent frameworks
(LangChain, LangGraph, CrewAI, AutoGen) and saves them to a CSV file
you can open in Excel or Google Sheets.

Each row is one repository: its name, owner, star count, last update
date and link. The list is meant for developer-marketing research,
for example finding teams that might want an agent debugging tool.

Run it with:
    python find_agent_repos.py
"""

# ---------------------------------------------------------------------
# 1. IMPORTS: tools this script borrows from Python and from libraries
# ---------------------------------------------------------------------
import csv                                  # writes the spreadsheet (CSV) file
import os                                   # reads environment variables (our token)
import time                                 # lets us pause between requests
from datetime import date, timedelta        # works out "90 days ago"

import requests                             # sends web requests to GitHub's API
from dotenv import load_dotenv              # loads the token from the .env file


# ---------------------------------------------------------------------
# 2. SETTINGS: change these to change what the script looks for
# ---------------------------------------------------------------------
FRAMEWORKS = ["langchain", "langgraph", "crewai", "autogen"]

MIN_STARS = 10               # skip tiny or abandoned experiments
ACTIVE_WITHIN_DAYS = 90      # only repos with code pushed in the last 90 days
RESULTS_PER_FRAMEWORK = 100  # how many repos to collect per framework (GitHub caps search at 1,000)

# The companies that make the frameworks aren't prospects, so skip them.
EXCLUDE_OWNERS = {"langchain-ai", "crewaiinc", "microsoft", "ag2ai"}

OUTPUT_FILE = "agent_repos.csv"

API_URL = "https://api.github.com/search/repositories"
PAUSE_SECONDS = 2            # be polite: GitHub allows about 30 searches per minute


# ---------------------------------------------------------------------
# 3. FUNCTIONS: small, named steps the main program calls in order
# ---------------------------------------------------------------------
def build_headers():
    """Return the HTTP headers GitHub expects, including our token if we have one."""
    load_dotenv()                            # copies the lines in .env into environment variables
    token = os.getenv("GITHUB_TOKEN")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agent-repo-finder",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        print("Warning: no GITHUB_TOKEN found in .env. Running without one (lower rate limits).")
    return headers


def build_query(framework):
    """Turn a framework name into a GitHub search query string."""
    since = date.today() - timedelta(days=ACTIVE_WITHIN_DAYS)
    return (
        f"{framework} in:name,description,topics "
        f"stars:>={MIN_STARS} "
        f"pushed:>={since.isoformat()} "
        f"archived:false"
    )


def search_github(framework, headers):
    """Ask GitHub for repos matching one framework. Returns a list of repo dictionaries."""
    query = build_query(framework)
    print(f"\nSearching for '{framework}' ...")
    print(f"  query: {query}")

    repos = []
    page = 1
    while len(repos) < RESULTS_PER_FRAMEWORK:
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 100,                 # the most GitHub returns per page
            "page": page,
        }
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)

        # Anything other than 200 means something went wrong. Explain it and stop.
        if response.status_code == 401:
            raise SystemExit("GitHub rejected the token (401). Check GITHUB_TOKEN in your .env file.")
        if response.status_code in (403, 429):
            reset = response.headers.get("X-RateLimit-Reset")
            wait = f" Try again after {time.strftime('%H:%M:%S', time.localtime(int(reset)))}." if reset else ""
            raise SystemExit(f"Hit GitHub's rate limit ({response.status_code}).{wait}")
        if response.status_code != 200:
            raise SystemExit(f"GitHub returned an error {response.status_code}: {response.text[:200]}")

        items = response.json().get("items", [])
        if not items:                        # no more results
            break

        repos.extend(items)
        print(f"  page {page}: got {len(items)} repos")
        time.sleep(PAUSE_SECONDS)
        if len(items) < 100:                 # a short page means it was the last one
            break
        page += 1

    return repos[:RESULTS_PER_FRAMEWORK]


def to_row(repo, framework):
    """Keep only the fields we care about from GitHub's large response."""
    description = (repo.get("description") or "").replace("\n", " ").strip()
    return {
        "repo": repo["full_name"],
        "owner": repo["owner"]["login"],
        "owner_type": repo["owner"]["type"],              # "User" or "Organization"
        "stars": repo["stargazers_count"],
        "last_updated": repo["pushed_at"][:10],          # last code push, as YYYY-MM-DD
        "url": repo["html_url"],
        "language": repo.get("language") or "",
        "description": description,
        "frameworks": framework,
    }


def save_csv(rows, filename):
    """Write the rows to a CSV file with a header line."""
    columns = ["repo", "owner", "owner_type", "stars", "last_updated",
               "url", "language", "description", "frameworks"]
    # utf-8-sig makes Excel show accented letters and emoji correctly.
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------
# 4. MAIN PROGRAM: search each framework, merge, sort, save
# ---------------------------------------------------------------------
def main():
    headers = build_headers()
    results = {}                             # key = "owner/repo", value = row; stops duplicates

    for framework in FRAMEWORKS:
        for repo in search_github(framework, headers):
            if repo["owner"]["login"].lower() in EXCLUDE_OWNERS:
                continue
            name = repo["full_name"]
            if name in results:
                # Already found under another framework: note both, keep one row.
                results[name]["frameworks"] += f"; {framework}"
            else:
                results[name] = to_row(repo, framework)

    rows = sorted(results.values(), key=lambda row: row["stars"], reverse=True)
    save_csv(rows, OUTPUT_FILE)

    orgs = sum(1 for row in rows if row["owner_type"] == "Organization")
    print(f"\nDone. Saved {len(rows)} repos ({orgs} owned by organizations) to {OUTPUT_FILE}")


# Run main() only when this file is run directly, not when it is imported.
if __name__ == "__main__":
    main()
