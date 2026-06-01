import os
import requests
import feedparser
from datetime import datetime

# 환경변수에서 텔레그램 정보 가져오기 (GitHub Secrets에서 설정)
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# 네이버 뉴스 RSS 피드 (주요 뉴스)
RSS_FEEDS = [
    "https://feeds.feedburner.com/navernews/top100",   # 네이버 뉴스 top100
    "https://news.naver.com/main/rss/allflash.naver",  # 속보
]

# 구글 뉴스 RSS (네이버가 막힐 경우 대비)
GOOGLE_NEWS_RSS = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"


def fetch_news(limit=10):
    """뉴스 RSS에서 헤드라인 가져오기"""
    articles = []

    # 구글 뉴스 RSS 시도 (안정적)
    feed = feedparser.parse(GOOGLE_NEWS_RSS)
    for entry in feed.entries[:limit]:
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "source": entry.get("source", {}).get("title", ""),
        })

    return articles


def format_message(articles):
    """텔레그램 메시지 포맷"""
    now = datetime.now()
    hour = now.hour
    time_label = "🌅 오전 주요 뉴스" if hour < 12 else "🌆 오후 주요 뉴스"
    date_str = now.strftime("%Y년 %m월 %d일")

    lines = [f"*{time_label}*", f"_{date_str}_", ""]

    for i, article in enumerate(articles, 1):
        source = f" _{article['source']}_" if article["source"] else ""
        lines.append(f"{i}\\. [{article['title']}]({article['link']}){source}")

    lines.append("")
    lines.append("_by 뉴스봇 🤖_")

    return "\n".join(lines)


def send_telegram(message):
    """텔레그램으로 메시지 전송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": False,
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    print(f"✅ 전송 완료: {response.status_code}")


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
