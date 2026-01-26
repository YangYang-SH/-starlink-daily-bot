# main.py
import os
import google.generativeai as genai
from datetime import datetime

# 配置 API Key (将从 GitHub Secrets 读取)
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("未找到 GOOGLE_API_KEY，请检查 Secrets 设置")

genai.configure(api_key=api_key)

def fetch_and_generate_report():
    print("正在调用 Gemini API...")
    
    # 使用 Flash 模型，速度快且省钱
    model = genai.GenerativeModel('models/gemini-1.5-flash') 
    
    prompt = f"""
    今天是 {datetime.now().strftime('%Y-%m-%d')}。
    请使用 Google Search 查找关于 'SpaceX Starlink' 的最新新闻。
    时间范围：过去 24 小时内。
    
    请生成一份 Markdown 格式的简报：
    1. 使用一级标题写 "Starlink 日报 - {datetime.now().strftime('%Y-%m-%d')}"。
    2. 列出 3-5 条最重要的动态。
    3. 每条动态包含：标题、简短摘要、来源链接。
    4. 如果没有重大新闻，请简短说明。
    """

    try:
        response = model.generate_content(
            prompt,
            tools='google_search_retrieval' # 启用搜索工具
        )
        
        content = response.text
        
        # 将结果保存到文件，供 GitHub Actions 后续步骤使用
        with open("daily_report.md", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("报告生成成功，已保存至 daily_report.md")

    except Exception as e:
        print(f"发生错误: {e}")
        # 如果出错，也写一个文件，以免报错导致 Action 彻底中断什么都看不到
        with open("daily_report.md", "w", encoding="utf-8") as f:
            f.write(f"任务执行出错: {e}")

if __name__ == "__main__":
    fetch_and_generate_report()