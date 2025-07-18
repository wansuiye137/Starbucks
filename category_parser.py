from playwright.async_api import Page
from utils import log_error

async def get_main_categories(page: Page):
    """获取所有主类别（drinks, food, at-home-coffee）"""
    try:
        main_categories = []
        sections = await page.query_selector_all('section.pb4.lg-pb6')
        for section in sections:
            section_id = await section.get_attribute('id')
            if section_id in ['drinks', 'food', 'at-home-coffee']:
                heading = await section.query_selector('h2.heading2')
                category_name = await heading.text_content() if heading else section_id.replace('-', ' ').title()
                main_categories.append({
                    'id': section_id,
                    'name': category_name.strip()
                })
        print(f"找到{len(main_categories)}个主类别")
        return main_categories
    except Exception as e:
        error_msg = f"获取主类别失败: {str(e)}"
        print(error_msg)
        log_error(error_msg)
        return []

async def get_second_level_categories(page: Page, main_category):
    """获取二级类别（如Cold Coffee, Hot Tea等）"""
    try:
        print(f"\n开始处理主类别: {main_category['name']}")
        section = await page.query_selector(f'section#{main_category["id"]}')
        if not section:
            log_error(f"主类别{main_category['name']}：未找到入口元素")
            return []

        second_level_categories = []
        tiles = await section.query_selector_all('li[data-e2e="tile"]')
        if not tiles:
            log_error(f"主类别{main_category['name']}下未找到二级类别")
            return []

        for tile in tiles:
            category_div = await tile.query_selector('div[data-e2e]')
            if category_div:
                category_name = await category_div.get_attribute('data-e2e')
                second_level_categories.append({
                    'name': category_name,
                    'element': category_div
                })

        print(f"在{main_category['name']}下找到{len(second_level_categories)}个二级类别")
        return second_level_categories
    except Exception as e:
        error_msg = f"获取二级类别失败: {str(e)}"
        print(error_msg)
        log_error(error_msg)
        return []


async def get_third_level_categories(page: Page, second_level_category):
    """获取三级类别（如Cold Brew, Nitro Cold Brew等）"""
    try:
        print(f"已进入{second_level_category['name']}类别页面")

        # 1. 点击二级类别元素（确保元素可点击）
        await second_level_category['element'].click()

        # 2. 等待三级类别容器加载（超时 30 秒，可调整）
        await page.wait_for_selector('div.baseMenu___UpTAi', timeout=30000)

        # 3. 定位三级类别容器
        base_menu_div = await page.query_selector('div.baseMenu___UpTAi')
        if not base_menu_div:
            print("未找到三级类别容器 div.baseMenu___UpTAi")
            return []

        # 4. 在容器内查询三级类别 sections
        sections = await base_menu_div.query_selector_all('section.pb4.lg-pb6[id]')
        if not sections:
            print("容器内未找到三级类别 sections")
            return []

        # 5. 提取三级类别信息
        third_level_categories = []
        for section in sections:
            section_id = await section.get_attribute('id')
            if not section_id:
                continue

            # 提取类别名称（id 转标题，如 cold-brew → Cold Brew）
            category_name = section_id.replace('-', ' ').title()

            # 提取产品数量（ul 下的 li 数量）
            product_list = await section.query_selector('ul.grid.grid--compactGutter')
            product_count = len(await product_list.query_selector_all('li.gridItem')) if product_list else 0

            third_level_categories.append({
                'id': section_id,
                'name': category_name.strip(),
                'full_category': f"{second_level_category['name']}/{category_name.strip()}",
                'product_count': product_count,
                'element': section
            })

        print(f"在{second_level_category['name']}下找到{len(third_level_categories)}个三级类别")
        return third_level_categories

    except Exception as e:
        error_msg = f"获取三级类别失败: {str(e)}"
        print(error_msg)
        log_error(error_msg)
        return []