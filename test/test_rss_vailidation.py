import feedparser
import requests

def is_valid_rss_feed(url, timeout=3):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # HTTP 에러 체크
        feed = feedparser.parse(response.content)
        if feed.bozo:
            return False
        if not feed.entries:
            return False
        return True
    except Exception:
        return False

def check_rss_feeds(url_list):
    valid_feeds = []
    invalid_feeds = []
    for url in url_list:
        if is_valid_rss_feed(url):
            valid_feeds.append(url)
            print(url)
            # print(f"✅ Valid RSS: {url}")
        else:
            invalid_feeds.append(url)
            # print(f"❌ Invalid RSS: {url}")
    return valid_feeds, invalid_feeds

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
    "https://techblog.woowahan.com/feed",
    "https://tech.devsisters.com/rss.xml",
    "https://medium.com/feed/coupang-engineering",
    "https://medium.com/feed/daangn",
    "https://medium.com/feed/zigbang",
    "https://medium.com/feed/watcha",
    "https://blog.banksalad.com/rss.xml",
    "https://hyperconnect.github.io/feed.xml",
    "https://techblog.yogiyo.co.kr/feed",
    "https://tech.socarcorp.kr/feed",
    "https://www.ridicorp.com/feed",
    "https://meetup.toast.com/rss",
    "https://news.hada.io/rss/news",
    "https://v2.velog.io/rss/",
    "https://blog.gaerae.com/feeds/posts/default?alt=rss",
    "https://www.44bits.io/ko/feed/all",
    "https://techblog.lycorp.co.jp/ko/feed/index.xml",
    "https://cheese10yun.github.io/feed.xml",
    "https://javacan.tistory.com/rss",
    "https://jojoldu.tistory.com/rss",
    "https://hyune-c.tistory.com/rss",
    "https://brunch.co.kr/rss/@@2MrI",
    "http://rss.egloos.com/blog/aeternum",
    "https://team.postype.com/rss"
]

valid_feeds, invalid_feeds = check_rss_feeds(FEED_URLS)