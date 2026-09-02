import os
import re
import json
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
import phonenumbers
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from openai import OpenAI

load_dotenv()

app = FastAPI(
    title="Company Intelligence API",
    version="1.0.0"
)

# Comma-separated list of allowed frontend origins. Defaults to local dev;
# set ALLOWED_ORIGINS in production to your deployed frontend URL(s), e.g.
# "https://your-app.vercel.app,http://localhost:3000"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/151.0 Safari/537.36 "
        "CompanyIntelligenceBot/1.0"
    )
}

MAX_PAGES = 15
MAX_TEXT_PER_PAGE = 12000
CRAWL_DELAY_SECONDS = 0.3
PHONE_REGIONS = ("US", "GB", "NL")


class AnalyzeRequest(BaseModel):
    url: HttpUrl


def normalize_url(url: str) -> str:
    url = str(url).strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url.rstrip("/")


def get_domain(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def get_robot_parser(base_url: str) -> RobotFileParser:
    """Fetch and parse robots.txt for the target site.

    If robots.txt can't be read, we fail open (allow crawling) since
    an unreadable robots.txt shouldn't block a legitimate MVP crawl -
    this matches how most well-behaved crawlers handle a missing file.
    """
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        parser.read()
    except Exception:
        pass

    return parser


def fetch_page(url: str):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=True
        )

        content_type = response.headers.get("content-type", "")

        if response.status_code >= 400:
            return None

        if "text/html" not in content_type:
            return None

        return response.text

    except requests.RequestException as exc:
        print(f"[fetch] skipped {url}: {exc}")
        return None


def clean_text(soup: BeautifulSoup) -> str:
    for element in soup([
        "script",
        "style",
        "noscript",
        "svg",
        "iframe"
    ]):
        element.decompose()

    text = soup.get_text(
        separator=" ",
        strip=True
    )

    text = re.sub(r"\s+", " ", text)

    return text[:MAX_TEXT_PER_PAGE]


def extract_emails(text: str):
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    emails = re.findall(pattern, text)

    return sorted(set(emails))


def extract_phones(text: str):
    """Extract phone numbers using Google's libphonenumber (via the
    `phonenumbers` package) instead of a raw digit-matching regex.

    A permissive regex tends to also match dates, zip codes, and other
    digit runs that happen to be 7-15 digits long. PhoneNumberMatcher
    validates candidates against real numbering-plan rules, so it's far
    more precise. We try a few default regions so that both
    internationally-formatted numbers (+31 ...) and locally-formatted
    ones (e.g. a Dutch or UK number with no country code) get picked up.
    """
    found = {}

    for region in PHONE_REGIONS:
        try:
            matches = phonenumbers.PhoneNumberMatcher(text, region)
        except Exception:
            continue

        for match in matches:
            if not phonenumbers.is_valid_number(match.number):
                continue

            e164 = phonenumbers.format_number(
                match.number,
                phonenumbers.PhoneNumberFormat.E164
            )

            if e164 not in found:
                found[e164] = phonenumbers.format_number(
                    match.number,
                    phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )

    return sorted(found.values())


def extract_social_links(soup: BeautifulSoup):
    social = {
        "linkedin": [],
        "instagram": [],
        "facebook": [],
        "twitter": [],
        "youtube": [],
        "tiktok": [],
        "github": [],
        "pinterest": []
    }

    for link in soup.find_all("a", href=True):
        href = link.get("href", "").strip()

        lower = href.lower()

        if "linkedin.com" in lower:
            social["linkedin"].append(href)

        elif "instagram.com" in lower:
            social["instagram"].append(href)

        elif "facebook.com" in lower:
            social["facebook"].append(href)

        elif "twitter.com" in lower or "x.com" in lower:
            social["twitter"].append(href)

        elif "youtube.com" in lower:
            social["youtube"].append(href)

        elif "tiktok.com" in lower:
            social["tiktok"].append(href)

        elif "github.com" in lower:
            social["github"].append(href)

        elif "pinterest.com" in lower:
            social["pinterest"].append(href)

    for key in social:
        social[key] = sorted(set(social[key]))

    return social


def discover_links(base_url: str, soup: BeautifulSoup):
    base_domain = get_domain(base_url)

    links = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")

        if not href:
            continue

        absolute = urljoin(base_url, href)

        parsed = urlparse(absolute)

        if parsed.scheme not in ["http", "https"]:
            continue

        if get_domain(absolute) != base_domain:
            continue

        clean = absolute.split("#")[0].rstrip("/")

        if clean not in links:
            links.append(clean)

    return links


def score_page(url: str):
    path = urlparse(url).path.lower()

    keywords = {
        "about": 10,
        "company": 9,
        "contact": 10,
        "team": 8,
        "leadership": 8,
        "services": 7,
        "products": 7,
        "careers": 7,
        "jobs": 7,
        "location": 6,
        "locations": 6,
        "history": 5,
        "news": 4,
        "blog": 3
    }

    score = 0

    for keyword, points in keywords.items():
        if keyword in path:
            score += points

    return score


