import requests
import feedparser
import io
import PyPDF2
import os
import schedule
import time
import logging
from openai import OpenAI
from notion_client import Client
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

logging.basicConfig(level=logging.INFO)

# APIキーの設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

# APIエンドポイントの定義
ARXIV_API_ENDPOINT = "http://export.arxiv.org/api/query?"

# Notionクライアントの初期化
notion_client = Client(auth=NOTION_API_KEY)

# OpenAIクライアントの初期化
openai_client = OpenAI(api_key=OPENAI_API_KEY)


def get_all_paper_titles():
    # Notionのデータベースから全てのエントリを取得する
    response = notion_client.databases.query(NOTION_DB_ID)
    entries = response["results"]

    # 全ての論文のタイトルを取得する
    all_titles = [entry["properties"]["名前"]["title"][0]["text"]["content"] for entry in entries]
    return all_titles

def search_arxiv_papers(query, max_results=10):
    # arXivから論文を検索して結果を返す。
    all_titles = get_all_paper_titles()
    papers = []
    start = 0

    while len(papers) < max_results:
        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results
        }
        response = requests.get(ARXIV_API_ENDPOINT, params=params)
        feed = feedparser.parse(response.content)
        new_papers = [
            {"title": entry.title, "pdf_link": entry.link.replace("abs", "pdf"), "published": entry.published}
            for entry in feed.entries
        ]
        for paper in new_papers:
            if paper["title"] not in all_titles or len(papers) < max_results:
                papers.append(paper)
        start += max_results

    if not papers:
        print("条件に合った論文がありません")
    return papers[:max_results]

def download_paper_text(url):
    # 指定されたURLからPDFをダウンロードし、テキストに変換する。
    response = requests.get(url)
    with io.BytesIO(response.content) as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        return "\n".join(page.extract_text() for page in reader.pages)

# def generate_summary(system_message, user_message):
#     #ChatGPTを使用してテキストの要約を生成する。
#     response = openai_client.chat.completions.create(
#         model="gpt-4-1106-preview",
#         messages=[
#             {"role": "system", "content": system_message},
#             {"role": "user", "content": user_message},
#         ]
#     )
#     summary = response.choices[0].message.content
#     token_usage = ", ".join(map(str, response.usage))
#     return f"{summary} Tokens Used: {token_usage}"

def add_to_notion_database(db_id, title, link, summary, published):
    # Notionデータベースに新しいエントリを追加する。
    response = notion_client.pages.create(
        parent={"database_id": db_id},
        properties={
            "名前": {"title": [{"text": {"content": title}}]},
            "URL": {"url": link},
            "公開日": {"date": {"start": published}}
        },
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary}}]
                }
            }
        ]
    )
    print("Notion database entry created:", response)

def main():
    logging.info("Task started")
    query = "artificial intelligence OR deep learning OR quantum mechanics OR generative AI OR generative models OR prompt OR large language models"
    papers = search_arxiv_papers(query)

    for paper in papers:
        print(f"Title: {paper['title']}")
        print(f"PDF Link: {paper['pdf_link']}")
        print(f"Published: {paper['published']}")

        pdf_text = download_paper_text(paper['pdf_link'])

        with open('prompt.txt', 'r', encoding='utf-8') as file:
            system_message = file.read()

        summary = ""
        # summary = generate_summary(system_message, pdf_text)
        # print(f"Summary: {summary}\n")

        add_to_notion_database(NOTION_DB_ID, paper['title'], paper['pdf_link'], summary, paper['published'])
    logging.info("Task finished")

if __name__ == "__main__":
    schedule.every().day.at("06:00").do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)

