# app/main.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from browser import get_chrome_driver


def scrape_gold_news():
    driver = get_chrome_driver()

    try:
        driver.get("https://www.investing.com/commodities/gold-news/12")

        wait = WebDriverWait(driver, 2)
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[data-test="news-list"]'))
        )

        # Get all article title links
        links = driver.find_elements(By.CSS_SELECTOR, 'a[data-test="article-title-link"]')

        for link in links:
            title = link.text
            url = link.get_attribute("href")
            print(f"{title}")
            # print(f"  {url}")
            print()

    finally:
        driver.quit()


if __name__ == "__main__":
    scrape_gold_news()