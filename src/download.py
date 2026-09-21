"""Download the three datasets into data/raw/.

1. Stack Overflow new questions per month, 2018-2026 (Stack Exchange API)
2. ChatGPT weekly active users (OpenAI announcements, compiled by hand)
3. Stack Overflow Developer Survey 2023-2025
4. Questions per tag, before vs. after ChatGPT (Stack Exchange API)
5. Stack Overflow answers per month, 2018-2026 (Stack Exchange API)
6. The questions themselves, one month before ChatGPT and one month now (Stack Exchange API)
"""
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def download_stackoverflow_questions():
    """Dataset 1: how many new questions Stack Overflow got each month, 2018-01 to 2026-08.

    Source: Stack Exchange API, 104 requests. Needs a free key from stackapps.com in .env.
    Saves data/raw/stackoverflow_monthly_questions.csv.
    """
    rows = []
    for month in pd.date_range("2018-01-01", "2026-08-01", freq="MS"):
        next_month = month + pd.DateOffset(months=1)
        params = {
            "site": "stackoverflow",
            "fromdate": int(month.timestamp()),
            "todate": int(next_month.timestamp()) - 1,
            "sort": "creation",
            "filter": "total",
        }
        if os.getenv("STACKEXCHANGE_KEY"):
            params["key"] = os.environ["STACKEXCHANGE_KEY"]
        data = requests.get("https://api.stackexchange.com/2.3/questions", params=params).json()
        if "total" not in data:
            print(f"Stack Exchange API stopped: {data['error_message']}")
            return
        rows.append({"month": month.date(), "questions": data["total"]})
    pd.DataFrame(rows).to_csv(RAW / "stackoverflow_monthly_questions.csv", index=False)
    print("saved stackoverflow_monthly_questions.csv")


def save_chatgpt_weekly_users():
    """Dataset 2: ChatGPT weekly active users (millions), from OpenAI's public announcements.

    OpenAI publishes no downloadable dataset, so these were compiled by hand. Each row keeps its
    source and how the number was phrased ("about", "more than", "on track for").
    Saves data/raw/chatgpt_weekly_users.csv.
    """
    rows = [
        ("2023-11-06", 100, "about", "https://techcrunch.com/2023/11/06/openais-chatgpt-now-has-100-million-weekly-active-users/"),
        ("2024-08-29", 200, "more than", "https://www.axios.com/2024/08/29/openai-chatgpt-200-million-weekly-active-users"),
        ("2024-10-29", 250, "about", "https://finance.yahoo.com/news/openai-cfo-says-75-revenue-175831132.html"),
        ("2024-12-04", 300, "about", "https://www.cnbc.com/2024/12/04/openais-active-user-count-soars-to-300-million-people-per-week.html"),
        ("2025-02-20", 400, "more than", "https://x.com/bradlightcap/status/1892579908179882057"),
        ("2025-03-31", 500, "about", "https://openai.com/index/march-funding-updates/"),
        ("2025-08-04", 700, "on track for", "https://techcrunch.com/2025/08/04/openai-says-chatgpt-is-on-track-to-reach-700m-weekly-users/"),
        ("2025-10-06", 800, "more than", "https://techcrunch.com/2025/10/06/sam-altman-says-chatgpt-has-hit-800m-weekly-active-users/"),
        ("2026-02-27", 900, "more than", "https://openai.com/index/scaling-ai-for-everyone/"),
        ("2026-03-31", 900, "more than", "https://openai.com/index/accelerating-the-next-phase-ai/"),
        ("2026-08-31", 1000, "more than", "https://openai.com/index/expanding-access-to-ai-with-chatgpt-ads/"),
    ]
    df = pd.DataFrame(rows, columns=["date", "weekly_users_millions", "qualifier", "source"])
    df.to_csv(RAW / "chatgpt_weekly_users.csv", index=False)
    print("saved chatgpt_weekly_users.csv")


def download_developer_survey():
    """Dataset 3: Stack Overflow Developer Survey 2023-2025 (AI use, Stack Overflow visits, languages).

    Source: github.com/StackExchange/Survey, about 150 MB per year.
    Saves data/raw/survey/survey_<year>_results.csv.
    """
    url ="https://media.githubusercontent.com/media/StackExchange/Survey/main/packages/archive/{year}/results.csv"
    for year in [2023, 2024, 2025]:
        path = RAW / "survey" / f"survey_{year}_results.csv"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(requests.get(url.format(year=year)).content)
        print(f"saved survey/{path.name}")


