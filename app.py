from bs4 import BeautifulSoup
from flask import Flask, request, render_template
import requests
from datetime import datetime
import os


app = Flask(__name__)

COURTLISTENER = "https://www.courtlistener.com"

# API endpoint for searching cases
CASE_API_ENDPOINT = "http://0.0.0.0:8080/search_opinions"

# API endpoint for fetching AI summaries
SUMMARY_API_ENDPOINT = "http://0.0.0.0:8080/get_opinion_summary"

API_KEY = os.environ["OPB_TEST_API_KEY"]
headers = {"X-API-KEY": API_KEY}

@app.route("/")
def index():
    return render_template("index.html")

class Opinion:

    def __init__(self, opinion_id: int, case_name: str, court_name: str, author_name: str, ai_summary: str, text: str, date_filed: str, url: str, match_score: float) -> None:
        self.opinion_id = opinion_id
        self.case_name = case_name
        self.court_name = court_name
        self.author_name = author_name
        self.ai_summary = ai_summary
        self.text = text
        self.date_filed = date_filed
        self.url = url
        self.match_score = match_score

@app.route("/search", methods=["POST"])
def search():
    keyword = request.form["keyword"]
    semantic_query = request.form["semantic_query"]
    before_date = request.form["before_date"]
    after_date = request.form["after_date"]
    jurisdiction = request.form["jurisdiction"]
    jurisdiction = jurisdiction.lower() if jurisdiction != "All" else None

    # Make API call to retrieve cases
    response = requests.get(CASE_API_ENDPOINT, headers=headers, params={
        "keyword_query": keyword,
        "query": semantic_query,
        "before_date": before_date,
        "after_date": after_date,
        "jurisdiction": jurisdiction,
        "k": 10
    })

    if response.status_code == 200:
        opinions = response.json()["results"]
        formatted_opinions = []
        for opinion in opinions:
            match_score = round(max([0, (2 - opinion['distance']) / 2]), 5)
            # case name
            if "case_name" in opinion["entity"]["metadata"]:
                case_name = opinion["entity"]["metadata"]["case_name"]
                if len(case_name) > 200:
                    case_name = case_name[:200] + "..."
            else:
                case_name = "Unknown Case"
            # court name
            if "court_name" in opinion["entity"]["metadata"]:
                court_name = opinion["entity"]["metadata"]["court_name"]
            else:
                court_name = "Unknown Court"
            # author name
            if "author_name" in opinion["entity"]["metadata"]:
                author_name = opinion["entity"]["metadata"]["author_name"]
            elif "author_str" in opinion["entity"]["metadata"]:
                author_name = opinion["entity"]["metadata"]["author_str"]
            else:
                author_name = "Unknown Author"
            # AI summary
            if "ai_summary" in opinion["entity"]["metadata"]:
                ai_summary = opinion["entity"]["metadata"]["ai_summary"]
            else:
                ai_summary = "unavailable"
            # matched excerpt and full text link
            if opinion["source"] == "courtlistener":
                text = BeautifulSoup(opinion["entity"]["text"], features="html.parser")
                for link in text.find_all("a"):
                    if "href" in link.attrs:
                        href = link.attrs["href"]
                    if href.startswith("/"):
                        href = COURTLISTENER + href
                        link.attrs["href"] = href
                text = text.prettify()
                url = COURTLISTENER + opinion["entity"]["metadata"]["absolute_url"]
            else: # cap
                text = f"""<p>{opinion["entity"]["text"]}</p>"""
                url = "unavailable"
            # date filed
            date_filed = datetime.strptime(opinion["entity"]["metadata"]["date_filed"], "%Y-%m-%d")
            date_filed = date_filed.strftime("%B %d, %Y")
            formatted_opinions.append(Opinion(**{
                "opinion_id": opinion["entity"]["metadata"]["id"],
                "case_name": case_name,
                "court_name": court_name,
                "author_name": author_name,
                "ai_summary": ai_summary,
                "text": text,
                "date_filed": date_filed,
                "url": url,
                "match_score": match_score,
            }))
        return render_template("results.html", opinions=formatted_opinions)
    else:
        return "Error searching for opinions"

@app.route("/summary/<opinion_id>")
def fetch_summary(opinion_id):
    # Make API call to retrieve AI summary
    response = requests.get(SUMMARY_API_ENDPOINT, headers=headers, params={"opinion_id": opinion_id})

    if response.status_code == 200:
        summary = response.json()["result"]
        return summary
    else:
        return "Error fetching summary from OPB API", 500

if __name__ == "__main__":
    app.run(debug=True)