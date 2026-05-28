import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from datetime import datetime

def find_chrome_binary():
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Google\Chrome\Application\chrome.exe")
    ]
    for path in paths:
        if os.path.exists(path): return path
    return None

def get_chrome_major_version(chrome_path):
    # Try using win32api
    try:
        import win32api
        info = win32api.GetFileVersionInfo(chrome_path, '\\')
        ms = info['FileVersionMS']
        major = win32api.HIWORD(ms)
        return major
    except Exception as e:
        print(f"[Scraper Warning] win32api version check failed: {e}")

    # Fallback 1: Registry check
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        return int(version.split('.')[0])
    except Exception as e:
        print(f"[Scraper Warning] Registry version check failed: {e}")

    # Fallback 2: Check standard directory structure (folder names containing numbers)
    try:
        chrome_dir = os.path.dirname(chrome_path)
        for name in os.listdir(chrome_dir):
            if os.path.isdir(os.path.join(chrome_dir, name)):
                parts = name.split('.')
                if len(parts) >= 2 and all(p.isdigit() for p in parts):
                    return int(parts[0])
    except Exception as e:
        print(f"[Scraper Warning] Directory search version check failed: {e}")

    # Fallback 3: subprocess call to chrome.exe --version
    try:
        import subprocess
        import re
        output = subprocess.check_output([chrome_path, "--version"], stderr=subprocess.STDOUT, text=True)
        match = re.search(r"Google Chrome (\d+)", output)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"[Scraper Warning] Subprocess version check failed: {e}")

    return 148  # Default fallback if all else fails

def scrape_redbus(source, dest, date):
    print(f"[Scraper] Extracting LIVE prices: {source} to {dest}...")
    chrome_path = find_chrome_binary()
    if not chrome_path: return []

    major_version = get_chrome_major_version(chrome_path)
    print(f"[Scraper] Dynamically resolved Chrome major version: {major_version}")

    options = uc.ChromeOptions()
    options.binary_location = chrome_path
    options.add_argument('--headless')
    
    driver = None
    scraped_data = []
    
    try:
        driver = uc.Chrome(options=options, version_main=major_version) 
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d-%b-%Y')
        except:
            formatted_date = date

        url = f"https://www.redbus.in/bus-tickets/{source.lower()}-to-{dest.lower()}?date={formatted_date}"
        driver.get(url)
        
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".fare, .seat-fare")))
        except: pass

        bus_items = driver.find_elements(By.CSS_SELECTOR, ".bus-item, .clearfix.row-one")
        
        for bus in bus_items[:5]: 
            try:
                operator = bus.find_element(By.CSS_SELECTOR, ".travels, .makeFlex hspan").text
                bus_type = bus.find_element(By.CSS_SELECTOR, ".bus-type").text
                depart = bus.find_element(By.CSS_SELECTOR, ".dp-time").text
                price_text = bus.find_element(By.CSS_SELECTOR, ".fare span, .seat-fare").text
                price = price_text.replace('INR', '').replace('₹', '').replace(',', '').strip()
                
                scraped_data.append({
                    "operator": operator + " (LIVE)", "bus_type": bus_type,
                    "depart": depart, "duration": "N/A", "price": price,
                    "rating": "4.2", "punctuality": 80
                })
            except: continue
                
        print(f"[Scraper] Extracted {len(scraped_data)} LIVE bus prices.")
    except Exception as e:
        print(f"[Scraper] Live extraction failed: {e}")
    finally:
        if driver:
            try: driver.quit()
            except: pass
                
    return scraped_data