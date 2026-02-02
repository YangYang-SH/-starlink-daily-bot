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
    """搜索 Starlink 最新新闻 (优化版：精简 Token 占用)"""
    print("正在搜索 Starlink 最新资讯...")
    results = []
    
    with DDGS() as ddgs:
        keywords = "SpaceX Starlink news latest technology"
        # 修改点 1: 将 max_results 从 10 减少到 5，大幅降低 Token 消耗
        news_gen = ddgs.news(keywords, region="wt-wt", safesearch="off", timelimit="d", max_results=5)
        
        for r in news_gen:
            # 修改点 2: 只提取 'title', 'date', 'body' 关键字段
            # 原始结果包含 url, image, source_url 等大量非必要 Token
            title = r.get('title', 'No Title')
            date = r.get('date', '')
            body = r.get('body', '') # 新闻摘要
            
            # 修改点 3: 强制截断摘要长度
            # 如果摘要超过 150 个字符，只取前 150 个，后面加省略号
            if len(body) > 150:
                body = body[:150] + "..."
            
            # 修改点 4: 格式化为纯文本字符串，而不是字典
            # 去掉 JSON 的大括号 {} 和引号 ""，这是最节省 Token 的格式
            clean_item = f"Date: {date}\nTitle: {title}\nSummary: {body}"
            
            results.append(clean_item)
    
    # 修改点 5: 将列表合并为一个长字符串返回
    # 这样调用 API 时直接把这个字符串传进去即可
    final_text = "\n---\n".join(results)
    
    # (可选) 修改点 6: 双重保险，确保总长度不超过限制（例如 2000 字符）
    if len(final_text) > 3000:
        final_text = final_text[:3000] + "\n...(内容已截断)"
        
    return final_text

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




