import os, time, requests, re
from decimal import Decimal

class PolyBot:
    def __init__(self):
        self.api_url = "https://clob.polymarket.com"
        self.gamma_url = "https://gamma-api.polymarket.com/markets"
        
        # Данные берутся из секретов GitHub автоматически
        self.tg_token = os.getenv("TELEGRAM_TOKEN")
        self.tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        self.max_p = Decimal("0.96")
        self.min_diff = Decimal("0.01")

    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def send_tg(self, text):
        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.tg_chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
        except: pass

    def get_p(self, tid):
        try:
            r = requests.get(f"{self.api_url}/price?token_id={tid}&side=buy", timeout=5).json()
            if 'price' in r: return Decimal(str(r['price']))
        except: pass
        return None

    def run(self):
        self.log("🚀 Мониторинг запущен в облаке GitHub...")
        start_time = time.time()
        
        # Бот будет работать внутри этого цикла
        while time.time() - start_time < 2700: # Работает 45 минут
            try:
                params = {"active": "true", "closed": "false", "limit": 100, "order": "volume24hr"}
                r = requests.get(self.gamma_url, params=params, timeout=15)
                ms = r.json() if r.status_code == 200 else []
                
                groups = {}
                for m in ms:
                    g_id = m.get('groupItemTitle') or m.get('title')
                    ids = m.get('clobTokenIds')
                    if not ids or not g_id: continue
                    
                    try:
                        tids = eval(ids) if isinstance(ids, str) else ids
                        p = self.get_p(tids[0])
                        if p and p > 0:
                            nums = re.findall(r'(\d+(?:\.\d+)?)', m.get('question',''))
                            val = float(nums[-1]) if nums else 0.0
                            if g_id not in groups: groups[g_id] = []
                            groups[g_id].append({'t': m['question'], 'v': val, 'p': p, 's': m['slug']})
                    except: continue

                for g_name, items in groups.items():
                    if len(items) < 2: continue
                    items.sort(key=lambda x: x['v'])
                    for i in range(len(items)):
                        for j in range(i+1, len(items)):
                            low, high = items[i], items[j]
                            if high['v'] > low['v'] and high['p'] > low['p']:
                                diff = high['p'] - low['p']
                                if diff < self.min_diff: continue
                                
                                msg = (f"⚖️ *АРБИТРАЖ (Облако)*\n\n📂 *Тема:* {g_name}\n"
                                       f"🟢 *Выгоднее:* {low['t']} (Цена: {low['p']})\n"
                                       f"🔴 *Дороже:* {high['t']} (Цена: {high['p']})\n"
                                       f"💡 Вариант Б сложнее, но стоит дороже А.\n"
                                       f"🔗 [ОТКРЫТЬ](https://polymarket.com/market/{low['slug']})")
                                self.send_tg(msg)
                time.sleep(35)
            except:
                time.sleep(20)

if __name__ == "__main__":
    PolyBot().run()
