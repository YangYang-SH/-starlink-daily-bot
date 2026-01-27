# main.py
import os
import datetime
import google.generativeai as genai
from duckduckgo_search import DDGS

# 配置 Gemini API
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("未找到 GEMINI_API_KEY")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash') # 或者使用 gemini-pro

def get_starlink_news():
    """搜索 Starlink 最新新闻"""
    print("正在搜索 Starlink 最新资讯...")
    results = []
    # 使用 DuckDuckGo 搜索过去24小时的新闻
    with DDGS() as ddgs:
        # keywords: 搜索关键词, region: 地区, safesearch: 安全搜索, timelimit: 时间限制(d=day)
        keywords = "SpaceX Starlink news latest technology"
        news_gen = ddgs.news(keywords, region="wt-wt", safesearch="off", timelimit="d", max_results=10)
        for r in news_gen:
            results.append(r)
    return results

def generate_report(news_items):
    """使用 Gemini 分析并生成报告"""
    print("正在调用 Gemini 进行分析...")
    
    # 构建提示词 (Prompt)
    news_text = ""
    for idx, item in enumerate(news_items, 1):
        news_text += f"{idx}. 标题: {item['title']}\n   摘要: {item['body']}\n   链接: {item['url']}\n   来源: {item['source']}\n   时间: {item['date']}\n\n"

    prompt = f"""
    你是一个资深的科技行业分析师。请根据以下收集到的关于 "Starlink (星链)" 的最新互联网新闻，用中文写一份深度日报。

    输入的新闻资讯如下：
    {news_text}

    请按照以下 Markdown 格式输出报告（不要包含 Markdown 代码块标记 ```）：

    # 🛰️ Starlink 每日观察报告 ({datetime.date.today()})

    ## 1. 核心分析
    (在这里对新闻进行深度解读，分析其对卫星通讯行业、SpaceX 战略或全球网络的影响。不要只是翻译，要给出见解。)

    ## 2. 资讯总结
    (分点总结发生的关键事件，语言简练。)

    ## 3. 原始资讯与出处
    (列出原始新闻的标题和链接，方便读者查阅。)
    """

    response = model.generate_content(prompt)
    return response.text

def save_report(content):
    """保存报告到文件"""
    today = datetime.date.today().isoformat()
    filename = f"reports/Starlink_Report_{today}.md"
    
    # 确保目录存在
    os.makedirs("reports", exist_ok=True)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    
    # 更新 README.md 显示最新报告
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(f"# Starlink 每日追踪\n\n最新更新时间: {today}\n\n{content}")
        
    print(f"报告已保存至 {filename}")

def main():
    try:
        news = get_starlink_news()
        if not news:
            print("未找到相关新闻，跳过生成。")
            return
            
        report = generate_report(news)
        save_report(report)
        
    except Exception as e:
        print(f"发生错误: {e}")
        raise e

if __name__ == "__main__":
    main()