def download_tag_survival():
    """Dataset 4: how many questions each popular tag got before vs. after ChatGPT.

    Windows are Sep 2021 - Aug 2022 and the same twelve months three years later.
    Source: Stack Exchange API, 201 requests. Saves data/raw/stackoverflow_tag_survival.csv.
    """
    key = os.getenv("STACKEXCHANGE_KEY")
    tags = requests.get("https://api.stackexchange.com/2.3/tags", params={
        "site": "stackoverflow", "order": "desc", "sort": "popular", "pagesize": 100, "key": key,
    }).json()["items"]
    tags = sorted(tags, key=lambda tag: -tag["count"])  # this endpoint returns the page alphabetically

    windows = {"pre": ("2021-09-01", "2022-09-01"), "post": ("2025-09-01", "2026-09-01")}
    rows = []
    for tag in tags:
        counts = {}
        for window, (start, end) in windows.items():
            data = requests.get("https://api.stackexchange.com/2.3/questions", params={
                "site": "stackoverflow",
                "tagged": tag["name"],
                "fromdate": int(pd.Timestamp(start).timestamp()),
                "todate": int(pd.Timestamp(end).timestamp()) - 1,
                "sort": "creation",
                "filter": "total",
                "key": key,
            }).json()
            counts[window] = data["total"]
        rows.append({"tag": tag["name"], "pre": counts["pre"], "post": counts["post"]})
    pd.DataFrame(rows).to_csv(RAW / "stackoverflow_tag_survival.csv", index=False)
    print(f"saved stackoverflow_tag_survival.csv ({len(rows)} tags)")


def download_monthly_answers():
    """Dataset 5: how many answers were written each month, 2018-01 to 2026-08.

    Same months as the question counts, so the two can be compared side by side.
    Source: Stack Exchange API, 104 requests. Saves data/raw/stackoverflow_monthly_answers.csv.
    """
    rows = []
    for month in pd.date_range("2018-01-01", "2026-08-01", freq="MS"):
        next_month = month + pd.DateOffset(months=1)
        data = requests.get("https://api.stackexchange.com/2.3/answers", params={
            "site": "stackoverflow",
            "fromdate": int(month.timestamp()),
            "todate": int(next_month.timestamp()) - 1,
            "sort": "creation",
            "filter": "total",
            "key": os.getenv("STACKEXCHANGE_KEY"),
        }).json()
        rows.append({"month": month.date(), "answers": data["total"]})
    pd.DataFrame(rows).to_csv(RAW / "stackoverflow_monthly_answers.csv", index=False)
    print("saved stackoverflow_monthly_answers.csv")


def download_question_samples():
    """Dataset 6: the questions themselves, one month before ChatGPT and one month now.

    Titles and tags for August 2022 (first 300) and August 2026 (all of them), so we can see what
    kind of question is left. Source: Stack Exchange API, about 15 requests.
    Saves data/raw/stackoverflow_question_samples.csv.
    """
    rows = []
    for month, pages in [("2022-08-01", 3), ("2026-08-01", 12)]:
        start = pd.Timestamp(month)
        for page in range(1, pages + 1):
            data = requests.get("https://api.stackexchange.com/2.3/questions", params={
                "site": "stackoverflow",
                "fromdate": int(start.timestamp()),
                "todate": int((start + pd.DateOffset(months=1)).timestamp()) - 1,
                "sort": "creation",
                "order": "asc",
                "page": page,
                "pagesize": 100,
                "key": os.getenv("STACKEXCHANGE_KEY"),
            }).json()
            for question in data["items"]:
                rows.append({"month": start.date(), "title": question["title"],
                             "tags": ";".join(question["tags"])})
            if not data["has_more"]:
                break
    pd.DataFrame(rows).to_csv(RAW / "stackoverflow_question_samples.csv", index=False)
    print(f"saved stackoverflow_question_samples.csv ({len(rows)} questions)")


if __name__ == "__main__":
    download_stackoverflow_questions()
    save_chatgpt_weekly_users()
    download_developer_survey()
    # download_tag_survival()
    # download_monthly_answers()
    # download_question_samples()
