from notion_client import Client
from notion_client.helpers import collect_paginated_api
from notion_client.errors import APIResponseError
import traceback
import re

def is_valid_iso_date(date_str):
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", date_str))

def _convert_markdown_to_notion_blocks(lines, indent_level=0):
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if indent == indent_level and stripped.startswith("- "):
            # 리스트 아이템 생성
            content = stripped[2:].strip()

            # 다음 줄들 중 더 들여쓰기 된 블록을 자식으로 처리
            j = i + 1
            children_lines = []
            while j < len(lines):
                next_line = lines[j]
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent > indent_level:
                    children_lines.append(next_line)
                    j += 1
                else:
                    break

            children = []
            if children_lines:
                children = _convert_markdown_to_notion_blocks(children_lines, indent_level=indent_level+2)

            block = {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": content}
                    }],
                    "children": children if children else None
                }
            }

            # children 필드는 빈 리스트가 아니면 넣고, 없으면 빼는게 좋음
            if not children:
                block["bulleted_list_item"].pop("children")

            blocks.append(block)
            i = j
        else:
            # indent level이 맞지 않으면 그냥 일반 문단으로 처리
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": stripped}
                    }]
                }
            })
            i += 1

    return blocks


def _convert_text_to_notion_blocks(text: str):
    lines = text.strip().split("\n")
    return _convert_markdown_to_notion_blocks(lines)


def write_digest(notion_token, database_id, articles):
    notion = Client(auth=notion_token)

    for idx, article in enumerate(articles):
        print(f"\n📝 [{idx+1}/{len(articles)}] Notion에 쓰는 중: {article.get('title', '제목 없음')}")
        print("🔍 원본 아티클 데이터:", article)

        # 필수 필드 검증
        required_fields = ["title", "url", "status", "source", "published_at", "summary"]
        for field in required_fields:
            if not article.get(field):
                raise ValueError(f"필수 필드 누락: '{field}'")

        # 날짜 형식 검증
        if not is_valid_iso_date(article["published_at"]):
            raise ValueError(f"날짜 형식 오류 (YYYY-MM-DD 아님): {article['published_at']}")

        # Notion에 페이지 생성
        response = notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Title": {
                    "title": [{"text": {"content": article["title"]}}]
                },
                "URL": {
                    "url": article["url"]
                },
                "Status": {
                    "status": {"name": article["status"]}
                },
                "Source": {
                    "select": {"name": article["source"]}
                },
                "Published At": {
                    "date": {"start": article["published_at"]}
                },
                "Tags": {
                    "multi_select": [{"name": tag} for tag in article.get("tags", [])]
                },
                "Summary": {
                    "rich_text": [{"text": {"content": article["summary"][:2000]}}]  # Notion API는 길이 제한 있음
                }
            },
            children=_convert_text_to_notion_blocks(article["content"])
        )

        print(f"✅ 작성 완료: {article['title']}")


def write_processed_articles(articles, notion_token, notion_log_database_id):
    """처리 완료된 article들을 Notion 로그 DB에 저장"""
    notion = Client(auth=notion_token)

    for article in articles:
        notion.pages.create(
            parent={"database_id": notion_log_database_id},
            properties={
                "title": {
                    "title": [{"text": {"content": article.get("title", "제목 없음")}}]
                },
                "link": {
                    "url": article.get("link")
                },
                "published_at": {
                    "date": {"start": article.get("published_at")}
                },
                # created_at은 Notion이 자동 생성하므로 별도 지정 없음
            }
        )
        print(f"✅ 로그 DB 저장 완료: {article.get('title')}")