import sys
import time
sys.path.insert(0, 'jarvis')

from app.core.assistant import NivaAssistant
from app.core.task_state import TaskStatus

a = NivaAssistant(safe_mode=False)

print("Starting Task 1: Open Calculator...")
t1 = a.process_command("Open Calculator")
a.wait_for_task(timeout=10)
print("Task 1:", t1.status, "Summary:", t1.result_summary)
print("Active app in context:", a.context.active_application)

time.sleep(1)

print("\nStarting Task 2: Add 2+2...")
t2 = a.process_command("Add 2+2")
finished = a.wait_for_task(timeout=25)
print("Finished within timeout:", finished)
print("Task 2 status:", t2.status)
print("Task 2 steps:")
for i, s in enumerate(t2.steps):
    print(f"  Step {i}: tool={s.tool_name}, status={s.status}, result={s.result}, error={s.error}")
print("Task 2 summary:", t2.result_summary)
