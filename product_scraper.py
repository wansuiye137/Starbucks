import csv
import random
from playwright.async_api import Page, BrowserContext
from utils import log_error
from tqdm import tqdm
import time

async def clear_cart(page: Page):
    """清空购物车"""
    try:
        # 检查是否已空
        if await page.query_selector('div:text("Start your next order")'):
            return

        # 减少数量按钮
        decrease_btns = await page.query_selector_all('button[data-e2e="decreaseQuantityButton"]') or await page.query_selector_all('button[aria-label*="Decrease amount"]')
        for btn in decrease_btns:
            await btn.click()
            await page.wait_for_timeout(1000)
    except Exception as e:
        log_error(f"清理购物车出错: {str(e)}")
        timestamp = int(time.time())
        await page.screenshot(path=f"cart_error_{timestamp}.png", full_page=True)

async def get_sold_out_product_sizes(page: Page, product_name, product_url, category):
    """获取售罄产品的规格信息"""
    results = []
    try:
        # 获取规格选项
        size_options = []
        select_element = await page.query_selector('select[data-e2e="size-selector"]')
        if select_element:
            options = await select_element.query_selector_all('option:not([disabled]):not([value=""])')
            for option in options:
                size_options.append((await option.get_attribute('value'), await option.text_content() or ''))
        else:
            size_container = await page.query_selector('form[data-e2e="size-selector"]')
            if size_container:
                radio_labels = await size_container.query_selector_all('label')
                for label in radio_labels:
                    size_name = await label.get_attribute("data-e2e") or (await label.text_content() or '').split()[0]
                    size_options.append((size_name, ""))
            else:
                size_options = [("Standard", "")]

        # 处理每个规格
        for size_name, option_text in size_options:
            try:
                if select_element:
                    await select_element.select_option(value=size_name)
                else:
                    label = await page.query_selector(f'label[data-e2e="{size_name}"]') or await page.query_selector(f'label:has-text("{size_name}")')
                    if label:
                        await label.click()

                await page.wait_for_timeout(1000 + random.randint(500, 1500))
                # 获取卡路里
                calories_element = await page.query_selector('div[class*="auxiliaryProductInfoFont"] span[data-e2e="calories"]') or await page.query_selector('span[data-e2e="calories"]') or await page.query_selector('div:has-text("Calories") + div')
                calories = await calories_element.text_content() if calories_element else "N/A"

                results.append({
                    "category": category,
                    "product_name": product_name,
                    "size": size_name,
                    "calories": calories.strip() if calories else "N/A",
                    "price": "soldout",
                    "url": product_url
                })
            except Exception as e:
                print(f"规格{size_name}处理失败：{str(e)}（跳过）")
                continue
        return results
    except Exception as e:
        log_error(f"获取售罄产品信息失败: {str(e)}")
        return [{
            "category": category,
            "product_name": product_name,
            "size": "Standard",
            "calories": "N/A",
            "price": "soldout",
            "url": product_url
        }]

