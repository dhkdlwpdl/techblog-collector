import requests
from bs4 import BeautifulSoup

def extract_article_body(url: str) -> str:
    try:
        response = requests.get(url, timeout=10, verify=False) #@TODO: verify=False 말고 다른 SSL 인증서 확인 방법
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 가장 일반적인 본문 선택 (필요시 사이트별 커스터마이징)
        candidates = [
            'div.post-content',  # 우아한형제들 블로그
            'article',
            'div.entry-content',
            'section.content',
            'div.contents'
        ]

        for selector in candidates:
            content = soup.select_one(selector)
            if content:
                return content.get_text(separator='\n', strip=True)

        return ""
    except Exception as e:
        print(f"⚠️ 크롤링 에러: url {url}, {e}")
        return ""