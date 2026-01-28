# FOMC Press Conference Transcript Monitor

一个用于抓取和展示FOMC（联邦公开市场委员会）新闻发布会转录稿的网站。自动将PDF格式的转录稿转换为HTML格式以便在线查看。

## 功能特点

- 📥 自动下载FOMC新闻发布会PDF文件
- 🔄 将PDF转换为HTML格式
- 🌐 美观的网页界面展示转录稿列表
- 🔍 搜索功能，可按日期、年份或关键词筛选
- 📱 响应式设计，支持移动设备

## 安装步骤

1. **创建虚拟环境并安装依赖**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **运行爬虫脚本**
```bash
source venv/bin/activate
python3 scraper.py
```

**注意**: 每次运行脚本前需要先激活虚拟环境：`source venv/bin/activate`

## 使用方法

### 1. 添加转录稿

编辑 `scraper.py` 文件，在 `main()` 函数中添加要抓取的转录稿：

```python
transcripts_to_add = [
    {
        "date": "2024-12-18",
        "title": "December 2024 FOMC Press Conference",
        "pdf_url": "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20241218.pdf"  # 可选：直接提供PDF链接
    },
]
```

如果不提供 `pdf_url`，脚本会尝试自动查找PDF链接。

### 2. 查看网站

启动本地服务器：
```bash
python3 -m http.server 8080
```

然后在浏览器中访问：`http://localhost:8080`

## 文件结构

```
Fedspeak Monitor/
├── index.html              # 主页面
├── scraper.py              # 爬虫和转换脚本
├── requirements.txt        # Python依赖
├── data/
│   ├── transcripts.json   # 转录稿元数据
│   ├── pdfs/              # 下载的PDF文件
│   └── htmls/             # 转换后的HTML文件
└── README.md              # 说明文档
```

## 数据格式

`data/transcripts.json` 文件包含所有转录稿的元数据：

```json
[
  {
    "date": "2024-12-18",
    "title": "December 2024 FOMC Press Conference",
    "pdf_url": "https://...",
    "pdf_path": "data/pdfs/fomc_2024-12-18.pdf",
    "html_path": "data/htmls/fomc_2024-12-18.html",
    "scraped_at": "2024-01-01T12:00:00"
  }
]
```

## 注意事项

- PDF链接需要手动查找或提供
- 转换后的HTML会保留原始文本格式
- 建议定期运行爬虫脚本更新最新转录稿

## 技术栈

- **Python 3**: 爬虫和PDF处理
- **pdfplumber**: PDF文本提取
- **requests**: HTTP请求
- **HTML/CSS/JavaScript**: 前端界面
