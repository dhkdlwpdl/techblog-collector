import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crawler import extract_article_body

if __name__ == "__main__":
    test_urls = [
        # "https://techblog.woowahan.com/22586/",  # 우아한형제들
        # "https://toss.tech/article/undercover-silo-3",  # 토스
        "https://techblog.lycorp.co.jp/ko/migrate-payment-system-db-to-vitess-2",  # LY Corp
    ]

    for url in test_urls:
        print(f"\n🔗 URL: {url}")
        body = extract_article_body(url)
        print("📄 본문 미리보기 (앞 500자):\n")
        # print(body[:500])  # 너무 길면 앞부분만 보기
        print(body)