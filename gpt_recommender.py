import re
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import json

MODEL_NAME = "gpt-4o-mini"

SYSTEM_CONTENT = """
당신은 데이터 엔지니어링 관련 기술 블로그를 큐레이션하는 전문가입니다.
사용자에게 도움이 될 만한 글을 추천해주세요.

주어진 링크 목록 내에서만 추천해야 합니다.
모든 글이 유용하다면 전부 추천해도 되고, 추천할 만한 글이 없다면 추천하지 않아도 무방합니다.
만약 추천할 글이 없다면 아무것도 반환하지 마세요.

추천 기준:
	•	실무에 바로 적용 가능한 데이터 파이프라인 설계, 인프라 구축, 운영 및 자동화 관련 주제
	•	데이터 엔지니어링에서 주로 활용되는 기술 (예: Airflow, Kafka, CDC, Spark, Hadoop, Databricks 등)
	•	ML 엔지니어링과 MLOps 관련 최신 동향 및 실용 정보
	•	최근 관심사인 MCP(Model Context Protocol)에 관한 글이 있다면 함께 추천
    •	대용량 데이터 처리, 대규모 트래픽 처리, 빅데이터 관련 정보
    •	서비스의 신뢰성 향상을 위한 작업, 모니터링, 자동화, 장애 대응, SRE 관련 정보
    •	쿠버네티스, 도커, 가상화 환경 관련 내용
    •	로깅 관련 기술 (OpenTelemetry, Elasticsearch, Loki, Prometheus 등) 포함 시 추천
    •	제목에 ‘데이터’라는 단어가 포함된 글은 반드시 추천
    •	실시간, 배치 데이터 처리에 대한 내용

각 추천 글에 다음 정보를 포함해주세요:
	•	제목
	•	추천 이유 (간략하게 핵심만)
	•	1줄 요약 (간결하게)
	•	링크

요약은 너무 길지 않게 한 문장 정도로 작성해주세요.
출력은 다음 JSON 형태로 해주세요:

[
  {
    "title": "글 제목",
    "url": "https://링크",
    "summary": "요약 내용",
    "source": "출처 이름",
    "published_at": "YYYY-MM-DD",
    "tags": ["태그1", "태그2"],
    "status": "Unread"
  },
  ...
]
"""

def clean_summary(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = re.sub(r"\s+", " ", text)
    return text

def build_prompt(articles):
    content_lines = ["다음은 최근 기술 블로그 글 목록입니다:"]
    for i, article in enumerate(articles, 1):
        content_lines.append(f"[{i}] {article['title']}\n링크: {article['link']}")
    user_prompt = "\n\n".join(content_lines)
    return [
        {"role": "system", "content": SYSTEM_CONTENT},
        {"role": "user", "content": user_prompt}
    ]

def generate_digest(articles, openai_api_key):
    if not articles:
        return []

    client = OpenAI(api_key=openai_api_key)
    messages: list[ChatCompletionMessageParam] = build_prompt(articles)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.7,
    )

    content = response.choices[0].message.content.strip()
    
    # print("[Gpt 응답 원본]", content)

    if content.startswith("```json"):
        content = content.removeprefix("```json").rstrip("```").strip()

    parsed = json.loads(content)
    if not parsed:
        print("⚠️ Gpt가 추천할 만한 글을 찾지 못했습니다.")
    else:
        # URL 기준으로 published_at 보정
        url_to_date = {a["link"]: a.get("published_at") for a in articles}

        for item in parsed:
            # url 필드가 없으면 link로 fallback
            article_url = item.get("url") or item.get("link")
            matched_date = url_to_date.get(article_url)
            if matched_date:
                item["published_at"] = matched_date

            # summary 클린업 적용
            if "summary" in item:
                item["summary"] = clean_summary(item["summary"])

    return parsed