def crawl_website(start_url: str):
    start_url = normalize_url(start_url)
    robots = get_robot_parser(start_url)

    visited = set()
    queue = [start_url]

    pages = []

    while queue and len(pages) < MAX_PAGES:

        current_url = queue.pop(0)

        if current_url in visited:
            continue

        visited.add(current_url)

        if not robots.can_fetch(HEADERS["User-Agent"], current_url):
            print(f"[robots] disallowed, skipping {current_url}")
            continue

        html = fetch_page(current_url)

        time.sleep(CRAWL_DELAY_SECONDS)

        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")

        text = clean_text(soup)

        social = extract_social_links(soup)

        page_text = soup.get_text(" ", strip=True)
        emails = extract_emails(page_text)
        phones = extract_phones(page_text)

        pages.append({
            "url": current_url,
            "title": (
                soup.title.get_text(strip=True)
                if soup.title
                else ""
            ),
            "text": text,
            "emails": emails,
            "phones": phones,
            "social": social
        })

        links = discover_links(
            start_url,
            soup
        )

        links.sort(
            key=score_page,
            reverse=True
        )

        for link in links:
            if link not in visited and link not in queue:
                queue.append(link)

    return pages


def combine_socials(pages):
    result = {
        "linkedin": [],
        "instagram": [],
        "facebook": [],
        "twitter": [],
        "youtube": [],
        "tiktok": [],
        "github": [],
        "pinterest": []
    }

    for page in pages:
        for platform, links in page["social"].items():
            result[platform].extend(links)

    for platform in result:
        result[platform] = sorted(
            set(result[platform])
        )

    return result


def combine_emails(pages):
    emails = []

    for page in pages:
        emails.extend(page["emails"])

    return sorted(set(emails))


def combine_phones(pages):
    phones = []

    for page in pages:
        phones.extend(page["phones"])

    return sorted(set(phones))


def prepare_ai_context(pages):
    context = []

    for page in pages:
        context.append(
            f"""
PAGE URL:
{page['url']}

PAGE TITLE:
{page['title']}

PAGE TEXT:
{page['text']}
"""
        )

    return "\n\n".join(context)


def analyze_with_ai(pages):
    context = prepare_ai_context(pages)

    schema = {
        "company_name": None,
        "legal_name": None,
        "industry": None,
        "company_category": None,
        "description": None,
        "founded_year": None,
        "employee_count": None,
        "employee_range": None,
        "company_type": None,

        "headquarters": None,
        "locations": [],

        "emails": [],
        "phone_numbers": [],

        "social_media": {
            "linkedin": [],
            "instagram": [],
            "facebook": [],
            "twitter": [],
            "youtube": [],
            "tiktok": [],
            "github": [],
            "pinterest": []
        },

        "services": [],
        "products": [],
        "industries_served": [],

        "founders": [],
        "ceo": None,
        "leadership": [],

        "contact_page": None,
        "about_page": None,
        "careers_page": None,

        "certifications": [],
        "awards": [],
        "clients": [],
        "partners": [],

        "technologies": [],
        "markets": [],

        "additional_information": []
    }

    prompt = f"""
You are a company intelligence extraction system.

Analyze the website content below.

Extract ONLY information that is actually supported
by the supplied website content.

DO NOT invent information.

If something is not available, return null or [].

Employee count must only be returned when explicitly
mentioned or clearly stated.

For every important piece of information, prefer the
exact public website source page when possible.

Return valid JSON matching this structure:

{json.dumps(schema, indent=2)}

WEBSITE CONTENT:

{context}
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt
    )

    output = response.output_text

    try:
        return json.loads(output)

    except json.JSONDecodeError:

        cleaned = output.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(
                r"^```(?:json)?",
                "",
                cleaned
            )

            cleaned = re.sub(
                r"```$",
                "",
                cleaned
            )

        return json.loads(cleaned)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Company Intelligence API"
    }


@app.post("/analyze")
def analyze_company(request: AnalyzeRequest):

    url = normalize_url(str(request.url))

    pages = crawl_website(url)

    if not pages:
        raise HTTPException(
            status_code=400,
            detail="Could not access or crawl this website."
        )

    emails = combine_emails(pages)
    phones = combine_phones(pages)
    socials = combine_socials(pages)

    ai_data = analyze_with_ai(pages)

    if not ai_data.get("emails"):
        ai_data["emails"] = emails

    if not ai_data.get("phone_numbers"):
        ai_data["phone_numbers"] = phones

    for platform in socials:

        if not ai_data["social_media"].get(platform):
            ai_data["social_media"][platform] = socials[platform]

    return {
        "success": True,
        "website": url,
        "pages_analyzed": len(pages),
        "company": ai_data,
        "sources": [
            {
                "url": page["url"],
                "title": page["title"]
            }
            for page in pages
        ]
    }
