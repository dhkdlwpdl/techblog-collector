from notion_client import Client
from notion_client.helpers import collect_paginated_api
from typing import List, Tuple

def fetch_processed_articles(notion_token: str, notion_log_database_id: str) -> List[Tuple[str, str]]:
    """Notion 로그 DB에서 이미 처리된 (title, url) 튜플 리스트를 반환."""
    notion = Client(auth=notion_token)
    processed = []

    # Notion 데이터베이스 쿼리 (모든 페이지를 페이지네이션하여 가져오기)
    pages = collect_paginated_api(
        notion.databases.query,
        database_id=notion_log_database_id,
        page_size=100,
    )
    
    for page in pages:
        props = page["properties"]
        
        title_prop = props.get("title")
        link_prop = props.get("link")

        # title 필드는 title 타입 배열로 들어옴 (title_prop["title"] 리스트)
        title = ""
        if title_prop and title_prop.get("title"):
            title_parts = title_prop["title"]
            if title_parts:
                title = "".join([part.get("plain_text", "") for part in title_parts])

        url = ""
        if link_prop and link_prop.get("url"):
            url = link_prop["url"]

        if title and url:
            processed.append((title, url))

    return processed