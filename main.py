import asyncio
import csv
import time
import re
from playwright.async_api import async_playwright
from tqdm import tqdm
from utils import log_error
from page_handler import open_main_menu, init_browser_context
from category_parser import get_main_categories, get_second_level_categories, get_third_level_categories
from product_scraper import scrape_products_in_category


def sanitize_filename(name):
    """将名称转换为合法的文件名（替换特殊字符）"""
    return re.sub(r'[\\/*?:"<>|]', '_', name).strip()


async def main_scraper():
    config = {
        'main_category': 'Drinks',  # 主类别名称
        'second_category': 'Cold Coffee',  # 二级类别名称
        'third_category': None,
        'csv_filename': 'Cold Coffee'
    }

    # 生成合法的CSV文件名
    if config['csv_filename']:
        csv_filename = sanitize_filename(config['csv_filename']) + '.csv'
    else:
        csv_filename = f"starbucks_{sanitize_filename(config['second_category'])}.csv"

    # 初始化CSV和日志
    fieldnames = ['category', 'product_name', 'size', 'calories', 'price', 'url']
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    with open('scrape_error_log.txt', 'w', encoding='utf-8') as f:
        f.write("===== 爬取错误日志 =====\n")

    async with async_playwright() as p:
        # 初始化浏览器
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        await init_browser_context(context)
        page = await context.new_page()

        try:
            # 1. 打开主菜单
            if not await open_main_menu(page):
                print("无法进入主菜单，终止爬取")
                return

            # 2. 获取主类别
            main_categories = await get_main_categories(page)
            if not main_categories:
                print("未找到任何主类别")
                return

            # 3. 查找目标主类别
            target_main_category = next((c for c in main_categories if c['name'] == config['main_category']), None)
            if not target_main_category:
                print(f"未找到主类别: {config['main_category']}")
                print(f"可用主类别: {[c['name'] for c in main_categories]}")
                return
            print(f"找到目标主类别: {target_main_category['name']}")

            # 4. 获取二级类别并查找目标二级类别
            second_level_categories = await get_second_level_categories(page, target_main_category)
            target_second_category = next(
                (c for c in second_level_categories if c['name'] == config['second_category']), None)
            if not target_second_category:
                print(f"在{target_main_category['name']}下未找到二级类别: {config['second_category']}")
                print(f"可用的二级类别: {[c['name'] for c in second_level_categories]}")
                return
            print(f"找到目标二级类别: {target_second_category['name']}")

            # 5. 获取并筛选三级类别
            third_level_categories = await get_third_level_categories(page, target_second_category)
            if not third_level_categories:
                print(f"在{target_second_category['name']}下未找到三级类别")
                return

            # 如果指定了三级类别，则筛选
            if config['third_category']:
                target_third_categories = [c for c in third_level_categories if config['third_category'] in c['name']]
                if not target_third_categories:
                    print(f"在{target_second_category['name']}下未找到包含'{config['third_category']}'的三级类别")
                    print(f"可用的三级类别: {[c['name'] for c in third_level_categories]}")
                    return
            else:
                target_third_categories = third_level_categories

            # 计算总产品数
            total_products = sum(c['product_count'] for c in target_third_categories if c['product_count'] > 0)
            if total_products == 0:
                print("没有可爬取的产品")
                return

            print(f"\n总共需要爬取 {total_products} 个产品")
            print(f"数据将保存到: {csv_filename}")
            progress_bar = tqdm(total=total_products, desc="总体进度", position=0, leave=True)

            # 6. 创建目标三级类别ID列表
            target_category_ids = [c['id'] for c in target_third_categories]

            # 7. 循环爬取每个三级类别
            for category_id in target_category_ids:
                # 每次循环前回到初始菜单
                print(f"\n准备爬取类别ID: {category_id}")
                if not await open_main_menu(page):
                    log_error(f"无法返回主菜单，跳过类别 {category_id}")
                    continue

                # 重新获取主类别
                main_categories = await get_main_categories(page)
                if not main_categories:
                    log_error("重新获取主类别失败")
                    continue

                # 重新获取目标主类别
                target_main_category = next((c for c in main_categories if c['name'] == config['main_category']), None)
                if not target_main_category:
                    log_error(f"重新获取主类别失败: {config['main_category']}")
                    continue

                # 重新获取二级类别
                second_level_categories = await get_second_level_categories(page, target_main_category)
                if not second_level_categories:
                    log_error(f"重新获取二级类别失败")
                    continue

                # 重新获取目标二级类别
                target_second_category = next(
                    (c for c in second_level_categories if c['name'] == config['second_category']), None)
                if not target_second_category:
                    log_error(f"重新获取二级类别失败: {config['second_category']}")
                    continue

                # 重新获取三级类别
                third_level_categories = await get_third_level_categories(page, target_second_category)
                if not third_level_categories:
                    log_error(f"重新获取三级类别失败")
                    continue

                # 查找当前目标类别
                current_category = next((c for c in third_level_categories if c['id'] == category_id), None)
                if not current_category:
                    log_error(f"未找到三级类别: {category_id}")
                    continue

                # 爬取当前类别
                if current_category['product_count'] > 0:
                    await scrape_products_in_category(page, current_category, progress_bar, csv_filename)
                else:
                    print(f"类别 {current_category['name']} 无产品，跳过")

            progress_bar.close()
            print(f"\n{config['second_category']}大类爬取完成！数据已保存到{csv_filename}")

        except Exception as e:
            log_error(f"全局错误: {str(e)}")
            timestamp = int(time.time())
            await page.screenshot(path=f"global_error_{timestamp}.png", full_page=True)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main_scraper())