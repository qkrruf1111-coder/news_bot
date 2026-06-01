import os
import requests
from datetime import datetime, timedelta
from calendar import monthrange
from urllib.parse import quote

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
MOVIE_CHAT_ID = os.environ["MOVIE_CHAT_ID"]
TMDB_API_KEY = os.environ["TMDB_API_KEY"]
KOBIS_API_KEY = os.environ["KOBIS_API_KEY"]

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
KOBIS_BASE = "http://www.kobis.or.kr/kobisopenapi/webservice/rest"


def naver_link(title):
    return f"https://search.naver.com/search.naver?query={quote(title + ' 영화')}"


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
        title = d.get("title", m["title"])

        detailed.append({
            "title": title,
            "release_date": d.get("release_date", ""),
            "genres": genres,
            "runtime": runtime,
            "director": director,
            "cast": cast,
            "poster": f"{TMDB_IMAGE_BASE}{poster}" if poster else None,
            "naver_url": naver_link(title),
        })

    return detailed, year, month


def fetch_boxoffice(multi_movie_yn=None):
    today = datetime.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    end = last_sunday.strftime("%Y%m%d")

    url = f"{KOBIS_BASE}/boxoffice/searchWeeklyBoxOfficeList.json"
    params = {
        "key": KOBIS_API_KEY,
        "targetDt": end,
        "weekGb": "0",
    }
    if multi_movie_yn:
        params["multiMovieYn"] = multi_movie_yn

    res = requests.get(url, params=params)
    res.raise_for_status()
    data = res.json()
    movies = data.get("boxOfficeResult", {}).get("weeklyBoxOfficeList", [])[:10]
    return movies, last_monday, last_sunday


def rank_change_emoji(m):
    if m.get("rankOldAndNew") == "NEW":
        return "🆕"
    change = int(m.get("rankInten", 0))
    if change > 0:
        return f"↑{change}"
    elif change < 0:
        return f"↓{abs(change)}"
    else:
        return "→"


def send_telegram_photo(photo_url, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": MOVIE_CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }
    res = requests.post(url, json=payload)
    return res.status_code == 200


def send_telegram_text(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": MOVIE_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    res = requests.post(url, json=payload)
    print(f"응답: {res.status_code} {res.text}")
    res.raise_for_status()


def run_upcoming():
    movies, year, month = fetch_upcoming_movies()
    send_telegram_text(f"🎬 <b>{year}년 {month}월 개봉 예정 영화</b>")

    for i, m in enumerate(movies, 1):
        date = m["release_date"][5:].replace("-", "/") if m["release_date"] else "미정"
        runtime = f"{m['runtime']}분" if m["runtime"] else "미정"
        genres = ", ".join(m["genres"]) if m["genres"] else "미정"
        cast = ", ".join(m["cast"]) if m["cast"] else "미정"

        caption = (
            f'{i}. <a href="{m["naver_url"]}"><b>{m["title"]}</b></a>\n'
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


def format_boxoffice(movies, start, end, title_emoji, title_label):
    start_str = start.strftime("%m/%d")
    end_str = end.strftime("%m/%d")

    lines = [f"{title_emoji} <b>{title_label}</b> ({start_str} ~ {end_str})\n"]

    for m in movies:
        rank = m.get("rank", "")
        title = m.get("movieNm", "")
        audience_week = int(m.get("audiCnt", 0))
        audience_acc = int(m.get("audiAcc", 0))
        sales_week = int(m.get("salesAmt", 0))
        screens = int(m.get("scrnCnt", 0))
        change = rank_change_emoji(m)
        link = naver_link(title)

        lines.append(
            f'{rank}위 {change} <a href="{link}">{title}</a>\n'
            f'     👥 주간 {audience_week:,}명 / 누적 {audience_acc:,}명\n'
            f'     🎬 스크린 {screens:,}개\n'
            f'     💰 주간 {sales_week:,}원\n'
        )

    lines.append("by 영화봇 🎥")
    return "\n".join(lines)


def run_boxoffice():
    movies, start, end = fetch_boxoffice()
    send_telegram_text(format_boxoffice(movies, start, end, "🏆", "주간 박스오피스"))

    art_movies, start, end = fetch_boxoffice(multi_movie_yn="Y")
    if art_movies:
        send_telegram_text(format_boxoffice(art_movies, start, end, "🎨", "예술영화 박스오피스"))


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "upcoming"
    if mode == "upcoming":
        print("🎬 개봉 예정 영화 전송 중...")
        run_upcoming()
        today = datetime.today()
        if today.weekday() == 0 and today.day in (1, 15):
            print("📅 오늘은 월요일이자 1일/15일 - 박스오피스도 전송!")
            run_boxoffice()
    elif mode == "boxoffice":
        print("🏆 박스오피스 전송 중...")
        run_boxoffice()
    print("✅ 완료!")
