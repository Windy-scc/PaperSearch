# 论文阅读助手

一个基于 Streamlit、arXiv 和智谱 AI 的论文检索与阅读辅助工具。项目支持论文搜索、关键词排序、单篇论文总结、创新点分析、研究趋势分析、论文关系图谱、文献综述生成、AI Reviewer 分析、收藏夹和 HTML 研究报告导出。

## 功能特性

- **arXiv 论文检索**：输入关键词后自动检索论文，并支持按提交时间、相关性、更新时间排序。
- **关注关键词排序**：根据用户设置的关注关键词，对论文标题和摘要进行匹配排序。
- **最新论文追踪**：支持按全部、最近 7 天、最近 30 天、最近 90 天过滤论文。
- **单篇论文辅助阅读**：支持论文总结、论文问答和创新点分析。
- **研究趋势分析**：支持按年、季度、月统计论文数量变化，并生成摘要关键词词云。
- **论文关系图谱**：调用智谱 AI 提取关键词，构建“论文-关键词”二分网络图。
- **自动生成文献综述**：基于当前排序后的前 N 篇论文生成结构化综述。
- **研究方向总结**：总结主要研究方向、热点问题和未来趋势。
- **AI Reviewer 分析**：对单篇或多篇论文生成结构化审稿意见和对比分析。
- **论文收藏夹**：在当前会话中收藏感兴趣论文。
- **HTML 报告导出**：导出包含检索信息、综述、研究方向、论文摘要和 Reviewer 结果的研究报告。

## 项目结构

```text
research_agent/
├── app.py              # Streamlit 主程序
├── paper_search.py     # 论文搜索相关辅助代码
├── requirements.txt    # Python 依赖
├── Dockerfile          # Docker 部署文件
└── README.md           # 项目说明
```

## 环境要求

- Python 3.9 或更高版本
- 智谱 AI API Key

## 安装依赖

建议先创建虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell：

```bash
.venv\Scripts\Activate.ps1
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 配置智谱 AI API Key

推荐使用环境变量配置：

Windows PowerShell：

```powershell
$env:ZHIPU_API_KEY="你的智谱AI API Key"
```

如果没有配置环境变量，也可以在应用左侧边栏的密码输入框中填写 API Key。该方式只保存在当前 Streamlit 会话中，不会写入代码。

## 启动应用

```bash
streamlit run app.py
```

启动后浏览器会打开本地页面，通常地址为：

```text
http://localhost:8501
```

## 使用流程

1. 在侧边栏输入 arXiv 查询关键词。
2. 设置最大论文数量、时间范围和关注关键词。
3. 点击“检索论文”。
4. 在主页面查看排序后的论文列表。
5. 根据需要生成文献综述、研究趋势、关系图谱、研究方向总结或 AI Reviewer 分析。
6. 对感兴趣的论文点击“⭐ 收藏”。
7. 点击“📄 导出研究报告”下载 HTML 报告。

## Docker 运行

构建镜像：

```bash
docker build -t paper-reading-assistant .
```

运行容器：

```bash
docker run -p 8501:8501 -e ZHIPU_API_KEY="你的智谱AI API Key" paper-reading-assistant
```

然后访问：

```text
http://localhost:8501
```

## 注意事项

- arXiv 检索依赖网络连接。
- 智谱 AI 相关功能需要有效的 `ZHIPU_API_KEY`。
- 关键词提取、文献综述、研究方向总结和 Reviewer 分析都会调用 AI 接口，可能产生 API 调用费用。
- 收藏夹基于 `st.session_state`，刷新页面或重启应用后可能丢失。
- 关系图谱会缓存关键词提取结果，避免重复调用 AI。

## 依赖列表

主要依赖包括：

- streamlit
- arxiv
- zhipuai
- pandas
- plotly
- networkx
- pyvis
- wordcloud
- matplotlib

完整版本要求见 `requirements.txt`。
