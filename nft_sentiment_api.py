# nft_sentiment_api_fast.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from transformers import pipeline
import urllib.parse
import time
import random

app = FastAPI(title="NFT Sentiment Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",        # for local development
        "https://www.blocnexus.site",   # your deployed frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


sentiment_model = pipeline("sentiment-analysis")

# -----------------------------
# Selenium driver
# -----------------------------
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

# -----------------------------
# Google News scraping
# -----------------------------
def fetch_google_news(nft_name, max_pages=3):
    driver = create_driver()
    articles = []
    try:
        for page in range(max_pages):
            start = page * 10
            query = urllib.parse.quote_plus(f"{nft_name} NFT news")
            url = f"https://www.google.com/search?q={query}&tbm=nws&start={start}"
            try:
                driver.get(url)
                time.sleep(random.uniform(1, 2))  # reduce sleep for speed
                soup = BeautifulSoup(driver.page_source, "html.parser")
                for g in soup.select("div.SoaBEf"):
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
                print(f"Google News page {page} failed: {e}")
    finally:
        driver.quit()
    return articles

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
    result = sentiment_model(text)[0]
    label = result["label"].upper()
    if label == "POSITIVE":
        return "POSITIVE", 0.5
    elif label == "NEGATIVE":
        return "NEGATIVE", -0.5
    else:
        return "NEUTRAL", 0

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
    if overall_score > 5:
        trend = "Hype/Positive 🚀"
    elif overall_score < -5:
        trend = "Negative ⚠️"
    else:
        trend = "Neutral 😐"
    return posts, percentages, trend

# -----------------------------
# API Endpoint (Google News only)
# -----------------------------
@app.get("/analyze")
def analyze_nft(nft_name: str = Query(..., description="Name of the NFT")):
    try:
        google_news = fetch_google_news(nft_name, max_pages=3)
        all_posts = [p for p in google_news if len(p["text"])>20]

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
