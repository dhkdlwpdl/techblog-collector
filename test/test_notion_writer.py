import os
from dotenv import load_dotenv
import sys

# 상위 폴더의 notion_writer.py 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notion_writer import write_digest_to_notion

# 환경변수 로드
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

def test_write_digest_to_notion():
    # 각 아티클을 딕셔너리로 표현 (스키마 기준 필드 포함)
    test_articles = [{'title': '일 평균 30억 건을 처리하는 결제 시스템의 DB를 Vitess로 교체하기 - 2. 개발 및 운영기', 'url': 'https://techblog.lycorp.co.jp/ko/migrate-payment-system-db-to-vitess-2', 'summary': '이 글에서는 결제 시스템의 데이터베이스를 Vitess로 교체하는 과정에서의 개발 및 운영 경험을 공유합니다. Vitess의 설정, 배포 방법, 운영 중 발생한 문제와 해결책을 상세히 다루며, 대규모 트래픽을 처리하는 시스템에서의 실제 사례를 통해 데이터 파이프라인과 인프라 운영에 대한 통찰을 제공합니다.', 'source': 'LY Corp Tech Blog', 'published_at': '2025-08-01', 'tags': ['데이터베이스', 'Vitess', '운영', '결제 시스템'], 'status': 'Unread'}]

    try:
        # notion_writer 함수에 딕셔너리 리스트 넘긴다고 가정
        write_digest_to_notion(NOTION_TOKEN, NOTION_DATABASE_ID, test_articles)
        print("✅ Notion에 정상적으로 업로드되었습니다.")
    except Exception as e:
        print("❌ 업로드 실패:")
        print(e)

if __name__ == "__main__":
    test_write_digest_to_notion()