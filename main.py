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
# MODEL_NAME = 'gemini-2.0-flash' 
# MODEL_NAME = 'gemini-1.5-flash'
MODEL_NAME = 'gemini-2.5-flash' 


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
    """生成分析报告 (优化版：包含失败时的 Token 统计)"""
    if not API_KEY:
        return "错误：未配置 API Key，无法生成报告。"

    print("正在准备调用 Gemini 进行分析...")
    
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

    # 配置 API
    try:
        # 建议添加 transport='rest' 以提高在国内网络环境下的稳定性
        genai.configure(api_key=API_KEY, transport='rest')
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        return f"配置 Gemini 失败: {e}"

    # --- 步骤 1: 预先计算 Token 数 (关键步骤) ---
    input_token_count = "未知"
    try:
        # 这是一个专门计算 Token 的轻量级 API 调用
        # 即使下面的生成失败了，我们也能知道这里有多少 Token
        count_result = model.count_tokens(prompt)
        input_token_count = count_result.total_tokens
        print(f"本次请求预计消耗输入 Token: {input_token_count}")
    except Exception as e:
        print(f"警告: 预计算 Token 失败 ({e})，但不影响后续尝试生成。")

    # --- 步骤 2: 带重试机制的生成逻辑 ---
    max_retries = 3
    base_delay = 2  # 【重要修复】单位是秒！
    
    for attempt in range(max_retries):
        try:
            print(f"尝试第 {attempt + 1}/{max_retries} 次调用生成 API...")
            
            # 调用生成接口
            response = model.generate_content(prompt)
            
            # 如果成功，获取更准确的 Token 统计（包含输出 Token）
            output_tokens = "未知"
            if hasattr(response, 'usage_metadata'):
                # 覆盖之前的预估值，使用服务端返回的准确值
                input_token_count = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
            
            print(f"生成成功! 输入: {input_token_count}, 输出: {output_tokens}")
            
            report_content = response.text
            footer = f"\n\n---\n*API 统计: 输入 Token: {input_token_count} | 输出 Token: {output_tokens}*"
            return report_content + footer
            
        except Exception as e:
            error_str = str(e)
            print(f"尝试 {attempt + 1} 失败: {error_str}")
            
            # 遇到 429 (限流) 或 503 (服务繁忙) 时重试
            if "429" in error_str or "503" in error_str:
                if attempt < max_retries - 1:
                    # 指数退避: 2s, 4s, 8s
                    wait_time = base_delay * (2 ** attempt) 
                    print(f"触发流控，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
            
            # 如果是最后一次尝试，或者遇到不可重试的错误（如 400, 403）
            if attempt == max_retries - 1:
                # 【这里实现了你的需求】：在错误返回中包含 Token 数
                return (f"错误：API 调用失败 (重试 {max_retries} 次)。\n"
                        f"涉及 Token 数: {input_token_count}\n"
                        f"最后一次报错信息: {error_str}")

    return f"未知错误 (Token: {input_token_count})"

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


