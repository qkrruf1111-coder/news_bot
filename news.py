import os
import requests
import feedparser
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

GOOGLE_NEWS_RSS = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"


def fetch_news(limit=10):
    articles = []
    feed = feedparser.parse(GOOGLE_NEWS_RSS)
    for entry in feed.entries[:limit]:
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "source": entry.get("source", {}).get("title", ""),
        })
    return articles


def format_message(articles):
    now = datetime.now()
    hour = now.hour
    time_label = "🌅 오전 주요 뉴스" if hour < 12 else "🌆 오후 주요 뉴스"
    date_str = now.strftime("%Y년 %m월 %d일")

    lines = [f"{time_label} - {date_str}", ""]

    for i, article in enumerate(articles, 1):
        source = f" ({article['source']})" if article["source"] else ""
        lines.append(f"{i}. {article['title']}{source}")
        lines.append(article['link'])
        lines.append("")

    lines.append("by 뉴스봇 🤖")
    return "\n".join(lines)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload)
    print(f"응답: {response.status_code} {response.text}")
    response.raise_for_status()
    print("✅ 전송 완료!")


def main():
    print("📰 뉴스 가져오는 중...")
    articles = fetch_news(limit=10)

    if not articles:
        print("❌ 뉴스를 가져오지 못했습니다.")
        return

    print(f"✅ {len(articles)}개 기사 수집 완료")
    message = format_message(articles)
    send_telegram(message)


if __name__ == "__main__":
    main()
