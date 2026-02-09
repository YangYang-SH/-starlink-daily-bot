# main.py

import os
import time
import datetime
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from duckduckgo_search import DDGS

# 配置 Gemini API
API_KEY = os.getenv("GEMINI_API_KEY")

# 建议：优先使用稳定版模型，如果报错再尝试 2.0
MODEL_NAME = 'gemini-2.0-flash' 
# MODEL_NAME = 'gemini-1.5-flash'

def get_starlink_news():
    """搜索 Starlink 最新新闻"""
    print("正在搜索 Starlink 最新资讯...")
    results = []
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            with DDGS() as ddgs:
                keywords = "SpaceX Starlink news latest technology"
                # timelimit='d' 表示过去一天，确保新闻新鲜
                news_gen = ddgs.news(keywords, region="wt-wt", safesearch="off", timelimit="d", max_results=5)
                
                for r in news_gen:
                    title = r.get('title', 'No Title')
                    date = r.get('date', '')
                    body = r.get('body', r.get('snippet', '')) 
                    
                    if len(body) > 150:
                        body = body[:150] + "..."
                    
                    clean_item = f"Date: {date}\nTitle: {title}\nSummary: {body}"
                    results.append(clean_item)
            if results: # 只有找到结果才跳出
                break 
        except Exception as e:
            print(f"DuckDuckGo 搜索尝试 {attempt + 1}/{max_retries} 失败: {e}")
            time.sleep(2)

    if not results:
        return ""

    final_text = "\n---\n".join(results)
    if len(final_text) > 3000:
        final_text = final_text[:3000] + "\n...(内容已截断)"
    return final_text

def generate_report(news_text):
    """生成分析报告 (修复重试逻辑版)"""
    if not API_KEY:
        print("错误：未找到 API Key")
        return None

    print(f"正在调用 Gemini ({MODEL_NAME}) 进行分析...")
    
    if not news_text or len(news_text) < 10:
        return "未搜索到相关 Starlink 新闻，跳过分析。"

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

    # --- 关键优化 1: 显式配置 Transport ---
    # 在某些网络环境下（特别是使用代理时），GRPC 可能会失败。强制使用 REST 往往更稳定。
    try:
        genai.configure(api_key=API_KEY, transport='rest')
    except Exception as e:
        print(f"配置 Gemini 失败: {e}")
        return None

    model = genai.GenerativeModel(MODEL_NAME)

    # --- 关键优化 2: 修正重试延迟单位 ---
    max_retries = 3
    base_delay = 2  # 修改为 2 秒 (原先 1000 秒太久了)
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            
            # 获取 Token 统计
            input_tokens = "未知"
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                print(f"API 调用成功! 消耗输入 Token: {input_tokens}")
            
            return response.text + f"\n\n---\n*Model: {MODEL_NAME} | Input Tokens: {input_tokens}*"
            
        except Exception as e:
            error_str = str(e)
            print(f"第 {attempt + 1} 次调用失败。错误信息: {error_str}")
            
            # 检查是否值得重试 (429: Too Many Requests, 503: Service Unavailable)
            # 也可以捕获 google_exceptions.ResourceExhausted
            if "429" in error_str or "503" in error_str or "ResourceExhausted" in error_str:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt) # 2s, 4s, 8s...
                    print(f"触发流控/服务繁忙，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    return f"错误：重试 {max_retries} 次后仍然失败。可能是 API 配额耗尽或服务宕机。\n详细错误: {error_str}"
            elif "404" in error_str:
                 return f"错误：模型 {MODEL_NAME} 未找到。请检查代码中的 MODEL_NAME 是否正确 (例如 gemini-1.5-flash)。"
            else:
                # 其他错误（如 400 参数错误，403 权限错误）重试也没用，直接返回
                return f"API 调用发生不可恢复错误: {error_str}"
    
    return "未知流程错误"

def save_report(content):
    if not content:
        return
    today = datetime.date.today().isoformat()
    os.makedirs("reports", exist_ok=True)
    filename = f"reports/Starlink_Report_{today}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"报告已保存至 {filename}")

def main():
    news = get_starlink_news()
    report = generate_report(news)
    if report:
        save_report(report)
        print("流程结束。")
    else:
        print("生成失败，未保存报告。")

if __name__ == "__main__":
    main()
