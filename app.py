from flask import Flask, request, render_template
import requests
from datetime import datetime
import os
import re
import time


app = Flask(__name__)

COURTLISTENER = "https://www.courtlistener.com"

API_URL = os.environ["OPB_API_URL"]
CASE_ENDPOINT = API_URL + "/search_opinions"
SUMMARY_ENDPOINT = API_URL + "/get_opinion_summary"
COUNT_ENDPOINT = API_URL + "/get_opinion_count"

JURISDICTIONS = [
    {'display': 'Federal Appellate', 'value': 'us-app'},
    {'display': 'Federal District', 'value': 'us-dis'},
    {'display': 'Federal Supreme Court', 'value': 'us-sup'},
    {'display': 'Federal Special', 'value': 'us-misc'},
    {'display': 'Alabama', 'value': 'al'},
    {'display': 'Alaska', 'value': 'ak'},
    {'display': 'Arizona', 'value': 'az'},
    {'display': 'Arkansas', 'value': 'ar'},
    {'display': 'California', 'value': 'ca'},
    {'display': 'Colorado', 'value': 'co'},
    {'display': 'Connecticut', 'value': 'ct'},
    {'display': 'Delaware', 'value': 'de'},
    {'display': 'District of Columbia', 'value': 'dc'},
    {'display': 'Florida', 'value': 'fl'},
    {'display': 'Georgia', 'value': 'ga'},
    {'display': 'Hawaii', 'value': 'hi'},
    {'display': 'Idaho', 'value': 'id'},
    {'display': 'Illinois', 'value': 'il'},
    {'display': 'Indiana', 'value': 'in'},
    {'display': 'Iowa', 'value': 'ia'},
    {'display': 'Kansas', 'value': 'ks'},
    {'display': 'Kentucky', 'value': 'ky'},
    {'display': 'Louisiana', 'value': 'la'},
    {'display': 'Maine', 'value': 'me'},
    {'display': 'Maryland', 'value': 'md'},
    {'display': 'Massachusetts', 'value': 'ma'},
    {'display': 'Michigan', 'value': 'mi'},
    {'display': 'Minnesota', 'value': 'mn'},
    {'display': 'Mississippi', 'value': 'ms'},
    {'display': 'Missouri', 'value': 'mo'},
    {'display': 'Montana', 'value': 'mt'},
    {'display': 'Nebraska', 'value': 'ne'},
    {'display': 'Nevada', 'value': 'nv'},
    {'display': 'New Hampshire', 'value': 'nh'},
    {'display': 'New Jersey', 'value': 'nj'},
    {'display': 'New Mexico', 'value': 'nm'},
    {'display': 'New York', 'value': 'ny'},
    {'display': 'North Carolina', 'value': 'nc'},
    {'display': 'North Dakota', 'value': 'nd'},
    {'display': 'Ohio', 'value': 'oh'},
    {'display': 'Oklahoma', 'value': 'ok'},
    {'display': 'Oregon', 'value': 'or'},
    {'display': 'Pennsylvania', 'value': 'pa'},
    {'display': 'Rhode Island', 'value': 'ri'},
    {'display': 'South Carolina', 'value': 'sc'},
    {'display': 'South Dakota', 'value': 'sd'},
    {'display': 'Tennessee', 'value': 'tn'},
    {'display': 'Texas', 'value': 'tx'},
    {'display': 'Utah', 'value': 'ut'},
    {'display': 'Vermont', 'value': 'vt'},
    {'display': 'Virginia', 'value': 'va'},
    {'display': 'Washington', 'value': 'wa'},
    {'display': 'West Virginia', 'value': 'wv'},
    {'display': 'Wisconsin', 'value': 'wi'},
    {'display': 'Wyoming', 'value': 'wy'}
]

API_KEY = os.environ["OPB_TEST_API_KEY"]
headers = {"X-API-KEY": API_KEY}
ERROR_MSG = "Error searching for opinions. Please try again later."

class Opinion:

    def __init__(
        self, opinion_id: int, case_name: str, court_name: str, author_name: str, ai_summary: str,
        text: str, date_filed: str, url: str, date_blocked: str, other_dates: str, summary: str,
        download_url: str, match_score: float
    ) -> None:
        self.opinion_id = opinion_id
        self.case_name = case_name
        self.court_name = court_name
        self.author_name = author_name
        self.ai_summary = ai_summary
        self.text = text
        self.date_filed = date_filed
        self.url = url
        self.date_blocked = date_blocked
        self.other_dates = other_dates
        self.summary = summary
        self.download_url = download_url
        self.match_score = match_score


def format_str(text: str) -> str:
    """Replace '\\n\\n' and with <br> and ¶ with '<br>¶'."""
    def replace_with_br(match):
        return f'<br>{match.group(0)}'

    pattern = r'\s(\S*¶\S*)'
    # \s matches any whitespace character
    # (\S*¶\S*) is a capture group that matches:
    #   - \S* : zero or more non-whitespace characters
    #   - ¶ : the paragraph character
    return re.sub(pattern, replace_with_br, text.replace("\n\n","<br>"))

def mark_keyword(text, keyword):
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    
    def replace_func(match):
        return f'<mark>{match.group()}</mark>'
    
    return pattern.sub(replace_func, text)

