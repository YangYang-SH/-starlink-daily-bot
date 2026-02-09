# main.py

import os
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import markdown
import google.generativeai as genai
from duckduckgo_search import DDGS

# ================= 配置区域 =================

# Gemini API Key
API_KEY = os.getenv("GEMINI_API_KEY")

# 邮件配置
MAIL_HOST = "smtp.163.com"
MAIL_USER = "zhangjiang201612@163.com"
MAIL_PASS = os.getenv("MAIL_PASSWORD") # 163 授权码
RECEIVERS = ["pan.yangpan@huawei.com", "songjunlin@huawei.com"]

# 模型配置
MODEL_NAME = 'gemini-2.5-flash'

# ===========================================

def get_starlink_news():
    """搜索 Starlink 最新新闻"""
    print("正在搜索 Starlink 最新资讯...")
    results = []
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            with DDGS() as ddgs:
                keywords = "SpaceX Starlink news latest Direct to Cell"
                news_gen = ddgs.news(keywords, region="wt-wt", safesearch="off", timelimit="d", max_results=5)
                
                for r in news_gen:
                    title = r.get('title', 'No Title')
                    date = r.get('date', '')
                    body = r.get('body', r.get('snippet', ''))
                    link = r.get('url', r.get('link', ''))
                    
                    if len(body) > 150:
                        body = body[:150] + "..."
                    
                    clean_item = f"Date: {date}\nTitle: {title}\nLink: {link}\nSummary: {body}"
                    results.append(clean_item)

            if results:
                break
        except Exception as e:
            print(f"DuckDuckGo 搜索尝试 {attempt + 1}/{max_retries} 失败: {e}")
            time.sleep(2)

    if not results:
        return ""

    final_text = "\n---\n".join(results)
    if len(final_text) > 4000:
        final_text = final_text[:4000] + "\n...(内容已截断)"
    return final_text

def generate_report(news_text):
    """生成分析报告"""
    if not API_KEY:
        return "错误：未配置 API Key，无法生成报告。"

    print("正在准备调用 Gemini 进行分析...")
    
    if not news_text or len(news_text) < 10:
        return "未搜索到相关 Starlink 新闻。"

    # 提示词保持 Markdown 格式要求，因为 markdown 库处理这个最方便
    prompt = f"""
请扮演一位专业的科技新闻分析师。基于以下关于 Starlink (星链) 的最新新闻资讯，用中文写一份简短的日报。

要求：
1. 提炼 5 个最重要的核心动态。
2. 语气专业、简洁。
3. 使用 Markdown 格式（使用 **加粗** 重点，使用 - 列表）。
4. **必须在每条动态的结尾，附上对应的原始链接（格式为 Markdown：[点击查看原文](URL)）。**

--- 新闻内容 ---
{news_text}
"""

    try:
        genai.configure(api_key=API_KEY, transport='rest')
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        return f"配置 Gemini 失败: {e}"

    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"尝试第 {attempt + 1}/{max_retries} 次调用生成 API...")
            response = model.generate_content(prompt)
            
            # 获取 Token 统计
            input_tokens = "未知"
            output_tokens = "未知"
            if hasattr(response, 'usage_metadata'):
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
            
            report_content = response.text
            # 添加 Markdown 格式的页脚
            footer = f"\n\n---\n> *API 统计: 输入 Token: {input_tokens} | 输出 Token: {output_tokens}*"
            return report_content + footer
            
        except Exception as e:
            error_str = str(e)
            print(f"尝试 {attempt + 1} 失败: {error_str}")
            if "429" in error_str or "503" in error_str:
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
            if attempt == max_retries - 1:
                return f"错误：API 调用失败。\n最后报错: {error_str}"

    return "未知错误"

def save_report(content):
    if not content:
        return
    today = datetime.date.today().isoformat()
    os.makedirs("reports", exist_ok=True)
    filename = f"reports/Starlink_Report_{today}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"报告已保存至 {filename}")

def send_email(content):
    """发送邮件功能 (HTML 版)"""
    print("正在准备发送邮件...")
    
    if not content or "错误" in content[:20]:
        print("报告内容为空或包含错误，跳过发送。")
        return

    # 1. 将 Markdown 转换为 HTML
    try:
        html_body = markdown.markdown(content, extensions=['tables', 'fenced_code'])
    except Exception as e:
        print(f"Markdown 转换失败，降级发送纯文本: {e}")
        html_body = f"<pre>{content}</pre>"

    # 2. 构建美化的 HTML 模板 (修改了 font-family)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                /* 关键修改：将微软雅黑放在第一位，并提供通用备选字体 */
                font-family: "Microsoft YaHei", "微软雅黑", STHeiti, MingLiu, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1, h2, h3 {{ 
                font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
                color: #2c3e50; 
                border-bottom: 2px solid #eaeaea; 
                padding-bottom: 10px; 
            }}
            a {{ color: #0066cc; text-decoration: none; font-weight: bold; }}
            a:hover {{ text-decoration: underline; }}
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 10px; }}
            strong {{ color: #d35400; }}
            blockquote {{
                background: #f9f9f9;
                border-left: 5px solid #ccc;
                margin: 1.5em 10px;
                padding: 0.5em 10px;
                color: #555;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 10px;
                border-top: 1px solid #eee;
                font-size: 12px;
                color: #999;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="content">
            {html_body}
        </div>
        <div class="footer">
            Generated by Gemini 2.5 Flash | 自动发送邮件系统
        </div>
    </body>
    </html>
    """
    
    today = datetime.date.today().isoformat()
    subject = f"Starlink 每日简报 - {today}"
    
    # 3. 构造 MIMEText 对象，注意第二个参数改为 'html'
    message = MIMEText(html_content, 'html', 'utf-8')
    # message['From'] = Header(MAIL_USER, 'utf-8')
    # message['To'] = Header(",".join(RECEIVERS), 'utf-8')
    message['From'] = MAIL_USER
    message['To'] = ", ".join(RECEIVERS)
    message['Subject'] = Header(subject, 'utf-8')

    try:
        smtp_obj = smtplib.SMTP_SSL(MAIL_HOST, 465) 
        smtp_obj.login(MAIL_USER, MAIL_PASS)
        smtp_obj.sendmail(MAIL_USER, RECEIVERS, message.as_string())
        print(f"HTML 邮件已成功发送至: {RECEIVERS}")
        smtp_obj.quit()
        
    except smtplib.SMTPException as e:
        print(f"邮件发送失败 (SMTP错误): {e}")
    except Exception as e:
        print(f"邮件发送发生未知错误: {e}")

def main():
    # 1. 获取新闻
    news = get_starlink_news()
    
    # 2. 生成报告
    report = generate_report(news)
    
    if report:
        # 3. 本地保存 (依然保存 Markdown 源码，方便存档)
        save_report(report)
        
        # 4. 发送邮件 (发送渲染后的 HTML)
        send_email(report)
        
        print("流程结束。")
    else:
        print("生成失败，未保存也未发送。")

if __name__ == "__main__":
    main()




