import os
import json
import time
from playwright.sync_api import sync_playwright

# Path to the generated articles
ARTICLES_PATH = "data/evaluation/articles_to_post.json"

def run_auto_post():
    if not os.path.exists(ARTICLES_PATH):
        print(f"❌ 找不到文章檔案: {ARTICLES_PATH}")
        return

    with open(ARTICLES_PATH, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    if not articles:
        print("✅ 沒有待處理的文章。")
        return

    # Use a persistent user data directory to save login sessions
    user_data_dir = os.path.join(os.getcwd(), "data/automation_profile")
    os.makedirs(user_data_dir, exist_ok=True)

    print(f"🚀 準備自動上傳 {len(articles)} 篇文章...")
    print(f"📁 瀏覽器設定檔存放於: {user_data_dir}")

    with sync_playwright() as p:
        # Use a persistent context with a real browser channel
        # This helps bypass 'browser not secure' blocks
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            channel="chrome", # Try to use system installed Google Chrome
            args=["--disable-blink-features=AutomationControlled"] # Hide automation flags
        )
        
        page = context.pages[0] if context.pages else context.new_page()

        print("\n🌐 正在開啟 Doctor Toolbox...")
        page.goto('https://doctor-toolbox.com/clinicBot')

        print("\n🔐 [重要] 1. 請在瀏覽器視窗中完成登入。")
        print("        2. 請點擊進入『診所知識文章』分頁。")
        print("        3. 準備就緒後，請回到終端機按 Enter...")
        input(">>> 就緒後請按 Enter >>>")

        for i, art in enumerate(articles):
            title = art.get('title')
            category = art.get('category', '術後照顧')
            content = art.get('content')

            print(f"\n📝 [{i+1}/{len(articles)}] 正在處理: {title}")

            try:
                # 1. Click "+ 新增文章"
                # Using a very persistent click strategy
                add_btn = page.get_by_text("新增文章").first
                add_btn.click(timeout=5000)
                time.sleep(2)

                # 2. Fill Title - Use keyboard focus and typing if locator fails
                page.keyboard.press("Tab") # Sometimes help focus first element
                title_field = page.locator('input:visible').first
                title_field.click()
                title_field.fill(title)
                print(f"   ✍️ 已填入標題")

                # 3. Handle Category
                try:
                    page.locator('select:visible').select_option(label=category)
                except: pass

                # 4. Fill Content
                # Use tab sequence if needed, but try textarea first
                content_field = page.locator('textarea:visible').first
                content_field.click()
                content_field.fill(content)
                print(f"   ✍️ 已填入內容")

                # 5. Click Save
                save_btn = page.locator('button:has-text("儲存"), button:has-text("確認"), .btn-primary').filter(visible=True).first
                save_btn.click(timeout=5000)
                print("   ✅ 已點擊儲存")

                time.sleep(2)

            except Exception as e:
                print(f"   ❌ 處理失敗: {e}")
                print("   💡 請手動完成這篇上傳，或手動點開『新增文章』彈窗後按 y 繼續下一篇。")
                if input(">>> 要跳過此篇繼續嗎？(y/n): ") != 'y':
                    break

        print("\n🎉 所有文章上傳程序結束！")
        context.close()

if __name__ == "__main__":
    run_auto_post()