def format_summary(summary):
    # Split the summary into lines
    lines = summary.split('- ')
    
    # Process each line
    formatted_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if the line starts with a title (wrapped in asterisks)
        if re.match(r'^\*\*.*\*\*', line):
            # Replace asterisks with HTML strong tags
            line = re.sub(r'^\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
            formatted_lines.append(line)
        else:
            # For non-title lines, just add the line
            formatted_lines.append(" - " + line)
    
    # Join the lines with line breaks
    formatted_content = '<br>'.join(formatted_lines)
    
    # Wrap everything in a single paragraph tag
    return f'<p>{formatted_content}</p>'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start = time.time()
        keyword = request.form.get('keyword')
        semantic = request.form.get('semantic')
        before_date = request.form.get('before_date')
        after_date = request.form.get('after_date')
        jurisdictions = request.form.getlist('jurisdictions')
        req_jurisdics = jurisdictions
        if len(jurisdictions) == len(JURISDICTIONS):
            # all jurisdictions, dont use a filter
            req_jurisdics = None
        params = {
            "keyword_query": keyword,
            "query": semantic,
            "before_date": before_date,
            "after_date": after_date,
            "jurisdictions": req_jurisdics,
            "k": 100
        }
        response = requests.post(CASE_ENDPOINT, headers=headers, json=params, timeout=90)
        # change this back to send the selected jurisdictions back to the front end
        params["jurisdictions"] = jurisdictions
        if response.status_code == 200:
            response_json = response.json()
            if "results" not in response_json:
                return ERROR_MSG
            opinions = response_json["results"]
            # get results_opinion_count
            opinion_ids = set()
            for opinion in opinions:
                if opinion["entity"]["metadata"]["id"] not in opinion_ids:
                    opinion_ids.add(opinion["entity"]["metadata"]["id"])
            results_opinion_count = len(opinion_ids)
            # format opinions
            formatted_opinions = []
            for opinion in opinions:
                match_score = round(max([0, (2 - opinion['distance']) / 2]), 5)
                metadata = opinion["entity"]["metadata"]
                case_name = metadata["case_name"]
                if len(case_name) > 200:
                    case_name = case_name[:200] + "..."
                court_name = metadata["court_name"]
                author_name = metadata["author_name"] if "author_name" in metadata else None
                ai_summary = format_summary(metadata["ai_summary"]) if "ai_summary" in metadata else None
                # CL summary
                summary = metadata["summary"] if "summary" in metadata else None
                download_url = metadata["download_url"] if "download_url" in metadata else None
                # matched excerpt
                text = format_str(opinion["entity"]["text"])
                text = f"""<p>{text}</p>"""
                if keyword:
                    text = mark_keyword(text, keyword)
                # full text link
                if "slug" in metadata:
                    url = COURTLISTENER + f"/opinion/{metadata['cluster_id']}/{metadata['slug']}/"
                elif "absolute_url" in metadata:
                    url = COURTLISTENER + metadata["absolute_url"]
                else:
                    url = None
                # dates
                date_filed = datetime.strptime(metadata["date_filed"], "%Y-%m-%d").strftime("%B %d, %Y")
                other_dates = metadata["other_dates"] if "other_dates" in metadata else None
                if "date_blocked" in metadata:
                    date_blocked = datetime.strptime(metadata["date_blocked"], "%Y-%m-%d").strftime("%B %d, %Y")
                else:
                    date_blocked = None
                formatted_opinions.append(Opinion(**{
                    "opinion_id": metadata["id"],
                    "case_name": case_name,
                    "court_name": court_name,
                    "author_name": author_name,
                    "ai_summary": ai_summary,
                    "text": text,
                    "date_filed": date_filed,
                    "url": url,
                    "download_url": download_url,
                    "date_blocked": date_blocked,
                    "other_dates": other_dates,
                    "summary": summary,
                    "match_score": match_score,
                }))
            end = time.time()
            elapsed = str(round(end - start, 5))
            return render_template(
                "index.html",
                results=formatted_opinions,
                form_data=params,
                jurisdictions=JURISDICTIONS,
                results_opinion_count=results_opinion_count,
                elapsed=elapsed,
            )
        else:
            return ERROR_MSG
    return render_template("index.html", jurisdictions=JURISDICTIONS)


@app.route("/opinion_count")
def get_opinion_count() -> int:
    try:
        response = requests.get(COUNT_ENDPOINT, headers=headers, timeout=90)
    except requests.exceptions.Timeout:
        return {"message": "Failure: timeout"}
    if response.status_code == 200:
        response_json = response.json()
        if "opinion_count" in response_json:
            return {"message": "Success", "opinion_count": response_json["opinion_count"]}
    return {"message": "Failure: exception in request or bad response code"}


@app.route("/summary/<opinion_id>")
def fetch_summary(opinion_id):
    # Make API call to retrieve AI summary
    response = requests.get(SUMMARY_ENDPOINT, headers=headers, params={"opinion_id": opinion_id})

    if response.status_code == 200:
        response_json = response.json()
        if "result" not in response_json:
            return "Error fetching summary from OPB API", 500
        summary = response_json["result"]
        return format_summary(summary)
    else:
        return "Error fetching summary from OPB API", 500
