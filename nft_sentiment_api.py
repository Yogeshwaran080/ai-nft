# nft_sentiment_api_newsapi_detailed.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from textblob import TextBlob
from datetime import datetime

NEWSAPI_KEY = "d726131aa90544af841b81087e9f3e9a"

app = FastAPI(title="NFT Sentiment Analyzer API (NewsAPI Detailed)")

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
    """
    Returns sentiment category and score:
    HYPE: +1, POSITIVE: +0.5, NEUTRAL: 0, NEGATIVE: -0.5, NEGATIVE/HYPE from keywords: -1/1
    """
    text_lower = text.lower()
    for kw in HYPE_KEYWORDS:
        if kw in text_lower:
            return "HYPE", 1
    for kw in NEGATIVE_KEYWORDS:
        if kw in text_lower:
            return "NEGATIVE", -1

    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        return "POSITIVE", 0.5
    elif polarity < -0.1:
        return "NEGATIVE", -0.5
    else:
        return "NEUTRAL", 0

# -----------------------------
# Fetch news using NewsAPI (detailed, specific NFT)
# -----------------------------
def fetch_newsapi_articles(nft_name: str, max_articles: int = 20):
    """
    Fetch latest news articles about a specific NFT using NewsAPI.
    Returns list of articles with text, platform, timestamp, source_url
    """
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f'"{nft_name}" NFT',  # exact phrase search using quotes
        "language": "en",
        "pageSize": max_articles,
        "sortBy": "publishedAt",
        "apiKey": NEWSAPI_KEY
    }

    articles = []
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("status") != "ok":
            print(f"NewsAPI error: {data.get('message')}")
            return []

        for item in data.get("articles", []):
            # Convert timestamp to readable format
            ts = item.get("publishedAt")
            if ts:
                try:
                    ts = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")
                except:
                    pass

            articles.append({
                "text": item.get("title") or "",
                "description": item.get("description") or "",
                "platform": item.get("source", {}).get("name", "NewsAPI"),
                "timestamp": ts,
                "source_url": item.get("url")
            })
    except Exception as e:
        print(f"Error fetching NewsAPI articles: {e}")
    return articles

# -----------------------------
# Analyze multiple posts
# -----------------------------
def analyze_sentiments_texts(posts):
    """
    Adds sentiment & score to each post, calculates overall trend & breakdown
    """
    if not posts:
        return [], {"POSITIVE":0,"NEGATIVE":0,"NEUTRAL":0,"HYPE":0}, "No data 😐"

    scores_count = {"POSITIVE":0,"NEGATIVE":0,"NEUTRAL":0,"HYPE":0}
    for post in posts:
        sentiment, score = analyze_post_sentiment(post["text"] + " " + post.get("description", ""))
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
def analyze_nft(nft_name: str = Query(..., description="Exact name of the NFT")):
    """
    Analyze NFT news sentiment using NewsAPI
    Returns detailed posts, sentiment breakdown & overall trend
    """
    try:
        articles = fetch_newsapi_articles(nft_name, max_articles=20)
        all_posts = [p for p in articles if len(p["text"])>20]

        if not all_posts:
            return {"error": f"No recent data found for '{nft_name}'."}

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
