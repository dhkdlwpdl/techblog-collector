import os
from dotenv import load_dotenv
load_dotenv()
from datetime import timezone, timedelta

# KST timezone 정의 (UTC+9)
KST = timezone(timedelta(hours=9))

FEED_URLS = [
    "https://tech.kakaoenterprise.com/feed",
    "https://toss.tech/rss.xml",
    "https://helloworld.kurly.com/feed.xml",
    "https://engineering.linecorp.com/ko/feed/",
    "https://netmarble.engineering/feed/",
    "https://tech.kakao.com/feed/",
    "https://woowabros.github.io/feed.xml",
    "https://medium.com/feed/musinsa-tech",
    "https://d2.naver.com/d2.atom",
    "https://tech.devsisters.com/rss.xml",
    "https://medium.com/feed/daangn",
    "https://medium.com/feed/watcha",
    "https://blog.banksalad.com/rss.xml",
    "https://hyperconnect.github.io/feed.xml",
    "https://techblog.yogiyo.co.kr/feed",
    "https://tech.socarcorp.kr/feed",
    "https://www.ridicorp.com/feed",
    "https://meetup.toast.com/rss",
    "https://news.hada.io/rss/news",
    "https://blog.gaerae.com/feeds/posts/default?alt=rss",
    "https://techblog.lycorp.co.jp/ko/feed/index.xml",
    "https://javacan.tistory.com/rss",
    "https://jojoldu.tistory.com/rss",
    "https://hyune-c.tistory.com/rss",
    "https://brunch.co.kr/rss/@@2MrI",
    "https://team.postype.com/rss"
]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_LOG_DATABASE_ID = os.getenv("NOTION_LOG_DATABASE_ID")