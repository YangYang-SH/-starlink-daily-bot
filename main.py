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

def generate_report(news_text):
    """
    生成分析报告
    参数 news_text: 已经是格式化好的字符串，不需要再循环处理
    """
    print("正在调用 Gemini 进行分析...")
    
    # 1. 检查是否有内容
    if not news_text or "No Title" in news_text and len(news_text) < 50:
        return "未搜索到相关 Starlink 新闻。"

    # 2. 构造 Prompt
    # 注意：这里不需要再 for 循环拼接了，因为 news_text 已经是拼好的字符串
    prompt = f"""
请扮演一位专业的科技新闻分析师。基于以下关于 Starlink (星链) 的最新新闻资讯，用中文写一份简短的日报。

要求：
1. 提炼 3 个最重要的核心动态。
2. 语气专业、简洁。
3. 如果内容包含技术突破或发射任务，请重点标注。

--- 新闻内容 ---
{news_text}
"""

    try:
        # 3. 调用 API (请根据你实际使用的模型变量名调整，例如 model 或 genai)
        # 假设你在外部初始化了 model，如果没有，请在这里初始化
        # model = genai.GenerativeModel('gemini-2.0-flash') 
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"Gemini API 调用错误: {e}")
        # 如果是配额错误，可以返回友好的提示
        if "429" in str(e):
            return "错误：API 调用过于频繁 (429)，请稍后再试。"
        return f"生成报告时发生错误: {e}"

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





