# Agent Repo Finder

A small Python tool that searches GitHub for active open-source projects built with AI agent frameworks (LangChain, LangGraph, CrewAI, AutoGen) and saves them to a spreadsheet.

I built it as a developer-marketing research tool: the output is a ranked list of teams building agents, which is the audience for agent debugging and observability tools like [TraceRoot](https://github.com/traceroot-ai/traceroot).

## What it does

1. Searches the GitHub API once per framework, for repos that mention it in their name, description or topics.
2. Keeps only repos that have at least 10 stars, had code pushed in the last 90 days, and aren't archived.
3. Skips the framework makers' own repos, since they aren't prospects.
4. Merges duplicates (a repo using both LangChain and LangGraph appears once, tagged with both).
5. Sorts by stars and writes `agent_repos.csv`.

## Output

| Column | Meaning |
| --- | --- |
| `repo` | `owner/name` |
| `owner` | GitHub user or organization |
| `owner_type` | `User` or `Organization` (organizations are more likely to be teams) |
| `stars` | Star count |
| `last_updated` | Date of the last code push (YYYY-MM-DD) |
| `url` | Link to the repo |
| `language` | Main programming language |
| `description` | The repo's own one-line description |
| `frameworks` | Which framework searches found it |

## Setup

You need Python 3.10 or newer and a free GitHub account.

```bash
git clone https://github.com/MohDough/agent-repo-finder.git
cd agent-repo-finder
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a GitHub fine-grained personal access token (Settings → Developer settings → Personal access tokens → Fine-grained tokens) with **Public repositories** access and no extra permissions. Then copy `.env.example` to `.env` and paste the token in:

```
GITHUB_TOKEN=github_pat_...
```

## Usage

```bash
python find_agent_repos.py
```

Example output (your numbers will differ):

```
Searching for 'crewai' ...
  query: crewai in:name,description,topics stars:>=10 pushed:>=2026-08-13 archived:false
  page 1: got 100 repos

Done. Saved <N> repos (<M> owned by organizations) to agent_repos.csv
```

## Configuration

Edit the settings at the top of `find_agent_repos.py`:

| Setting | Default | What it controls |
| --- | --- | --- |
| `FRAMEWORKS` | langchain, langgraph, crewai, autogen | Which frameworks to search for |
| `MIN_STARS` | 10 | Minimum stars |
| `ACTIVE_WITHIN_DAYS` | 90 | How recently code must have been pushed |
| `RESULTS_PER_FRAMEWORK` | 100 | Repos collected per framework (GitHub's cap is 1,000) |
| `EXCLUDE_OWNERS` | framework makers | Accounts to skip |

## How it works

- **GitHub REST API:** the script calls the `GET /search/repositories` endpoint with the `requests` library and reads the JSON response.
- **Authentication:** the token is read from a `.env` file with `python-dotenv`, so it never appears in the code or on GitHub.
- **Rate limits:** GitHub allows about 30 authenticated searches per minute, so the script pauses 2 seconds between requests and explains the error if a limit is hit.
- **Pagination:** results come back 100 per page; the script keeps asking for the next page until it has enough.
- **"Last updated":** uses `pushed_at` (last code change) rather than `updated_at`, which also changes when someone stars the repo.

## Limitations

- Matching on name, description and topics finds repos that *say* they use a framework. It misses projects that use one without mentioning it, and includes some tutorials and demos.
- GitHub search returns at most 1,000 results per query.
- Star count is a rough proxy for team size or seriousness.

## Responsible use

This tool collects only public repository information. It doesn't collect email addresses. GitHub's Acceptable Use Policies prohibit using data from its API for spam or unsolicited bulk email, so use the list for research and personal, relevant outreach (for example, opening a helpful issue or engaging in a project's own community channels).

## Ideas for next steps

- Search `requirements.txt` and `pyproject.toml` files with GitHub code search for exact dependency matches.
- Add the number of contributors per repo as a team-size signal.
- Run it weekly with GitHub Actions and track new repos over time.

## License

MIT
