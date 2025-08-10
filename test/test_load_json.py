
import json

INPUT_STRING = '''
[
  {
    "title": "일 평균 30억 건을 처리하는 결제 시스템의 DB를 Vitess로 교체하기 - 2. 개발 및 운영기",
    "url": "https://techblog.lycorp.co.jp/ko/migrate-payment-system-db-to-vitess-2",
    "summary": "이 글에서는 결제 시스템의 데이터베이스를 Vitess로 마이그레이션하는 과정에서의 개발 및 운영 경험을 공유합니다. Vitess의 아키텍처, 장점, 그리고 운영 중 발생한 문제와 해결 방안에 대해 구체적으로 다룹니다.",
    "source": "LY Corp Tech Blog",
    "published_at": "YYYY-MM-DD",
    "tags": ["데이터베이스", "Vitess", "운영", "마이그레이션"],
    "status": "Unread"
  }
]
'''

def main():
    try:
        parsed = json.loads(INPUT_STRING)
        print("✅ JSON 파싱 성공!")
        print(parsed)
    except json.JSONDecodeError as e:
        print("❌ JSON 파싱 실패:")
        print(f"에러 메시지: {e.msg}")
        print(f"문제 발생 위치: 줄 {e.lineno}, 열 {e.colno}")
        lines = INPUT_STRING.split('\n')
        error_line = lines[e.lineno - 1]
        print(f"\n문제 줄 내용:\n{error_line}")
        print(" " * (e.colno - 1) + "^ 여기에서 문제 발생")

if __name__ == "__main__":
    main()