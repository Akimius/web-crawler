import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def get_chrome_driver(headless: bool = True):
    """Create an undetected Chrome driver to bypass Cloudflare.

    Args:
        headless: Run in headless mode (default True). Set False for debugging.
    """
    options = uc.ChromeOptions()

    if headless:
        options.add_argument("--headless=new")

    # Required flags for Docker
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Additional flags
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--lang=en-US,en")

    # Use system chromium
    options.binary_location = "/usr/bin/chromium"

    driver = uc.Chrome(
        options=options,
        driver_executable_path="/usr/bin/chromedriver",
        version_main=143  # Match your chromium version
    )
    driver.set_page_load_timeout(30)

    return driver


def get_standard_chrome_driver(headless: bool = True):
    """Fallback standard Chrome driver if undetected-chromedriver fails."""
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    options.binary_location = "/usr/bin/chromium"

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)

    return driver