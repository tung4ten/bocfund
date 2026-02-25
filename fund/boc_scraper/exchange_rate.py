
import requests
from bs4 import BeautifulSoup
import re
import time

# Cache the rate to avoid frequent requests
_RATE_CACHE = {
    "USD": {"rate": None, "timestamp": 0},
    "CAD": {"rate": None, "timestamp": 0}
}
CACHE_DURATION = 3600 # 1 hour

def get_exchange_rates():
    global _RATE_CACHE
    now = time.time()
    
    # If both cached valid, return dict
    if _RATE_CACHE["USD"]["rate"] and (now - _RATE_CACHE["USD"]["timestamp"] < CACHE_DURATION) and \
       _RATE_CACHE["CAD"]["rate"] and (now - _RATE_CACHE["CAD"]["timestamp"] < CACHE_DURATION):
        return {
            "USD": _RATE_CACHE["USD"]["rate"],
            "CAD": _RATE_CACHE["CAD"]["rate"]
        }

    url = "https://www.boc.cn/sourcedb/whpj/"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=5)
        resp.encoding = 'utf-8'
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.find_all('tr')
        
        rates = {}
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 0:
                currency_name = cols[0].text.strip()
                target_code = None
                
                if "美元" in currency_name:
                    target_code = "USD"
                elif "加拿大元" in currency_name:
                    target_code = "CAD"
                
                if target_code:
                    # Use Middle Rate (Index 5) or Buying Rate (Index 1)
                    rate_str = cols[5].text.strip()
                    if not rate_str or not re.match(r'^\d+(\.\d+)?$', rate_str):
                        rate_str = cols[1].text.strip()
                    
                    if rate_str:
                        rate = float(rate_str) / 100.0
                        _RATE_CACHE[target_code]["rate"] = rate
                        _RATE_CACHE[target_code]["timestamp"] = now
                        rates[target_code] = rate
        
        return {
            "USD": _RATE_CACHE["USD"]["rate"] or 7.25,
            "CAD": _RATE_CACHE["CAD"]["rate"] or 5.10
        }
            
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
    
    return {
        "USD": _RATE_CACHE["USD"]["rate"] or 7.25,
        "CAD": _RATE_CACHE["CAD"]["rate"] or 5.10
    }
