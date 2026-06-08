import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import escape

import arxiv
import networkx as nx
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from matplotlib import pyplot as plt
from pyvis.network import Network
from wordcloud import STOPWORDS, WordCloud
from zhipuai import ZhipuAI


st.set_page_config(
    page_title="论文阅读助手",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


STOPWORDS_EXTRA = {
    "paper", "papers", "study", "studies", "method", "methods", "result",
    "results", "approach", "model", "models", "data", "using", "based",
    "propose", "proposed", "show", "shows", "new", "task", "tasks",
    "learning",
}

ACTIVE_ZHIPU_API_KEY = ""


def apply_custom_css():
    st.markdown(
        """
        <style>
        :root {
            --background: #f8fafc;
            --foreground: #0f172a;
            --card: #ffffff;
            --card-foreground: #0f172a;
            --muted: #f1f5f9;
            --muted-foreground: #64748b;
            --primary: #2563eb;
            --primary-foreground: #ffffff;
            --secondary: #e0f2fe;
            --secondary-foreground: #075985;
            --accent: #eff6ff;
            --accent-foreground: #1d4ed8;
            --border: #e2e8f0;
            --input: #e2e8f0;
            --ring: rgba(37, 99, 235, 0.28);
            --radius: 12px;
            --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.05);
            --shadow-md: 0 8px 24px rgba(15, 23, 42, 0.08);
            --shadow-lg: 0 18px 45px rgba(15, 23, 42, 0.12);
        }

        #MainMenu, footer, [data-testid="stDecoration"] {
            visibility: hidden;
            height: 0;
        }

        header, [data-testid="stHeader"] {
            visibility: visible !important;
            background: transparent !important;
        }

        [data-testid="stToolbar"] {
            visibility: visible !important;
        }

        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"] {
            visibility: visible !important;
            display: flex !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            z-index: 10000 !important;
        }

        html {
            scroll-behavior: smooth;
        }

        html, body, [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(59, 130, 246, 0.10), transparent 32rem),
                linear-gradient(180deg, #ffffff 0%, var(--background) 34%, #eef2f7 100%);
            color: var(--foreground);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        [data-testid="stSidebar"] {
            visibility: visible !important;
            background: rgba(255, 255, 255, 0.92);
            border-right: 1px solid var(--border);
            box-shadow: 10px 0 30px rgba(15, 23, 42, 0.04);
            backdrop-filter: blur(14px);
            z-index: 999;
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
            color: #334155;
            font-size: 0.82rem;
            font-weight: 760;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-top: 1.2rem;
        }

        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3.5rem;
            max-width: 1240px;
        }

        h1 {
            color: #0f172a;
            font-size: 2.25rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            margin-bottom: 0.25rem;
        }

        h2, h3 {
            color: #1e293b;
            font-weight: 760;
        }

        a {
            color: var(--primary) !important;
            text-decoration: none;
        }

        a:hover {
            color: #1d4ed8 !important;
            text-decoration: underline;
        }

        p, li, label, .stMarkdown, .stText {
            color: #1f2937;
            line-height: 1.6;
        }

        [data-testid="stCaptionContainer"] {
            color: var(--muted-foreground);
            font-size: 0.92rem;
        }

        div[data-testid="stExpander"] {
            background: var(--card);
            border: 1px solid rgba(226, 232, 240, 0.95);
            border-radius: var(--radius);
            box-shadow: var(--shadow-md);
            margin-bottom: 1rem;
            overflow: hidden;
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
        }

        div[data-testid="stExpander"]:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-lg);
            border-color: #bfdbfe;
        }

        div[data-testid="stExpander"] details summary {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border-radius: var(--radius);
            color: #0f172a;
            font-weight: 730;
            padding: 0.95rem 1.05rem;
        }

        div[data-testid="stExpander"] details[open] summary {
            border-bottom: 1px solid var(--border);
            border-radius: var(--radius) var(--radius) 0 0;
        }

        div[data-testid="stExpander"] details > div {
            padding: 0.85rem 1.05rem 1.1rem;
        }

        .paper-abstract, .paper-oneline {
            font-size: 14px;
            line-height: 1.65;
        }

        .paper-oneline {
            color: #475569;
            font-style: italic;
            background: linear-gradient(180deg, #f8fafc 0%, #eff6ff 100%);
            border: 1px solid #dbeafe;
            border-left: 4px solid var(--primary);
            border-radius: 10px;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.9rem;
        }

        .paper-abstract {
            color: #334155;
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0.85rem 0.95rem;
        }

        div.stButton > button, div.stDownloadButton > button {
            border-radius: 8px !important;
            border: 1px solid #1d4ed8 !important;
            background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%) !important;
            color: var(--primary-foreground) !important;
            font-weight: 650 !important;
            min-height: 2.45rem;
            transition: transform 140ms ease, background 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.20);
        }

        div.stButton > button:hover, div.stDownloadButton > button:hover {
            transform: translateY(-1px) scale(1.01);
            background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
            border-color: #1e40af !important;
            box-shadow: 0 12px 24px rgba(37, 99, 235, 0.26);
        }

        div.stButton > button:focus, div.stDownloadButton > button:focus {
            box-shadow: 0 0 0 4px var(--ring) !important;
        }

        div.stButton > button:disabled {
            background: #cbd5e1 !important;
            border-color: #cbd5e1 !important;
            color: #64748b !important;
            box-shadow: none !important;
            transform: none !important;
        }

        input, textarea, select,
        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div,
        [data-baseweb="select"] > div {
            border-radius: 8px !important;
            border-color: var(--input) !important;
            background: #ffffff !important;
        }

        input:focus, textarea:focus,
        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="textarea"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within {
            border-color: var(--primary) !important;
            box-shadow: 0 0 0 3px var(--ring) !important;
        }

        [data-testid="stAlert"] {
            border-radius: var(--radius);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }

        [data-testid="stStatusWidget"] {
            border-radius: var(--radius);
            border-color: var(--border);
            box-shadow: var(--shadow-sm);
        }

        pre, code {
            font-size: 14px !important;
            line-height: 1.55 !important;
            border-radius: 10px !important;
            background: #0f172a !important;
            color: #e2e8f0 !important;
        }

        .empty-state {
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.96)),
                radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.16), transparent 26rem);
            border: 1px dashed #bfdbfe;
            border-radius: 16px;
            box-shadow: var(--shadow-md);
            padding: 2.8rem 1.4rem;
            text-align: center;
            margin-top: 1.4rem;
        }

        .empty-state h3 {
            margin: 0.25rem 0;
            color: #0f172a;
        }

        .empty-state p {
            color: var(--muted-foreground);
        }

        .empty-icon {
            font-size: 3.2rem;
            margin-bottom: 0.45rem;
        }

        .toolbar-card {
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid rgba(226, 232, 240, 0.95);
            border-radius: 16px;
            box-shadow: var(--shadow-md);
            padding: 1rem;
            margin: 1rem 0 1.15rem;
            backdrop-filter: blur(12px);
        }

        .back-to-top {
            position: fixed;
            right: 24px;
            bottom: 24px;
            z-index: 9999;
            padding: 0.66rem 0.9rem;
            border-radius: 999px;
            background: #0f172a;
            color: white !important;
            text-decoration: none;
            box-shadow: 0 14px 28px rgba(15, 23, 42, 0.30);
            font-weight: 750;
            transition: transform 140ms ease, background 140ms ease, box-shadow 140ms ease;
        }

        .back-to-top:hover {
            background: var(--primary);
            transform: translateY(-1px) scale(1.02);
            box-shadow: 0 18px 32px rgba(37, 99, 235, 0.28);
            text-decoration: none;
        }

        [data-testid="stMetric"] {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow-sm);
            padding: 0.85rem;
        }

        @media (max-width: 720px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            div[data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
            }

            h1 {
                font-size: 1.8rem;
            }

            .toolbar-card {
                padding: 0.85rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state():
    defaults = {
        "papers": [],
        "last_query": "",
        "keyword_cache": {},
        "summary_cache": {},
        "novelty_cache": {},
        "review_cache": {},
        "literature_review": "",
        "reviewer_result": "",
        "direction_summary": "",
        "report_html": "",
        "selected_paper_ids": set(),
        "favorite_items": [],
        "zhipu_api_key": "",
        "trend_granularity": "按年",
        "query_input": "large language model",
        "time_range": "全部",
        "filtered_message": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_api_key():
    return os.getenv("ZHIPU_API_KEY") or ACTIVE_ZHIPU_API_KEY or st.session_state.get("zhipu_api_key", "")


def get_zhipu_client():
    api_key = get_api_key()
    if not api_key:
        return None
    return ZhipuAI(api_key=api_key)


def call_zhipu(prompt, temperature=0.3):
    try:
        client = get_zhipu_client()
        if client is None:
            return "⚠️ 未检测到智谱 AI API Key。请设置环境变量 ZHIPU_API_KEY，或在侧边栏输入 API Key。"
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return f"⚠️ 智谱 AI 调用失败：{exc}"


def paper_id(paper):
    return paper.get("entry_id") or paper.get("title", "")


def format_authors(authors):
    if not authors:
        return ""
    if isinstance(authors, str):
        return authors
    return ", ".join(str(author) for author in authors)


def get_published_year(paper):
    published = paper.get("published", "")
    if hasattr(published, "year"):
        return str(published.year)
    parsed = pd.to_datetime(published, errors="coerce")
    if pd.isna(parsed):
        return "未知年份"
    return str(parsed.year)


def first_sentence(text):
    clean_text = " ".join(str(text).split())
    if not clean_text:
        return "暂无摘要信息。"
    match = re.search(r"(.+?[.!?。！？])\s", clean_text)
    return match.group(1) if match else clean_text[:220] + ("..." if len(clean_text) > 220 else "")


def parse_focus_keywords(text):
    return [item.strip().lower() for item in re.split(r"[,，;；]", text) if item.strip()]


def words_from_text(text):
    return set(re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower()))


def keyword_score(paper, focus_keywords):
    text_words = words_from_text(f"{paper.get('title', '')} {paper.get('summary', '')}")
    focus_words = set()
    for keyword in focus_keywords:
        focus_words.update(words_from_text(keyword))
    return len(text_words & focus_words)


def sort_papers_by_focus_keywords(papers, focus_keywords):
    if not focus_keywords:
        return papers
    return sorted(papers, key=lambda paper: keyword_score(paper, focus_keywords), reverse=True)


def time_range_days(time_range):
    return {
        "最近7天": 7,
        "最近30天": 30,
        "最近90天": 90,
    }.get(time_range)


def filter_papers_by_time_range(papers, time_range):
    days = time_range_days(time_range)
    if days is None:
        return papers, f"已筛选：{len(papers)}篇论文（全部）"

    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    filtered = []
    for paper in papers:
        published = pd.to_datetime(paper.get("published"), errors="coerce", utc=True)
        if not pd.isna(published) and published >= cutoff:
            filtered.append(paper)
    return filtered, f"已筛选：{len(filtered)}篇论文（最近{days}天）"


@st.cache_data(show_spinner=False)
def search_arxiv(query, max_results=10, sort_by="submitted"):
    sort_map = {
        "submitted": arxiv.SortCriterion.SubmittedDate,
        "relevance": arxiv.SortCriterion.Relevance,
        "last_updated": arxiv.SortCriterion.LastUpdatedDate,
    }
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=sort_map.get(sort_by, arxiv.SortCriterion.SubmittedDate),
        sort_order=arxiv.SortOrder.Descending,
    )
    client = arxiv.Client(page_size=max_results, delay_seconds=3, num_retries=3)

    last_error = None
    for attempt in range(3):
        try:
            papers = []
            for result in client.results(search):
                papers.append(
                    {
                        "title": result.title,
                        "summary": result.summary,
                        "authors": [author.name for author in result.authors],
                        "published": result.published,
                        "updated": result.updated,
                        "entry_id": result.entry_id,
                        "pdf_url": result.pdf_url,
                        "primary_category": result.primary_category,
                    }
                )
            return papers
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2)
    raise RuntimeError(f"arXiv 检索失败，已重试 2 次：{last_error}")


def summarize_paper(title, abstract):
    cache_key = f"{title}::summary"
    if cache_key in st.session_state.summary_cache:
        return st.session_state.summary_cache[cache_key]

    prompt = f"""
请对下面这篇论文做结构化中文总结：

标题：{title}

摘要：{abstract}

请包含：
1. 研究问题
2. 核心方法
3. 主要贡献
4. 实验或验证方式
5. 适合继续阅读的理由
"""
    result = call_zhipu(prompt, temperature=0.3)
    st.session_state.summary_cache[cache_key] = result
    return result


def ask_paper_question(title, abstract, question):
    prompt = f"""
你是论文阅读助手。请仅基于给定论文标题和摘要回答用户问题。

标题：{title}

摘要：{abstract}

用户问题：{question}
"""
    return call_zhipu(prompt, temperature=0.2)


def analyze_novelty(title, abstract):
    cache_key = f"{title}::novelty"
    if cache_key in st.session_state.novelty_cache:
        return st.session_state.novelty_cache[cache_key]

    prompt = f"""
请分析以下论文的创新点，重点说明它与 prior work 的区别、新方法、新发现或新应用场景。

标题：{title}

摘要：{abstract}

请用简洁中文列表输出，控制在 3-6 条。
"""
    result = call_zhipu(prompt, temperature=0.3)
    st.session_state.novelty_cache[cache_key] = result
    return result


def parse_keywords_response(result):
    if result.startswith("⚠️"):
        return [result]
    keywords = [
        re.sub(r"^[\d\-\.\)\s]+", "", item).strip()
        for item in re.split(r"[,;，；\n]", result)
    ]
    return [kw for kw in keywords if kw][:5]


def fetch_keywords_from_ai(title, abstract):
    prompt = f"""
请从下面论文中提取 3 到 5 个最能代表研究主题的英文关键词。
只返回关键词列表，用英文逗号分隔，不要解释。

标题：{title}

摘要：{abstract}
"""
    try:
        client = get_zhipu_client()
        if client is None:
            return ["⚠️ 未检测到智谱 AI API Key。"]
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return parse_keywords_response(response.choices[0].message.content.strip())
    except Exception as exc:
        return [f"⚠️ 关键词提取失败：{exc}"]


def extract_keywords(title, abstract):
    cache_key = f"{title}::keywords"
    if cache_key not in st.session_state.keyword_cache:
        st.session_state.keyword_cache[cache_key] = fetch_keywords_from_ai(title, abstract)
    return st.session_state.keyword_cache[cache_key]


def warn_keyword_failures():
    failed_count = sum(
        1
        for value in st.session_state.keyword_cache.values()
        if isinstance(value, list) and value and str(value[0]).startswith("⚠️")
    )
    if failed_count > 0:
        st.warning(f"有 {failed_count} 篇论文关键词提取失败，请检查 API Key、网络或接口额度。")


def ensure_keywords_cached(papers):
    pending = []
    for paper in papers:
        cache_key = f"{paper.get('title', '')}::keywords"
        if cache_key not in st.session_state.keyword_cache:
            pending.append((cache_key, paper.get("title", ""), paper.get("summary", "")))

    if not pending:
        st.info("关键词缓存已命中，无需重复调用 AI。")
        warn_keyword_failures()
        return

    st.write("图谱生成中，请稍候...")
    progress = st.progress(0, text="正在提取关键词...")
    done_count = 0
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {
            executor.submit(fetch_keywords_from_ai, title, abstract): cache_key
            for cache_key, title, abstract in pending
        }
        for future in as_completed(future_map):
            cache_key = future_map[future]
            try:
                st.session_state.keyword_cache[cache_key] = future.result()
            except Exception as exc:
                st.session_state.keyword_cache[cache_key] = [f"⚠️ 关键词提取失败：{exc}"]
            done_count += 1
            progress.progress(done_count / len(pending), text=f"关键词提取进度：{done_count}/{len(pending)}")
    progress.empty()
    warn_keyword_failures()


def show_relation_graph(papers):
    if not papers:
        st.info("暂无论文数据，请先检索论文。")
        return

    ensure_keywords_cached(papers)
    graph = nx.Graph()
    for idx, paper in enumerate(papers, start=1):
        title = paper["title"]
        paper_node = f"paper::{idx}"
        graph.add_node(
            paper_node,
            label=f"P{idx}",
            title=title,
            node_type="paper",
            color="#4C78A8",
        )

        keywords = [
            kw for kw in extract_keywords(title, paper.get("summary", ""))
            if kw and not kw.startswith("⚠️")
        ]
        for keyword in keywords:
            keyword_node = f"keyword::{keyword.lower()}"
            graph.add_node(
                keyword_node,
                label=keyword,
                title=keyword,
                node_type="keyword",
                color="#F58518",
            )
            graph.add_edge(paper_node, keyword_node)

    if graph.number_of_edges() == 0:
        st.warning("没有可用于生成图谱的关键词。")
        return

    net = Network(height="650px", width="100%", bgcolor="#ffffff", font_color="#222222")
    net.from_nx(graph)
    net.toggle_physics(True)
    net.set_options(
        """
        {
          "interaction": {"hover": true, "navigationButtons": true, "keyboard": true},
          "physics": {"barnesHut": {"gravitationalConstant": -18000, "springLength": 130}},
          "nodes": {"shape": "dot", "size": 18},
          "edges": {"color": {"color": "#B8B8B8"}}
        }
        """
    )
    components.html(net.generate_html(notebook=False), height=700, scrolling=True)


def build_wordcloud_text(summaries):
    stopwords = set(STOPWORDS) | STOPWORDS_EXTRA
    words = []
    for summary in summaries:
        for word in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", str(summary).lower()):
            word = word.strip("-")
            if word and word not in stopwords:
                words.append(word)
    return " ".join(words)


def normalize_published_column(df):
    if pd.api.types.is_datetime64_any_dtype(df["published"]):
        return df["published"]
    return pd.to_datetime(df["published"], errors="coerce")


def show_trend_analysis(papers):
    st.subheader("研究趋势分析")
    if not papers:
        st.info("暂无论文数据，请先检索论文。")
        return

    granularity = st.session_state.get("trend_granularity", "按年")
    chart_height = st.session_state.get("trend_chart_height", 420)
    df = pd.DataFrame(papers)
    df["published"] = normalize_published_column(df)
    df = df.dropna(subset=["published"])

    if df.empty:
        st.warning("论文数据中没有可解析的发布日期。")
    else:
        freq_map = {"按年": "YS", "按季度": "QS", "按月": "MS"}
        label_map = {"按年": "年份", "按季度": "季度", "按月": "月份"}
        trend_df = (
            df.set_index("published")
            .resample(freq_map[granularity])
            .size()
            .reset_index(name="paper_count")
        )
        trend_df = trend_df[trend_df["paper_count"] > 0]
        if granularity == "按年":
            trend_df["time_label"] = trend_df["published"].dt.strftime("%Y")
        elif granularity == "按季度":
            trend_df["time_label"] = (
                trend_df["published"].dt.year.astype(str)
                + "-Q"
                + trend_df["published"].dt.quarter.astype(str)
            )
        else:
            trend_df["time_label"] = trend_df["published"].dt.strftime("%Y-%m")

        fig = px.line(
            trend_df,
            x="time_label",
            y="paper_count",
            markers=True,
            labels={"time_label": label_map[granularity], "paper_count": "论文数"},
            title=f"论文数量变化趋势（{granularity}）",
        )
        fig.update_layout(hovermode="x unified", height=chart_height)
        st.plotly_chart(fig, use_container_width=True)

    text = build_wordcloud_text(df["summary"].tolist() if "summary" in df else [])
    if text:
        st.markdown("#### 摘要关键词词云")
        wordcloud = WordCloud(
            width=900,
            height=450,
            background_color="white",
            stopwords=set(STOPWORDS) | STOPWORDS_EXTRA,
            collocations=False,
        ).generate(text)
        fig_wc, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig_wc)
        plt.close(fig_wc)
    else:
        st.warning("摘要文本不足，暂时无法生成关键词词云。")


def generate_literature_review(papers, max_papers=5):
    selected = papers[:max_papers]
    paper_blocks = []
    for idx, paper in enumerate(selected, start=1):
        paper_blocks.append(
            f"论文 {idx}\n标题：{paper.get('title', '')}\n摘要：{paper.get('summary', '')[:1800]}"
        )

    prompt = f"""
你是学术研究助理。请基于以下论文标题和摘要，生成一份结构化中文文献综述。

要求包含以下部分：
1. 研究背景
2. 主流方法分类
3. 主要发现与贡献
4. 存在的问题与挑战
5. 未来研究方向

请避免逐篇机械复述，尽量综合归纳。

{chr(10).join(paper_blocks)}
"""
    return call_zhipu(prompt, temperature=0.3)


def generate_research_direction_summary(papers, max_papers=10):
    selected = papers[:max_papers]
    paper_blocks = []
    for idx, paper in enumerate(selected, start=1):
        paper_blocks.append(
            f"论文 {idx}\n标题：{paper.get('title', '')}\n摘要：{paper.get('summary', '')[:1200]}"
        )

    prompt = f"""
你是学术趋势分析助手。请基于以下论文列表，生成当前领域的研究方向总结。

输出 Markdown，包含：
1. 主要研究方向：3-5 个，每个方向附简短说明
2. 热点问题：2-3 个
3. 未来趋势：2-3 个

请综合归纳，不要逐篇复述。

{chr(10).join(paper_blocks)}
"""
    return call_zhipu(prompt, temperature=0.3)


def reviewer_analysis(selected_papers):
    cache_key = "::".join(paper_id(paper) for paper in selected_papers)
    if cache_key in st.session_state.review_cache:
        return st.session_state.review_cache[cache_key]

    paper_blocks = []
    for idx, paper in enumerate(selected_papers, start=1):
        paper_blocks.append(
            f"""
论文 {idx}
标题：{paper.get('title', '')}
作者：{format_authors(paper.get('authors', []))}
摘要：{paper.get('summary', '')[:1600]}
"""
        )

    prompt = f"""
你是一名严格但建设性的 AI Reviewer。请基于下面论文信息生成结构化审稿意见。
如果有多篇论文，请进行对比分析，指出哪些论文更强、差异点在哪里。

输出格式必须包含：
* Overall Assessment (Strengths / Weaknesses)
* Scores:
  - Novelty: 分数/10 + 简短理由
  - Technical Quality: 分数/10 + 简短理由
  - Clarity: 分数/10 + 简短理由
  - Experimental Design: 分数/10 + 简短理由
  - Impact: 分数/10 + 简短理由
* Final Recommendation: Accept / Weak Accept / Borderline / Reject
* Detailed Comments: 3-5 条具体建议

{chr(10).join(paper_blocks)}
"""
    result = call_zhipu(prompt, temperature=0.3)
    st.session_state.review_cache[cache_key] = result
    return result


def is_favorite(item_id):
    return any(item["id"] == item_id for item in st.session_state.favorite_items)


def add_favorite(paper):
    item_id = paper_id(paper)
    if is_favorite(item_id):
        return False
    st.session_state.favorite_items.append(
        {
            "id": item_id,
            "title": paper.get("title", "Untitled"),
            "entry_id": paper.get("entry_id", item_id),
            "pdf_url": paper.get("pdf_url", ""),
        }
    )
    return True


def render_paper_card(paper, idx):
    title = paper.get("title", "Untitled")
    summary = paper.get("summary", "")
    authors = format_authors(paper.get("authors", []))
    published = paper.get("published", "")
    published_text = published.strftime("%Y-%m-%d") if hasattr(published, "strftime") else str(published)
    year = get_published_year(paper)
    item_id = paper_id(paper)

    with st.expander(f"{idx}. {title}  ·  {year}", expanded=False):
        st.markdown(f'<div class="paper-oneline">{escape(first_sentence(summary))}</div>', unsafe_allow_html=True)

        selected = st.checkbox("选择用于 AI Reviewer 对比分析", key=f"select_{item_id}")
        if selected:
            st.session_state.selected_paper_ids.add(item_id)
        else:
            st.session_state.selected_paper_ids.discard(item_id)

        st.markdown(f"**作者：** {authors or '未知'}")
        st.markdown(f"**发布日期：** {published_text}")
        if paper.get("pdf_url"):
            st.markdown(f"**PDF：** [{paper['pdf_url']}]({paper['pdf_url']})")
        st.markdown("**摘要：**")
        st.markdown(f'<div class="paper-abstract">{escape(summary)}</div>', unsafe_allow_html=True)

        fav_col, info_col = st.columns([1, 4])
        with fav_col:
            if st.button("⭐ 收藏", key=f"favorite_{item_id}", disabled=is_favorite(item_id)):
                if add_favorite(paper):
                    st.success("已收藏")
                else:
                    st.info("已在收藏夹中")
        with info_col:
            if is_favorite(item_id):
                st.caption("已加入收藏夹")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("生成总结", key=f"summary_{item_id}"):
                with st.status("正在生成论文总结...", expanded=True) as status:
                    status.write("正在组织标题与摘要...")
                    status.write("正在调用智谱 AI...")
                    result = summarize_paper(title, summary)
                    status.update(label="论文总结已生成", state="complete")
                st.markdown(result)
        with col2:
            if st.button("💡 创新点分析", key=f"novelty_{item_id}"):
                with st.status("正在分析创新点...", expanded=True) as status:
                    status.write("正在对比研究问题与方法贡献...")
                    status.write("正在调用智谱 AI...")
                    result = analyze_novelty(title, summary)
                    status.update(label="创新点分析已生成", state="complete")
                st.markdown(result)

        question = st.text_input("向这篇论文提问", key=f"question_{item_id}")
        if st.button("回答问题", key=f"qa_{item_id}") and question:
            with st.status("正在回答论文问题...", expanded=True) as status:
                status.write("正在读取论文摘要...")
                status.write("正在调用智谱 AI...")
                answer = ask_paper_question(title, summary, question)
                status.update(label="回答已生成", state="complete")
            st.markdown(answer)


def render_favorites_sidebar():
    with st.sidebar.expander("⭐ 我的收藏"):
        if not st.session_state.favorite_items:
            st.caption("还没有收藏论文。")
            return
        for idx, item in enumerate(st.session_state.favorite_items, start=1):
            title = item.get("title", "Untitled").replace("[", "").replace("]", "")
            url = item.get("entry_id") or item.get("pdf_url") or "#"
            st.markdown(f"{idx}. [{title}]({url})")


def render_iteration_notes():
    st.sidebar.markdown("### 迭代说明")
    with st.sidebar.expander("📘 设计亮点与迭代过程"):
        st.markdown(
            """
**设计亮点**

- 多维度排序：先由 arXiv 返回候选论文，再按用户关注关键词在标题和摘要中的命中情况重排。
- AI 增强图谱：用智谱 AI 抽取关键词，构建论文-关键词二分网络，支持缩放和悬停查看。
- 一键综述生成：按当前排序后的前 N 篇论文自动生成结构化文献综述。
- 单篇深读：每篇论文支持总结、问答和创新点分析，适合快速筛选与精读。
- 缓存优化：搜索结果、关键词、总结、创新点和 Reviewer 分析都进入 session 缓存，减少重复请求。

**迭代过程**

- v0.1：完成 arXiv 检索和论文列表展示。
- v0.2：加入单篇论文总结、问答和基础排序。
- v0.3：加入研究趋势分析、年度折线图和摘要词云。
- v0.4：加入论文关系图谱、关键词缓存和文献综述生成。
- v0.5：加入 AI Reviewer、创新点分析、API Key 安全输入、关键词排序和并发限流。
- v0.6：加入最新论文追踪、研究方向总结、收藏夹和 HTML 报告导出。
"""
        )


def render_sidebar():
    st.sidebar.markdown("### 检索设置")
    query = st.sidebar.text_input(
        "arXiv 查询关键词",
        key="query_input",
        help="输入英文关键词或 arXiv 查询表达式，例如 large language model、RAG、diffusion model。",
    )
    max_results = st.sidebar.slider(
        "最大论文数量",
        min_value=5,
        max_value=50,
        value=10,
        step=5,
        help="控制从 arXiv 返回的论文数量。数量越多，AI 分析和图谱生成耗时越长。",
    )
    time_range = st.sidebar.radio(
        "时间范围",
        ["全部", "最近7天", "最近30天", "最近90天"],
        key="time_range",
        help="检索后基于 published 字段过滤最新论文。",
    )
    sort_by = st.sidebar.selectbox(
        "arXiv 初始排序",
        options=["submitted", "relevance", "last_updated"],
        format_func=lambda x: {"submitted": "提交时间", "relevance": "相关性", "last_updated": "更新时间"}[x],
        help="这是 arXiv 返回结果的初始排序，之后还会按关注关键词重新排序。",
    )

    st.sidebar.markdown("### 排序与趋势")
    focus_text = st.sidebar.text_input(
        "关注关键词（逗号分隔）",
        value="transformer, LLM, diffusion",
        help="系统会按这些关键词在标题和摘要中的命中情况，对论文进行降序排序。",
    )
    show_trend = st.sidebar.checkbox(
        "显示研究趋势",
        help="显示按时间粒度统计的论文数量变化，以及摘要关键词词云。",
    )
    st.sidebar.radio(
        "趋势时间粒度",
        ["按年", "按季度", "按月"],
        key="trend_granularity",
        help="选择研究趋势折线图的时间聚合粒度。",
    )
    st.sidebar.slider(
        "趋势图高度",
        min_value=320,
        max_value=720,
        value=420,
        step=40,
        key="trend_chart_height",
        help="调整趋势折线图的显示高度。",
    )

    st.sidebar.markdown("### 智谱 AI")
    env_has_key = bool(os.getenv("ZHIPU_API_KEY"))
    if env_has_key:
        st.sidebar.success("已从环境变量读取 ZHIPU_API_KEY。")
    else:
        st.session_state.zhipu_api_key = st.sidebar.text_input(
            "ZHIPU_API_KEY",
            value=st.session_state.zhipu_api_key,
            type="password",
            help="不会写入代码，仅保存在当前 Streamlit 会话中。",
        )

    if st.sidebar.button("测试连接", help="发送一个极短 prompt，验证智谱 AI 是否可用。"):
        with st.sidebar.status("正在测试智谱 AI 连接...", expanded=True) as status:
            status.write("正在读取 API Key...")
            status.write("正在发送测试请求...")
            result = call_zhipu("请回复：连接成功", temperature=0.1)
            if result.startswith("⚠️"):
                status.update(label="连接测试失败", state="error")
                st.sidebar.error(result)
            else:
                status.update(label="连接测试成功", state="complete")
                st.sidebar.success(result)

    render_favorites_sidebar()
    render_iteration_notes()
    return query, max_results, sort_by, focus_text, show_trend, time_range


def render_empty_state():
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-icon">📄</div>
            <h3>输入关键词开始探索</h3>
            <p>从 arXiv 检索论文后，可继续生成趋势图谱、文献综述和 AI Reviewer 分析。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("**示例关键词**")
    examples = ["large language model", "retrieval augmented generation", "diffusion model"]
    cols = st.columns(len(examples))
    for col, example in zip(cols, examples):
        with col:
            if st.button(example, key=f"example_{example}"):
                st.session_state.query_input = example
                st.rerun()


def render_back_to_top_button():
    st.markdown(
        """
        <a class="back-to-top" href="#top" onclick="window.scrollTo({top: 0, behavior: 'smooth'}); return false;">
            ↑ 回到顶部
        </a>
        """,
        unsafe_allow_html=True,
    )


def truncate_text(text, max_len=200):
    text = " ".join(str(text).split())
    return text[:max_len] + ("..." if len(text) > max_len else "")


def generate_report_html(query, time_range, papers, literature_review, direction_summary, reviewer_result):
    date_text = datetime.now().strftime("%Y-%m-%d")
    paper_items = []
    for idx, paper in enumerate(papers[:10], start=1):
        title = escape(paper.get("title", "Untitled"))
        authors = escape(format_authors(paper.get("authors", [])) or "未知")
        summary = escape(truncate_text(paper.get("summary", ""), 200))
        link = escape(paper.get("entry_id", ""))
        paper_items.append(
            f"""
            <section class="paper">
              <h3>{idx}. {title}</h3>
              <p><strong>Authors:</strong> {authors}</p>
              <p><strong>Link:</strong> <a href="{link}">{link}</a></p>
              <p>{summary}</p>
            </section>
            """
        )

    def optional_section(title, content):
        if not content:
            return ""
        return f"<section><h2>{escape(title)}</h2><pre>{escape(content)}</pre></section>"

    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Research Report - {escape(query)}</title>
  <style>
    body {{
      margin: 0;
      padding: 32px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #1F2937;
      background: #f5f7fa;
      line-height: 1.6;
    }}
    .container {{
      max-width: 960px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      padding: 32px;
      box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
    }}
    h1, h2, h3 {{ color: #1E3A8A; }}
    a {{ color: #3B82F6; }}
    .meta {{
      background: #f8fafc;
      border-left: 4px solid #3B82F6;
      padding: 12px 16px;
      border-radius: 8px;
      margin-bottom: 24px;
    }}
    .paper {{
      border-top: 1px solid #e5e7eb;
      padding-top: 16px;
      margin-top: 16px;
    }}
    pre {{
      white-space: pre-wrap;
      background: #f8fafc;
      border-radius: 8px;
      padding: 16px;
      font-family: inherit;
      font-size: 14px;
    }}
    @media print {{
      body {{ background: #ffffff; padding: 0; }}
      .container {{ box-shadow: none; border-radius: 0; }}
      a {{ color: #1E3A8A; text-decoration: none; }}
    }}
  </style>
</head>
<body>
  <main class="container">
    <h1>论文阅读助手研究报告</h1>
    <div class="meta">
      <p><strong>检索关键词：</strong>{escape(query)}</p>
      <p><strong>时间范围：</strong>{escape(time_range)}</p>
      <p><strong>论文数量：</strong>{len(papers)}</p>
      <p><strong>生成日期：</strong>{date_text}</p>
    </div>
    {optional_section("文献综述", literature_review)}
    {optional_section("研究方向总结", direction_summary)}
    <section>
      <h2>前 10 篇论文</h2>
      {''.join(paper_items)}
    </section>
    {optional_section("AI Reviewer 分析", reviewer_result)}
  </main>
</body>
</html>
"""


def main():
    global ACTIVE_ZHIPU_API_KEY

    init_state()
    apply_custom_css()

    st.markdown('<div id="top"></div>', unsafe_allow_html=True)
    st.title("论文阅读助手")
    st.caption("arXiv 检索、论文总结、趋势分析、关系图谱、文献综述与 AI Reviewer")

    query, max_results, sort_by, focus_text, show_trend, time_range = render_sidebar()
    ACTIVE_ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY") or st.session_state.get("zhipu_api_key", "")
    focus_keywords = parse_focus_keywords(focus_text)

    if not get_api_key():
        st.error("请先设置环境变量 ZHIPU_API_KEY，或在侧边栏输入智谱 AI API Key。")
        st.stop()

    st.markdown('<div class="toolbar-card">', unsafe_allow_html=True)
    top_col1, top_col2, top_col3, top_col4 = st.columns([1, 1.35, 1, 1])
    with top_col1:
        search_clicked = st.button("检索论文", type="primary", use_container_width=True)
    with top_col2:
        review_count = st.slider(
            "综述论文数量",
            min_value=1,
            max_value=max_results,
            value=min(5, max_results),
            help="按当前排序后的前 N 篇论文生成文献综述。",
        )
        review_clicked = st.button("生成文献综述", use_container_width=True)
    with top_col3:
        graph_clicked = st.button("生成关系图谱", use_container_width=True)
    with top_col4:
        export_clicked = st.button("📄 导出研究报告", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if search_clicked:
        if not query.strip():
            st.warning("请输入检索关键词。")
        else:
            with st.status("正在检索论文...", expanded=True) as status:
                try:
                    status.write("正在连接 arXiv...")
                    raw_papers = search_arxiv(query.strip(), max_results, sort_by)
                    status.write("正在按时间范围筛选...")
                    filtered_papers, filtered_message = filter_papers_by_time_range(raw_papers, time_range)
                    status.write("正在按关注关键词排序...")
                    st.session_state.papers = sort_papers_by_focus_keywords(filtered_papers, focus_keywords)
                    st.session_state.filtered_message = filtered_message
                    st.session_state.last_query = query.strip()
                    st.session_state.selected_paper_ids = set()
                    st.session_state.reviewer_result = ""
                    st.session_state.literature_review = ""
                    st.session_state.direction_summary = ""
                    st.session_state.report_html = ""
                    status.update(label="检索完成，已按时间范围筛选并按关注关键词排序", state="complete")
                except Exception as exc:
                    status.update(label="检索失败", state="error")
                    st.error(str(exc))
                    st.session_state.papers = []

    papers = st.session_state.papers

    if export_clicked:
        st.session_state.report_html = generate_report_html(
            query=st.session_state.last_query or query,
            time_range=time_range,
            papers=papers,
            literature_review=st.session_state.literature_review,
            direction_summary=st.session_state.direction_summary,
            reviewer_result=st.session_state.reviewer_result,
        )

    if st.session_state.report_html:
        st.download_button(
            "下载 HTML 研究报告",
            st.session_state.report_html,
            file_name=f"research_report_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html",
        )

    if not papers:
        render_empty_state()
        return

    if st.session_state.filtered_message:
        st.success(st.session_state.filtered_message)
    if focus_keywords:
        st.info("已按关注关键词排序。")

    if review_clicked:
        with st.status(f"正在生成前 {review_count} 篇论文的文献综述...", expanded=True) as status:
            status.write("正在拼接标题与摘要...")
            status.write("正在调用智谱 AI...")
            st.session_state.literature_review = generate_literature_review(papers, max_papers=review_count)
            status.update(label="文献综述已生成", state="complete")

    if st.session_state.literature_review:
        with st.expander("文献综述", expanded=True):
            st.markdown(st.session_state.literature_review)
            st.download_button(
                "下载为 Markdown",
                st.session_state.literature_review,
                file_name="literature_review.md",
                mime="text/markdown",
            )

    st.markdown(f"### 找到 {len(papers)} 篇论文（已排序）")

    if show_trend:
        trend_col, summary_col = st.columns([2, 1])
        with trend_col:
            show_trend_analysis(papers)
        with summary_col:
            st.subheader("研究方向")
            if st.button("📊 研究方向总结", use_container_width=True):
                with st.status("正在生成研究方向总结...", expanded=True) as status:
                    status.write("正在整理当前论文列表...")
                    status.write("正在调用智谱 AI...")
                    st.session_state.direction_summary = generate_research_direction_summary(papers, max_papers=10)
                    status.update(label="研究方向总结已生成", state="complete")
            if st.session_state.direction_summary:
                with st.expander("研究方向总结", expanded=True):
                    st.markdown(st.session_state.direction_summary)

    if graph_clicked:
        with st.status("正在生成论文关系图谱...", expanded=True) as status:
            status.write("正在检查关键词缓存...")
            status.write("正在构建二分网络...")
            show_relation_graph(papers)
            status.update(label="论文关系图谱已生成", state="complete")

    for idx, paper in enumerate(papers, start=1):
        render_paper_card(paper, idx)

    st.markdown("---")
    if st.button("🧑‍⚖️ AI Reviewer 分析"):
        selected = [paper for paper in papers if paper_id(paper) in st.session_state.selected_paper_ids]
        if not selected:
            selected = papers
        with st.status("正在生成 AI Reviewer 分析...", expanded=True) as status:
            status.write("正在整理选中论文...")
            status.write("正在调用智谱 AI...")
            st.session_state.reviewer_result = reviewer_analysis(selected)
            status.update(label="AI Reviewer 分析已生成", state="complete")

    if st.session_state.reviewer_result:
        with st.expander("AI Reviewer 分析结果", expanded=True):
            st.markdown(st.session_state.reviewer_result)

    if len(papers) > 10:
        render_back_to_top_button()


if __name__ == "__main__":
    main()
