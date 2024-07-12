from bs4 import BeautifulSoup
from flask import Flask, request, render_template
import requests
from datetime import datetime
import os


app = Flask(__name__)

COURTLISTENER = "https://www.courtlistener.com"

API_URL = "http://0.0.0.0:8080"
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

def get_opinion_count():
    # get opinion count
    try:
        response = requests.get(COUNT_ENDPOINT, headers=headers, timeout=5)
    except requests.exceptions.Timeout:
        return -1
    if response.status_code == 200:
        response_json = response.json()
        if "opinion_count" in response_json:
            return response_json["opinion_count"]
    return -1

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
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
            "k": 10
        }
        response = requests.post(CASE_ENDPOINT, headers=headers, json=params, timeout=90)
        # change this back to send the selected jurisdictions back to the front end
        params['jurisdictions'] = jurisdictions
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
            # get opinion count after search on POST
            opinion_count = get_opinion_count()
            return render_template(
                'index.html',
                results=formatted_opinions,
                form_data=params,
                jurisdictions=JURISDICTIONS,
                opinion_count=opinion_count,
                results_opinion_count=results_opinion_count,
            )
        else:
            return ERROR_MSG
    # get opinion count after search on GET
    opinion_count = get_opinion_count()
    return render_template('index.html', jurisdictions=JURISDICTIONS, opinion_count=opinion_count)

@app.route("/summary/<opinion_id>")
def fetch_summary(opinion_id):
    # Make API call to retrieve AI summary
    response = requests.get(SUMMARY_ENDPOINT, headers=headers, params={"opinion_id": opinion_id})

    if response.status_code == 200:
        summary = response.json()["result"]
        return summary
    else:
        return "Error fetching summary from OPB API", 500