async def get_product_sizes(page: Page, product_name, product_url, category):
    """获取正常产品的规格信息"""
    results = []
    size_calories_map = {}
    try:
        # 获取规格选项
        size_options = []
        select_element = await page.query_selector('select[data-e2e="size-selector"]')
        if select_element:
            options = await select_element.query_selector_all('option:not([disabled]):not([value=""])')
            for option in options:
                size_options.append((await option.get_attribute('value'), await option.text_content() or ''))
        else:
            size_container = await page.query_selector('form[data-e2e="size-selector"]')
            if size_container:
                radio_labels = await size_container.query_selector_all('label')
                for label in radio_labels:
                    size_name = await label.get_attribute("data-e2e") or (await label.text_content() or '').split()[0]
                    size_options.append((size_name, ""))
            else:
                size_options = [("Standard", "")]

        # 处理规格并添加到购物车
        for size_name, option_text in size_options:
            try:
                if select_element:
                    await select_element.select_option(value=size_name)
                else:
                    label = await page.query_selector(f'label[data-e2e="{size_name}"]') or await page.query_selector(f'label:has-text("{size_name}")')
                    if label:
                        await label.click()

                await page.wait_for_timeout(2000 + random.randint(500, 1500))
                # 获取卡路里
                calories_element = await page.query_selector('div[class*="auxiliaryProductInfoFont"] span[data-e2e="calories"]') or await page.query_selector('span[data-e2e="calories"]') or await page.query_selector('div:has-text("Calories") + div')
                calories = await calories_element.text_content() if calories_element else "N/A"
                size_calories_map[size_name] = calories.strip() if calories else "N/A"

                # 添加到购物车
                add_btn = await page.query_selector('button[data-e2e="add-to-order-button"]') or await page.query_selector('button:has-text("Add to order")')
                if add_btn:
                    await add_btn.click()
                    await page.wait_for_timeout(2000)
                    # 关闭弹窗
                    close_btn = await page.query_selector('button[aria-label="Close"]')
                    if close_btn:
                        await close_btn.click()
                        await page.wait_for_timeout(1000)
                else:
                    print("未找到Add to order按钮，跳过当前规格")
                    continue
            except Exception as e:
                print(f"规格{size_name}处理失败：{str(e)}（跳过）")
                continue

        # 从购物车提取价格
        await page.goto("https://www.starbucks.com/menu/cart", timeout=60000, wait_until="domcontentloaded")
        for sel in ['h1:has-text("Your Order")', 'div[data-e2e="cart-container"]']:
            try:
                await page.wait_for_selector(sel, timeout=10000)
                break
            except:
                continue
        await page.wait_for_timeout(3000)

        # 提取价格
        cart_items = await page.query_selector_all('div[data-e2e="cart-item"]') or await page.query_selector_all('div[class*="cart-item"]')
        for item in cart_items:
            size_element = await item.query_selector('div[data-e2e="option-price-line"] p') or await item.query_selector('div[data-e2e="cart-item-size"]')
            size_text = await size_element.text_content() if size_element else "N/A"
            # 匹配规格名称
            size_name_matched = "Standard"
            for key in size_calories_map.keys():
                if key.lower() in size_text.lower():
                    size_name_matched = key
                    break
            # 获取价格
            price_element = None
            for sel in ['span[data-e2e="cart-item-price"]', 'div[class*="price"] span']:
                price_element = await item.query_selector(sel)
                if price_element:
                    break
            price = await price_element.text_content() if price_element else "N/A"

            results.append({
                "category": category,
                "product_name": product_name,
                "size": size_name_matched,
                "calories": size_calories_map.get(size_name_matched, "N/A"),
                "price": price.strip(),
                "url": product_url
            })
        return results
    except Exception as e:
        log_error(f"获取产品规格失败: {str(e)}")
        return []

async def scrape_products_in_category(page: Page, category, progress_bar: tqdm = None,
                                          csv_filename: str = 'starbucks_products.csv'):
    """从类别爬取单个产品"""
    try:
        category_name = category['full_category']
        print(f"\n===== 开始爬取类别: {category_name} =====")

        await category['element'].scroll_into_view_if_needed()
        await page.wait_for_timeout(1500)

        # 获取产品链接
        product_list = await category['element'].query_selector('ul.grid.grid--compactGutter')
        if not product_list:
            print(f"在{category_name}下未找到产品网格")
            return False

        product_links = []
        product_items = await product_list.query_selector_all('li.gridItem')
        for item in product_items:
            link = await item.query_selector('a.prodTile[href^="/menu/product/"]') or await item.query_selector('a.block.linkOverlay__primary[href^="/menu/product/"]')
            if link:
                href = await link.get_attribute('href')
                product_name = await link.get_attribute('data-e2e')
                if not product_name:
                    hidden_span = await link.query_selector('span.hiddenVisually')
                    product_name = await hidden_span.text_content() if hidden_span else href.split('/')[-2].replace('-', ' ').title()
                product_links.append({
                    'name': product_name.strip(),
                    'url': f"https://www.starbucks.com{href}",
                    'category': category_name
                })

        print(f"在{category_name}下找到{len(product_links)}个产品")

        # 爬取每个产品
        fieldnames = ['category', 'product_name', 'size', 'calories', 'price', 'url']
        for product in product_links:
            try:
                if progress_bar:
                    progress_bar.set_description(f"产品: {product['name'][:20]}...")
                    progress_bar.update(1)
                else:
                    print(f"爬取产品: {product['name']}")

                # 新标签页打开产品
                context = page.context
                new_page = await context.new_page()
                await new_page.goto(product['url'], timeout=60000, wait_until="domcontentloaded")
                await new_page.wait_for_selector('button[data-e2e="add-to-order-button"]', timeout=30000)

                # 检查售罄
                sold_out = await new_page.query_selector('text=/sold out/i')
                if sold_out:
                    results = await get_sold_out_product_sizes(new_page, product['name'], product['url'], product['category'])
                else:
                    results = await get_product_sizes(new_page, product['name'], product['url'], product['category'])
                    await clear_cart(new_page)  # 仅正常产品需要清理购物车

                # 写入CSV
                with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    for result in results:
                        writer.writerow(result)

                await new_page.close()
                await page.wait_for_timeout(1000)
            except Exception as e:
                log_error(f"产品{product['name']}爬取失败: {str(e)} | URL: {product['url']}")
                continue

        print(f"===== 类别 {category_name} 爬取完成 =====")
        return True
    except Exception as e:
        log_error(f"爬取类别 {category_name} 失败: {str(e)}")
        return False