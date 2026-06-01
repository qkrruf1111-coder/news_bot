import os
import requests
from datetime import datetime, timedelta
from calendar import monthrange

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TMDB_API_KEY = os.environ["TMDB_API_KEY"]

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def get_next_month_range():
    today = datetime.today()
    year = today.year if today.month < 12 else today.year + 1
    month = today.month + 1 if today.month < 12 else 1
    last_day = monthrange(year, month)[1]
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-{last_day}"
    return start, end, year, month


def fetch_upcoming_movies():
    start, end, year, month = get_next_month_range()
    url = f"{TMDB_BASE}/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "ko-KR",
        "region": "KR",
        "primary_release_date.gte": start,
        "primary_release_date.lte": end,
        "sort_by": "popularity.desc",
        "page": 1,
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    movies = res.json().get("results", [])[:10]

    detailed = []
    for m in movies:
        detail_url = f"{TMDB_BASE}/movie/{m['id']}"
        detail_params = {"api_key": TMDB_API_KEY, "language": "ko-KR", "append_to_response": "credits"}
        d = requests.get(detail_url, params=detail_params).json()

        director = next((c["name"] for c in d.get("credits", {}).get("crew", []) if c["job"] == "Director"), "정보 없음")
        cast = [c["name"] for c in d.get("credits", {}).get("cast", [])[:3]]
        genres = [g["name"] for g in d.get("genres", [])[:2]]
        runtime = d.get("runtime", 0)
        poster = d.get("poster_path", "")

        detailed.append({
            "title": d.get("title", m["title"]),
            "release_date": d.get("release_date", ""),
            "genres": genres,
            "runtime": runtime,
            "director": director,
            "cast": cast,
            "poster": f"{TMDB_IMAGE_BASE}{poster}" if poster else None,
        })

    return detailed, year, month


def fetch_boxoffice():
    url = f"{TMDB_BASE}/movie/now_playing"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "ko-KR",
        "region": "KR",
        "page": 1,
    }
    res = requests.get(url, params=params)
    res.raise_for_status()
    movies = res.json().get("results", [])[:10]
    return sorted(movies, key=lambda x: x.get("popularity", 0), reverse=True)


def send_telegram_photo(photo_url, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }
    res = requests.post(url, json=payload)
    return res.status_code == 200


def send_telegram_text(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    res = requests.post(url, json=payload)
    res.raise_for_status()


def run_upcoming():
    movies, year, month = fetch_upcoming_movies()
    header = f"🎬 <b>{year}년 {month}월 개봉 예정 영화</b>\n\n"
    send_telegram_text(header)

    for i, m in enumerate(movies, 1):
        date = m["release_date"][5:].replace("-", "/") if m["release_date"] else "미정"
        runtime = f"{m['runtime']}분" if m["runtime"] else "미정"
        genres = ", ".join(m["genres"]) if m["genres"] else "미정"
        cast = ", ".join(m["cast"]) if m["cast"] else "미정"

        caption = (
            f"{i}. <b>{m['title']}</b>\n"
            f"📅 {date}  ⏱ {runtime}\n"
            f"🎭 {genres}\n"
            f"🎬 {m['director']}\n"
            f"👥 {cast}"
        )

        if m["poster"]:
            if not send_telegram_photo(m["poster"], caption):
                send_telegram_text(caption)
        else:
            send_telegram_text(caption)

    send_telegram_text("by 영화봇 🎥")


def run_boxoffice():
    movies = fetch_boxoffice()
    today = datetime.today().strftime("%Y년 %m월 %d일")
    lines = [f"🏆 <b>이번 주 박스오피스</b> ({today})\n"]

    for i, m in enumerate(movies, 1):
        rating = m.get("vote_average", 0)
        lines.append(f"{i}위  {m['title']}  ⭐ {rating:.1f}")

    lines.append("\nby 영화봇 🎥")
    send_telegram_text("\n".join(lines))


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "upcoming"
    if mode == "upcoming":
        print("🎬 개봉 예정 영화 전송 중...")
        run_upcoming()
    elif mode == "boxoffice":
        print("🏆 박스오피스 전송 중...")
        run_boxoffice()
    print("✅ 완료!")
