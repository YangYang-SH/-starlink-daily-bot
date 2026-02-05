# main.py

import os
import time
import datetime
import google.generativeai as genai
from duckduckgo_search import DDGS

# 配置 Gemini API
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    # 建议：在这里不直接抛出异常，允许在 CI/CD 中通过打印日志排查
    print("警告: 未找到 GEMINI_API_KEY，后续生成步骤将失败")

# 建议：模型名称提取为常量，方便修改
MODEL_NAME = 'gemini-2.0-flash'  

def get_starlink_news():
    """搜索 Starlink 最新新闻 (优化版)"""
    print("正在搜索 Starlink 最新资讯...")
    results = []
    
    # 增加简单的重试机制，应对 DDGS 的网络抖动
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with DDGS() as ddgs:
                keywords = "SpaceX Starlink news latest technology"
                # 注意：ddgs.news 的参数随版本变化较大，保持关注
                news_gen = ddgs.news(keywords, region="wt-wt", safesearch="off", timelimit="d", max_results=5)
                
                for r in news_gen:
                    title = r.get('title', 'No Title')
                    date = r.get('date', '')
                    # 兼容不同版本的字段名 (body 或 snippet)
                    body = r.get('body', r.get('snippet', '')) 
                    
                    if len(body) > 150:
                        body = body[:150] + "..."
                    
                    clean_item = f"Date: {date}\nTitle: {title}\nSummary: {body}"
                    results.append(clean_item)
            break # 成功则跳出循环
        except Exception as e:
            print(f"搜索尝试 {attempt + 1}/{max_retries} 失败: {e}")
            time.sleep(2) # 等待 2 秒后重试

    if not results:
        return ""

    final_text = "\n---\n".join(results)
    
    # 双重保险
    if len(final_text) > 3000:
        final_text = final_text[:3000] + "\n...(内容已截断)"
        
    return final_text

def generate_report(news_text):
    """生成分析报告 (包含重试机制)"""
    if not API_KEY:
        return "错误：未配置 API Key，无法生成报告。"

    print("正在调用 Gemini 进行分析...")
    
    if not news_text or len(news_text) < 10:
        return "未搜索到相关 Starlink 新闻。"

    prompt = f"""
请扮演一位专业的科技新闻分析师。基于以下关于 Starlink (星链) 的最新新闻资讯，用中文写一份简短的日报。

要求：
1. 提炼 3 个最重要的核心动态。
2. 语气专业、简洁。
3. 如果内容包含技术突破或发射任务，请重点标注。
4. 输出格式为 Markdown。

--- 新闻内容 ---
{news_text}
"""

    # 配置 API (只需配置一次，建议放在循环外)
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        return f"配置 Gemini 失败: {e}"

    # --- 重试逻辑开始 ---
    max_retries = 3
    base_delay = 100  # 基础等待 100 秒
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            error_str = str(e)
            # 检查是否为 429 (Resource Exhausted) 或 503 (Service Unavailable)
            if "429" in error_str or "503" in error_str:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt) # 指数退避: 100s, 200s, 400s
                    print(f"API 繁忙 (429/503)，{wait_time} 秒后进行第 {attempt + 2} 次重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    return "错误：API 调用过于频繁，重试多次后仍然失败。请检查配额或稍后再试。"
            elif "404" in error_str:
                 return f"错误：模型 {MODEL_NAME} 未找到，请检查模型名称是否正确。"
            else:
                # 其他错误直接返回，不重试
                return f"生成报告时发生错误: {e}"
    # --- 重试逻辑结束 ---
    
    return "未知错误。"

def save_report(content):
    """保存报告"""
    today = datetime.date.today().isoformat()
    # 确保目录存在
    os.makedirs("reports", exist_ok=True)
    
    filename = f"reports/Starlink_Report_{today}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"报告已保存至 {filename}")
    
    # 更新 README (此处保持你的逻辑，即覆盖模式)
    try:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(f"# Starlink 每日追踪\n\n最新更新时间: {today}\n\n{content}")
    except Exception as e:
        print(f"更新 README 失败: {e}")

def main():
    try:
        news = get_starlink_news()
        if not news:
            print("未找到相关新闻，跳过生成。")
            # 即使没新闻，也可以选择生成一个'今日无新闻'的报告
            return
            
        report = generate_report(news)
        save_report(report)
        
    except Exception as e:
        print(f"主程序发生严重错误: {e}")
        # 在 GitHub Actions 等环境中，exit(1) 可以让 Workflow 显示失败
        exit(1)

if __name__ == "__main__":
    main()


