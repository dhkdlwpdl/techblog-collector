import argparse
from rss_reader import fetch_rss_articles
from notion_reader import fetch_processed_articles
from gpt_recommender import generate_digest
from crawler import extract_article_body
from gpt_summarizer import generate_structured_summary
from notion_writer import write_digest, write_processed_articles
from datetime import datetime, timedelta, date
from config import KST, FEED_URLS, OPENAI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID, NOTION_LOG_DATABASE_ID
import json

def _collect_rss_articles(feed_urls, start_date, end_date):
    print("🔍 RSS에서 새 글을 수집 중...")
    articles = fetch_rss_articles(feed_urls, start_date, end_date)
    print(f"✅ {len(articles)}개의 글 수집 완료")
    return articles

def _filter_new_articles(articles, notion_token, notion_log_db_id):
    """이미 처리한 글 제거 (title 또는 link가 중복되면 제외)"""
    print("📌 중복 검사 중...")
    processed_articles = fetch_processed_articles(notion_token, notion_log_db_id)
    
    processed_titles = set(t for t, _ in processed_articles)
    processed_links = set(l for _, l in processed_articles)
    
    new_articles = [
        a for a in articles
        if a["link"] not in processed_links and a["title"] not in processed_titles
    ]
    
    print(f"📌 신규 글 {len(new_articles)}개")
    return new_articles

def _create_digest(articles, open_api_key):
    """Open AI에게 추천 digest 생성 요청"""
    print("\n🤖 Open AI에게 추천 글 요약 요청 중...")
    return generate_digest(articles, open_api_key)

def _enrich_digest_with_summaries(digest, open_api_key):
    """digest 대상 글들의 본문 크롤링 & 구조화 요약"""
    print("\n🧠 digest 대상 글들에 대해 구조화 요약 생성 중...")
    for item in digest:
        item["content"] = ""
        article_url = item.get("url") or item.get("link")

        print(f"📰 본문 크롤링 중: {article_url}")
        article_text = extract_article_body(article_url)

        if not article_text:
            print(f"⚠️ 본문 크롤링 실패: {article_url}")
            continue

        print(f"🧠 Gpt 구조화 요약 생성 중: {item['title']}")
        article_summary = generate_structured_summary(article_text, open_api_key)

        if not article_summary:
            print(f"⚠️ Gpt 요약 실패: {article_url}")
            continue

        item["content"] = article_summary #참조로 접근하기 떄문에 직접 수정하면 됨
    return digest

def _save_results_to_notion(digest, notion_token, notion_db_id):
    """최종 추천 글을 Notion에 저장"""
    write_digest(notion_token, notion_db_id, digest)


def _log_processed_articles(articles, notion_token, notion_log_db_id):
    """처리한 글을 로그 DB에 기록"""
    write_processed_articles(articles, notion_token, notion_log_db_id)


if __name__ == "__main__":
    # 실행 기간
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_date', type=str, default='')
    parser.add_argument('--end_date', type=str, default='')
    args = parser.parse_args()

    if args.start_date:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
    else:
        start_date = datetime.now().date() - timedelta(days=7)

    if args.end_date:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
    else:
        end_date = datetime.now().date()

    print(f"start_date: {start_date}, end_date: {end_date}")

    # 새 글 수집
    articles = _collect_rss_articles(FEED_URLS, start_date, end_date)
    if not articles:
        print("❌ 수집된 글이 없습니다. 종료합니다.")
        exit(0)

    # 중복 제거
    new_articles = _filter_new_articles(articles, NOTION_TOKEN, NOTION_LOG_DATABASE_ID)
    if not new_articles:
        print("❌ 신규 글이 없습니다. 종료합니다.")
        exit(0)

    print(new_articles)

    try:
        digest = _create_digest(new_articles, OPENAI_API_KEY) # 추천 digest 생성

        if digest:
            enriched_digest = _enrich_digest_with_summaries(digest, OPENAI_API_KEY) # 요약 추가
            _save_results_to_notion(digest, NOTION_TOKEN, NOTION_DATABASE_ID) # notion 저장
        else:
            print("❌ 추천할 만한 글이 없습니다. 종료합니다.")

        _log_processed_articles(new_articles, NOTION_TOKEN, NOTION_LOG_DATABASE_ID) # 로그 저장

    except json.JSONDecodeError as e:
        print(f"❌ Gpt 응답 파싱 실패: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        exit(1)