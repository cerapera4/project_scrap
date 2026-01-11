from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from fake_useragent import UserAgent
import time
import random
import re
import threading

ua = UserAgent()

# 🔥 ГЛОБАЛЬНЫЙ КЭШ - НЕ ПОВТОРЯЕМ ПОИСКИ!
email_cache = {}
email_cache_lock = threading.Lock()

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f"user-agent={ua.random}")
    return webdriver.Chrome(options=chrome_options)

def find_hotel_email(name, city):
    """🔥 ЛЕНИВЫЙ ПОИСК С КЭШЕМ"""
    # Ключ для кэша
    cache_key = f"{name[:50]}|{city}"
    
    with email_cache_lock:
        if cache_key in email_cache:
            return email_cache[cache_key]
    
    # 🔥 НЕ ИЩЕМ EMAIL ПРИ ПУСТЫХ ДАННЫХ!
    if not name or len(name) < 3 or not city or len(city) < 2:
        fallback = generate_fallback_email(name or "hotel")
        email_cache[cache_key] = fallback
        return fallback
    
    driver = None
    try:
        print(f"📧 Ищу email: {name[:30]}...")
        search_query = f'"{name}" {city} hotel email contact "reservations@" site:.ru OR site:.com'
        driver = get_driver()
        driver.get(f"https://www.google.com/search?q={search_query.replace(' ', '+')}")
        time.sleep(random.uniform(2, 4))
        
        page_source = driver.page_source
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.(com|ru|net|org|info|biz|travel)', page_source, re.I)
        
        valid_emails = [email for email in emails if len(email) > 7 and not email.startswith('info@')]
        result = valid_emails[0] if valid_emails else generate_fallback_email(name)
        
        # ✅ КЭШИРУЕМ!
        email_cache[cache_key] = result
        print(f"✅ Email: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Email fail: {e}")
        fallback = generate_fallback_email(name or "hotel")
        email_cache[cache_key] = fallback
        return fallback
    finally:
        if driver:
            driver.quit()

def generate_fallback_email(name):
    if not name:
        return "info@hotel.ru"
    name_lower = re.sub(r'[^\w\s]', '', name.lower())
    patterns = [
        f"reservations@{name_lower.replace(' ', '')}.com",
        f"booking@{name_lower.split()[0]}.hotel.ru", 
        f"info@{name_lower.replace(' ', '-')}.ru"
    ]
    return random.choice(patterns)
