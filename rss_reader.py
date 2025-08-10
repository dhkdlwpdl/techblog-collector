import feedparser
from datetime import datetime, date

def fetch_rss_articles(feed_urls, start_date: date, end_date: date):
    articles_in_range = []

    for url in feed_urls:
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6]).date()  # 시간 제외하고 날짜만 비교
                # start_date <= pub_date <= end_date 범위 체크
                if start_date <= pub_date <= end_date:
                    articles_in_range.append({
                        "title": entry.title,
                        "link": entry.link,
                        "published_at": pub_date.strftime("%Y-%m-%d")
                    })
            else:
                print(f"check if this url is valid : {url}")

    seen = set()
    unique_articles = []
    for article in articles_in_range:
        identifier = (article["title"], article["link"])  # 중복 판단 기준
        if identifier not in seen:
            seen.add(identifier)
            unique_articles.append(article)

    return unique_articles