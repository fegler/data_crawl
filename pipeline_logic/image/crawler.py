# saramin_click_detail_playwright.py

import asyncio
from playwright.async_api import async_playwright
import os

def clean_filename(title):
    title = title.replace(" ", "_").replace("/", "_")
    return "".join(c for c in title if c.isalnum() or c in "_-")

async def crawl_saramin(keyword, data_dir):
    async with async_playwright() as p:
        ## 사람인 페이지 load
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        page = await browser.new_page() 

        search_url = f"https://www.saramin.co.kr/zf_user/search?searchword={keyword}"
        await page.goto(search_url) ## keyword 검색 
        await page.wait_for_selector("div#recruit_info_list")

        ## JD list 
        jd_items = await page.query_selector_all("div#recruit_info_list div.item_recruit")
        print(f"🔍 Found {len(jd_items)} job items")

        for i, item in enumerate(jd_items[:5]):
            try: 
                title_el = await item.query_selector("h2.job_tit > a")
                title = await title_el.inner_text() if title_el else "N/A"
                
                company_el = await item.query_selector("div.area_corp strong.corp_name > a")
                company = await company_el.inner_text() if company_el else "N/A"
                
                link = await title_el.get_attribute("href")
                full_url = f"https://www.saramin.co.kr{link}"

                print(f"[{i+1}] {company} - {title}")
                print(f"URL: {full_url}")

                jd_page = await browser.new_page()
                await jd_page.goto(full_url)
                # await jd_page.wait_for_selector(".wrap_jv_cont", timeout=10000)

                wrap_jview = await jd_page.query_selector("div.wrap_jview")
                first_section = await wrap_jview.query_selector("section.jview")
                jd_cont = await first_section.query_selector("div.wrap_jv_cont")
                jd_target_contents = await jd_cont.query_selector("div.jv_cont.jv_detail")


                filename = f"{i+1}_{company}_{title}"
                output_dir = os.path.join(data_dir, filename)
                os.makedirs(output_dir, exist_ok=True)

                ## screenshot
                screenshot_path = os.path.join(output_dir, 'screenshot.png')
                await jd_target_contents.screenshot(path=screenshot_path)
            
            except Exception as e:
                print(f"❌ Error while handling item {i+1}: {e}")
                continue

    await browser.close()

if __name__ == "__main__":
    asyncio.run(crawl_saramin(keyword="ML 엔지니어", data_dir='/Users/djyun/project/data_crawl/data/image'))