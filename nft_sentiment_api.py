# nft_sentiment_api_lightest.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import requests
import urllib.parse
from textblob import TextBlob

app = FastAPI(title="NFT Sentiment Analyzer API Lightest")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://www.blocnexus.site",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Sentiment analysis
# -----------------------------
HYPE_KEYWORDS = ["surge","record","all-time high","rally","spike","soar","increase","growth","top sales"]
NEGATIVE_KEYWORDS = ["loss","downturn","decline","drop","fall","retreat","decrease","crash"]

def analyze_post_sentiment(text):
    text_lower = text.lower()
    for kw in HYPE_KEYWORDS:
        if kw in text_lower:
            return "HYPE", 1
    for kw in NEGATIVE_KEYWORDS:
        if kw in text_lower:
            return "NEGATIVE", -1

    # TextBlob sentiment (polarity -1 to 1)
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        return "POSITIVE", 0.5
    elif polarity < -0.1:
        return "NEGATIVE", -0.5
    else:
        return "NEUTRAL", 0

# -----------------------------
# Google News scraping
# -----------------------------
def fetch_google_news(nft_name, max_articles=10):
    query = urllib.parse.quote_plus(f"{nft_name} NFT news")
    url = f"https://www.google.com/search?q={query}&tbm=nws"
    headers = {"User-Agent": "Mozilla/5.0"}
    articles = []
    try:
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        for g in soup.select("div.SoaBEf")[:max_articles]:
            title_tag = g.select_one("div:nth-of-type(1) a")
            title = g.get_text(" ", strip=True)
            link = title_tag['href'] if title_tag else url
            if title:
                articles.append({
                    "text": title,
                    "platform": "Google News",
                    "timestamp": None,
                    "source_url": link
                })
    except Exception as e:
        print(f"Error fetching Google News: {e}")
    return articles

# -----------------------------
# Analyze sentiments
# -----------------------------
def analyze_sentiments_texts(posts):
    if not posts:
        return [], {"POSITIVE":0,"NEGATIVE":0,"NEUTRAL":0,"HYPE":0}, "No data 😐"
    scores_count = {"POSITIVE":0,"NEGATIVE":0,"NEUTRAL":0,"HYPE":0}
    for post in posts:
        sentiment, score = analyze_post_sentiment(post["text"])
        post["sentiment"] = sentiment
        post["score"] = score
        scores_count[sentiment] += 1
    total = sum(scores_count.values())
    percentages = {k: round((v/total)*100,1) for k,v in scores_count.items()}
    overall_score = sum(p["score"] for p in posts)
    if overall_score > 2:
        trend = "Hype/Positive 🚀"
    elif overall_score < -2:
        trend = "Negative ⚠️"
    else:
        trend = "Neutral 😐"
    return posts, percentages, trend

# -----------------------------
# API endpoint
# -----------------------------
@app.get("/analyze")
def analyze_nft(nft_name: str = Query(..., description="Name of the NFT")):
    try:
        articles = fetch_google_news(nft_name)
        all_posts = [p for p in articles if len(p["text"])>20]

        if not all_posts:
            return {"error": "No recent data found for this NFT."}

        posts_with_sentiments, percentages, trend = analyze_sentiments_texts(all_posts)

        return {
            "nft_name": nft_name,
            "total_posts": len(posts_with_sentiments),
            "posts": posts_with_sentiments,
            "sentiment_breakdown": percentages,
            "overall_trend": trend
        }
    except Exception as e:
        print(f"Error analyzing NFT {nft_name}: {e}")
        return {"error": "Internal server error. Please try again later."}
