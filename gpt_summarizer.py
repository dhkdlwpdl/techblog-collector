import re
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from typing import List, Dict, Any

MODEL_NAME = "gpt-4o"  # 또는 "gpt-4-turbo" 등

SYSTEM_CONTENT = "당신은 기술 블로그를 잘 요약하는 AI 비서입니다. 각 글을 마크다운 구조로 정리해 주세요."

PROMPT = """
다음 기술 글의 내용을 마크다운 리스트 형식으로 정리해줘.

형식:
- 첫 줄부터 세 줄까지는 핵심 요점을 요약 (plain text, 리스트로 작성하지 말 것)
- 그 아래는 마크다운 리스트 형식으로 기술 내용을 정리
- 각 항목은 계층 구조를 갖춰서 작성
- 각 리스트 항목은 기술 설명 위주로 작성 (요약 금지)
- 문체는 존댓말도 반말도 아닌, 중립적이고 기술 문서에 적합한 스타일
- 정보가 많을 경우 길어져도 괜찮음
- 마크다운 리스트만 사용하고 `#`, `##` 같은 제목 태그는 사용하지 말 것
- 리스트는 `-` 기호를 이용해 중첩 구조로 표현할 것
- 볼드(**)는 적용하지 않을것
- 요약에 실패할 경우 빈 문자열을 반환할 것

--- 원문 내용 ---
"""

def clean_summary(summary: str) -> str:
    # 공백 정리, 특수문자 제거 등
    return re.sub(r'\n{2,}', '\n', summary.strip())

def build_prompt(article_text: str) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_CONTENT},
        {"role": "user", "content": PROMPT + f"\n{article_text}"}
    ]

def generate_structured_summary(article_text: str, openai_api_key: str):
    try:
        client = OpenAI(api_key=openai_api_key)
        messages: List[ChatCompletionMessageParam] = build_prompt(article_text)

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()
        # print("[🧠 Gpt 응답 원본]", content)
        return content
    except Exception as e:
        print("⚠️ Gpt 통한 요약에 실패했습니다: {e}")
        return ""