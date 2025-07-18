from playwright.async_api import Page
from utils import log_error

async def init_browser_context(context):
    """初始化浏览器上下文（规避反爬）"""
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
    """)

async def open_main_menu(page: Page) -> bool:
    """打开主菜单页面并验证"""
    try:
        MENU_URL = "https://www.starbucks.com/menu?storeNumber=56450-290146&distance=0.2118&confirmedOrderingUnavailable=56450-290146"
        await page.goto(MENU_URL, timeout=60000, wait_until="domcontentloaded")
        print("已进入初始菜单页面")
        await page.wait_for_selector('section#drinks', timeout=30000)
        await page.wait_for_timeout(2000)
        return True
    except Exception as e:
        error_msg = f"进入主菜单失败: {str(e)}"
        print(error_msg)
        log_error(error_msg)
        return False