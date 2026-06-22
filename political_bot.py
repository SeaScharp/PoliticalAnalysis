import streamlit as st
import requests
import feedparser
from datetime import datetime
from anthropic import Anthropic

st.set_page_config(page_title="Political Risk Bot", page_icon="🌍", layout="wide")

st.title("🌍 Political Risk Analysis Bot")
st.caption("Political + Geopolitical market-risk scanner for crypto and stocks")

# -----------------------------
# CONFIG
# -----------------------------
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = st.secrets.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

RSS_FEEDS = {
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "Le Monde Middle East": "https://www.lemonde.fr/en/middle-east/rss_full.xml",
    "Le Monde International": "https://www.lemonde.fr/en/international/rss_full.xml",
}

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


# -----------------------------
# FUNCTIONS
# -----------------------------
def fetch_rss_news(max_items=25):
    articles = []

    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)

        for entry in feed.entries[:max_items]:
            articles.append({
                "source": source,
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", "")
            })

    return articles


def fetch_gdelt_news(query, max_records=25):
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": max_records,
        "sort": "datedesc"
    }

    try:
        response = requests.get(
            GDELT_URL,
            params=params,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if response.status_code != 200:
            st.warning(f"GDELT returned HTTP {response.status_code}")
            return []

        if not response.text.strip():
            st.warning("GDELT returned empty response.")
            return []

        try:
            data = response.json()
        except Exception:
            st.warning("GDELT did not return valid JSON. Skipping GDELT.")
            return []

        articles = []
        for item in data.get("articles", []):
            articles.append({
                "source": item.get("sourceCountry", "GDELT"),
                "title": item.get("title", ""),
                "summary": item.get("domain", ""),
                "link": item.get("url", ""),
                "published": item.get("seendate", "")
            })

        return articles

    except Exception as e:
        st.warning(f"GDELT error: {e}")
        return []


def keyword_risk_score(text):
    risk_keywords = {
        "war": 12,
        "attack": 10,
        "missile": 10,
        "invasion": 14,
        "sanction": 9,
        "tariff": 8,
        "election": 5,
        "coup": 13,
        "oil": 8,
        "iran": 10,
        "israel": 10,
        "russia": 9,
        "china": 8,
        "taiwan": 10,
        "nato": 8,
        "red sea": 9,
        "hormuz": 12,
        "fed": 6,
        "central bank": 6,
        "crypto regulation": 10,
        "sec": 6,
        "inflation": 7,
        "protest": 7,
        "strike": 6,
        "default": 10,
        "debt": 6,
    }

    text = text.lower()
    score = 20

    for keyword, weight in risk_keywords.items():
        if keyword in text:
            score += weight

    return min(score, 100)


def analyze_with_claude(articles):
    if not client:
        return "Claude API key missing. Add ANTHROPIC_API_KEY in Streamlit secrets."

    news_text = ""

    for i, article in enumerate(articles[:30], 1):
        news_text += f"""
{i}. Source: {article['source']}
Title: {article['title']}
Summary: {article['summary']}
Published: {article['published']}
Link: {article['link']}
"""

    prompt = f"""
You are a political and geopolitical risk analyst for crypto and stock traders.

Analyze the following political news.

Return the answer in this exact structure:

1. Global Political Risk Score: X/100
2. Market Mood: Risk-On / Neutral / Risk-Off
3. Crypto Impact: Bullish / Neutral / Bearish
4. Stock Market Impact: Bullish / Neutral / Bearish
5. Oil Impact: Bullish / Neutral / Bearish
6. Gold Impact: Bullish / Neutral / Bearish
7. USD Impact: Bullish / Neutral / Bearish
8. Top 5 Political Risks
9. Trading Bias for the Next 24-72 Hours
10. Confidence Score: X%

Important:
- Do not give financial advice.
- Explain uncertainty.
- Focus on politics, war, sanctions, elections, tariffs, central banks, regulation, energy, and geopolitical escalation.

News:
{news_text}
"""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1200,
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.content[0].text


# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.header("Settings")

region = st.sidebar.selectbox(
    "Focus Region",
    [
        "Global",
        "Middle East",
        "United States",
        "China Taiwan",
        "Russia Ukraine",
        "Europe",
        "Crypto Regulation",
        "Oil Shipping Routes"
    ]
)

manual_query = st.sidebar.text_input("Extra Search Keyword", "")

run_button = st.sidebar.button("Run Political Analysis")


# -----------------------------
# QUERY BUILDER
# -----------------------------
region_queries = {
    "Global": "war OR sanctions OR election OR tariffs OR oil OR inflation OR central bank",
    "Middle East": "Iran Israel Gaza Lebanon Syria oil Hormuz war missile",
    "United States": "United States election Fed tariffs SEC crypto regulation debt",
    "China Taiwan": "China Taiwan tariffs South China Sea trade war",
    "Russia Ukraine": "Russia Ukraine NATO sanctions oil gas war",
    "Europe": "Europe election NATO Russia energy inflation",
    "Crypto Regulation": "crypto regulation SEC stablecoin bitcoin ETF government",
    "Oil Shipping Routes": "oil shipping Red Sea Hormuz sanctions tanker"
}

search_query = region_queries.get(region, region_queries["Global"])

if manual_query:
    search_query += f" {manual_query}"


# -----------------------------
# MAIN APP
# -----------------------------
if run_button:
    with st.spinner("Fetching political and geopolitical news..."):
        rss_articles = fetch_rss_news()
        all_articles = rss_articles

    if not all_articles:
        st.error("No news found.")
        st.stop()

    combined_text = " ".join(
        [a["title"] + " " + a["summary"] for a in all_articles]
    )

    base_score = keyword_risk_score(combined_text)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Political Risk Score", f"{base_score}/100")

    with col2:
        if base_score >= 70:
            mood = "Risk-Off"
        elif base_score >= 45:
            mood = "Neutral"
        else:
            mood = "Risk-On"

        st.metric("Market Mood", mood)

    with col3:
        if base_score >= 70:
            crypto_bias = "Bearish / Defensive"
        elif base_score >= 45:
            crypto_bias = "Neutral / Cautious"
        else:
            crypto_bias = "Bullish / Risk-On"

        st.metric("Crypto Bias", crypto_bias)

    st.divider()

    with st.spinner("Claude is analyzing political market impact..."):
        ai_analysis = analyze_with_claude(all_articles)

    st.subheader("AI Political Market Analysis")
    st.write(ai_analysis)

    st.divider()

    st.subheader("Top News Used")

    for article in all_articles[:15]:
        st.markdown(f"### {article['title']}")
        st.write(f"**Source:** {article['source']}")
        st.write(f"**Published:** {article['published']}")
        st.write(article["summary"])
        if article["link"]:
            st.write(article["link"])
        st.divider()

else:
    st.info("Choose a region and click **Run Political Analysis**.")
