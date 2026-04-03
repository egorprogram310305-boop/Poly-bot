import os, time, requests, re
from decimal import Decimal

class PolyProTrader:
    def __init__(self):
        # Ключи для Телеграм
        self.tg_token = os.getenv("TELEGRAM_TOKEN")
        self.tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        # Настройки торговли
        self.min_anomaly = Decimal("0.001")
  # Ищем разницу от 100% (5 центов)
        self.bet_amount = 1.0              # Сумма входа (минималка 1$)
        
        # API Polymarket
        self.api_url = "https://clob.polymarket.com"
        self.gamma_url = "https://gamma-api.polymarket.com/markets"

    def send_tg(self, text):
        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": self.tg_chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
        except: pass

    def calc_levels(self, price):
        """Рассчитывает Stop-Loss и Take-Profit"""
        p = Decimal(str(price))
        sl = p - Decimal("0.04") # Защита: если упало на 4 цента - выходим
        tp = p + Decimal("0.08") # Цель: если выросло на 8 центов - забираем
        
        if sl < Decimal("0.01"): sl = Decimal("0.01")
        if tp > Decimal("0.98"): tp = Decimal("0.98")
        return round(sl, 3), round(tp, 3)

    def get_p(self, tid):
        try:
            r = requests.get(f"{self.api_url}/price?token_id={tid}&side=buy", timeout=5).json()
            if 'price' in r: return Decimal(str(r['price']))
        except: pass
        return None

    def run(self):
        print("🚀 Режим разведки и расчета сделок активен...")
        # Сообщим в ТГ о запуске новой системы
        self.send_tg("🤖 *Система управления сделками запущена!*\n\nБот ищет аномалии > 5%, рассчитывает SL/TP и имитирует вход на 1$.")
        
        start_t = time.time()
        while time.time() - start_t < 2700:
            try:
                r = requests.get(self.gamma_url, params={"active": "true", "limit": 100}, timeout=15)
                ms = r.json() if r.status_code == 200 else []
                
                groups = {}
                for m in ms:
                    g_id = m.get('groupItemTitle') or m.get('title')
                    ids = m.get('clobTokenIds')
                    if not ids or not g_id: continue
                    
                    tids = eval(ids) if isinstance(ids, str) else ids
                    p = self.get_p(tids[0])
                    if p:
                        nums = re.findall(r'(\d+(?:\.\d+)?)', m.get('question',''))
                        val = float(nums[-1]) if nums else 0.0
                        if g_id not in groups: groups[g_id] = []
                        groups[g_id].append({'t': m['question'], 'v': val, 'p': p, 'slug': m['slug']})

                for name, items in groups.items():
                    if len(items) < 2: continue
                    items.sort(key=lambda x: x['v'])
                    
                    for i in range(len(items)):
                        for j in range(i+1, len(items)):
                            A, B = items[i], items[j]
                            if B['v'] > A['v'] and B['p'] > A['p']:
                                diff = B['p'] - A['p']
                                if diff >= self.min_anomaly:
                                    sl, tp = self.calc_levels(A['p'])
                                    
                                    # Подробный отчет
                                    msg = (
                                        f"📈 *АНАЛИЗ СДЕЛКИ: ОБНАРУЖЕН ВХОД*\n"
                                        f"━━━━━━━━━━━━━━\n"
                                        f"📁 *Тема:* {name}\n"
                                        f"🎯 *Инструмент:* {A['t']}\n"
                                        f"💰 *Цена входа:* `{A['p']}`\n"
                                        f"💵 *Сумма сделки:* `${self.bet_amount}`\n"
                                        f"━━━━━━━━━━━━━━\n"
                                        f"🛡 *Stop-Loss (Риск):* `{sl}`\n"
                                        f"🚀 *Take-Profit (Цель):* `{tp}`\n"
                                        f"⚖️ *Аномалия:* `{diff}`\n"
                                        f"━━━━━━━━━━━━━━\n"
                                        f"📝 *Логика:* Рынок '{B['t']}' стоит `{B['p']}`. Это математическая ошибка. "
                                        f"Входим в более дешевый вариант А в ожидании роста к `{tp}`.\n\n"
                                        f"🔗 [ОТСЛЕДИТЬ СДЕЛКУ](https://polymarket.com/market/{A['slug']})"
                                    )
                                    self.send_tg(msg)
                                    time.sleep(15) 
                time.sleep(40)
            except: time.sleep(20)

if __name__ == "__main__":
    PolyProTrader().run()
