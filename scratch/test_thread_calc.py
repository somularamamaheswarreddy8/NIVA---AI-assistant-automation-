import sys
import threading
import time
sys.path.insert(0, 'jarvis')
from app.automation.calculator_automation import CalculatorAutomation

def run():
    print("Thread started, calling CalculatorAutomation.calculate...")
    t0 = time.time()
    res = CalculatorAutomation.calculate("2+2", ensure_open=True)
    t1 = time.time()
    print(f"Thread finished in {t1-t0:.2f}s, result: {res}")

t = threading.Thread(target=run)
t.start()
t.join(timeout=15)
if t.is_alive():
    print("THREAD TIMED OUT!")
else:
    print("Thread completed successfully.")
