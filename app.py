import os
import feedparser
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify

# Gemini APIキーの設定
GEMINI_API_KEY = "APIキー"

# Gemini APIの初期化
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel('gemini-2.5-flash-lite')

app = Flask(__name__)

# ニュースの取得元 (RSS URL) の定義
RSS_FEEDS = {
    "economy": "https://news.yahoo.co.jp/rss/categories/business.xml", # 経済(Yahoo)
    "gourmet": "https://news.google.com/rss/search?q=グルメ&hl=ja&gl=JP&ceid=JP:ja", # グルメ(Google)
    "health": "https://news.google.com/rss/search?q=健康&hl=ja&gl=JP&ceid=JP:ja" # 健康(Google)
}

#　画面を表示する
@app.route('/')
def index():
    return render_template('index.html')

# 4. ニュースデータを渡す機能
@app.route('/api/news', methods=['POST'])
def get_news():
    data = request.json
    category = data.get('category', 'economy') # デフォルトを経済に
    
    # カテゴリに対応するRSSのURLを取得
    rss_url = RSS_FEEDS.get(category)
    if not rss_url:
        return jsonify({"error": "Invalid category"}), 400

    # RSSからニュースを取得
    feed = feedparser.parse(rss_url)
    news_list = []

    # 記事を上から10個処理する
    entries = feed.entries[:10]

    for entry in entries:
        title = entry.title
        link = entry.link
        
        # 概要文を取得
        summary = ""
        if 'summary' in entry:
            summary = entry.summary
        elif 'description' in entry:
            summary = entry.description

        # HTMLタグなどを簡易的に除去
        summary = clean_html(summary)

        # Geminiを使ってタグを生成
        tags = generate_tags(title)

        # データのまとめ
        news_list.append({
            "title": title,
            "link": link,
            "summary": summary,
            "tags": tags
        })

    return jsonify(news_list)

def generate_tags(title):
    """ニュースタイトルからタグを生成"""
    try:
        # 具体的な指示を与えてタグを生成
        prompt = f"以下のニュースタイトルに対して、内容を表す具体的な名詞のタグを3つ生成してください。出力はカンマ区切り（例: スポーツ,サッカー,日本代表）のみにしてください。挨拶や説明など余計な文章は一切入れないでください。\n\nタイトル: {title}"
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # 改行や全角カンマを半角カンマに変換
        text = text.replace('\n', ',').replace('、', ',')
        
        # カンマで分割し、空白を除去
        raw_tags = [t.strip() for t in text.split(',') if t.strip()]
        
        # 不要な記号を除去
        tags = []
        for tag in raw_tags:
            tag = tag.lstrip('*-• ') # 箇条書き記号などが先頭にあれば除去
            tags.append(tag)
            
        return tags[:3] # タグを最大3つまで返す
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return ["AIタグ生成中..."]

def clean_html(raw_html):
    """HTMLタグを取り除いて見やすくする"""
    import re
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', raw_html)
    return text[:80] + "..."

if __name__ == '__main__':
    app.run(debug=True, port=5000)