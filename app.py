from flask import Flask, render_template, request, send_file, flash
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import io
import time
import random
import os
import sys
from utils import find_hotel_email
import logging

# 🔥 ФИКС UNICODE ОШИБКИ ДЛЯ WINDOWS
if os.name == 'nt':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    os.system('chcp 65001 > nul')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'triplesix_ultra_secret_key')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# Логи
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_driver():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--headless')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # 🔥 Render.com Chrome!
    options.binary_location = '/usr/bin/google-chrome'
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    city = ""
    
    if request.method == 'POST':
        city = request.form['city'].strip()
        if city:
            print(f"🕷️  Сканирую отели в {city}...")
            results = scrape_all_hotels(city)
            print(f"🏆 НАЙДЕНО: {len(results)} отелей!")
            flash(f'Найдено {len(results)} отелей для {city}!')
    
    return render_template('index.html', results=results, city=city)

def clean_hotel_name(name):
    """🧹 Чистит названия от Booking/TripAdvisor мусора"""
    trash_phrases = [
        "Откроется в новом окне",
        "Opens in new window",
        "Opens new window", 
        "New window",
        "Read more",
        "Подробнее",
        "Details"
    ]
    
    for phrase in trash_phrases:
        name = name.replace(phrase, "").strip()
    
    # Финальная очистка
    name = ' '.join(name.split())
    return name[:120] if name else "Неизвестный отель"


def scrape_all_hotels(city):
    all_hotels = []
    driver = None
    
    try:
        driver = get_driver()
        driver.maximize_window()
        
        # BOOKING - основной источник
        booking_hotels = scrape_booking(driver, city)
        all_hotels.extend(booking_hotels)
        
        print(f"📈 Booking: {len(booking_hotels)} отелей")
        
        # TripAdvisor как бонус
        time.sleep(2)
        trip_hotels = scrape_tripadvisor(driver, city)
        all_hotels.extend(trip_hotels)
        print("📧 Парсинг email для всех отелей...")
        for i, hotel in enumerate(all_hotels):
            city_h, name_h, _ = hotel
            all_hotels[i][2] = find_hotel_email(name_h, city_h)
            time.sleep(0.5)  # Антибан
    
        return all_hotels
    except Exception as e:
        print(f"💥 КРИТИЧНО: {e}")
    finally:
        if driver:
            driver.quit()
    
    # ✅ ПРАВИЛЬНЫЙ УНИКАЛЬНЫЙ КОД
    unique = {}
    for hotel_data in all_hotels:
        hotel_name = str(hotel_data[1])[:50]  # str() для безопасности
        if hotel_name not in unique:
            unique[hotel_name] = hotel_data
    
    print(f"🎯 УНИКАЛЬНЫХ ОТЕЛЕЙ: {len(unique)}")
    return list(unique.values())

def scrape_booking(driver, city):
    hotels = []
    try:
        url = f"https://www.booking.com/searchresults.html?ss={city.replace(' ', '+')}&lang=ru"
        driver.get(url)
        time.sleep(8)
        driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(3)
        
        cards = driver.find_elements(By.CSS_SELECTOR, '[data-testid="property-card"]')
        print(f"🏨 НАЙДЕНО КАРТОЧЕК: {len(cards)}")
        
        for i, card in enumerate(cards[:15]):
            try:
                # 🎯 Название БЕЗ мусора
                name_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="title-link"]')
                raw_name = name_elem.text.strip()
                
                # 🧹 ОЧИСТКА
                name = clean_hotel_name(raw_name)
                
                if len(name) > 5:
                    print(f"✅ #{i+1} {name}")
                    email = find_hotel_email(name, city) or "нет"
                    hotels.append([city, name, email])
                
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"❌ Booking: {e}")
    
    return hotels


def scrape_tripadvisor(driver, city):
    """Упрощенный TripAdvisor - работает стабильно"""
    hotels = []
    try:
        # Лучший URL для поиска
        url = f"https://www.tripadvisor.ru/Hotels-g298484-{city.replace(' ', '_')}-Hotels.html"
        print(f"🔍 TripAdvisor: {city}")
        driver.get(url)
        time.sleep(7)
        
        # Множество селекторов
        trip_selectors = [
            'a[data-test-target="hotels-list-title-link"]',
            '.WAllg a',
            '.UIEzd',
            '[data-automation-id="hotel-title"] a',
            '.result-title a'
        ]
        
        for selector in trip_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✅ TripAdvisor ({selector}): {len(elements)}")
                    
                    for i, elem in enumerate(elements[:8]):
                        name = elem.text.strip()
                        if len(name) > 8:
                            print(f"✅ Trip #{i+1}: {name[:40]}")
                            email = "🔍 Поиск..."  # Плейсхолдер
                            hotels.append([city, name, email])
                    break
            except:
                continue
                
    except Exception as e:
        print(f"⚠️  TripAdvisor пропуск: {e}")
    
    return hotels


if __name__ == '__main__':
    app.run(debug=True, port=5000)
