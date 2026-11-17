import sys, os, time
sys.path.insert(0, r"c:\Users\somul\OneDrive\Desktop\final year\jarvis")
from app.core.assistant import NivaAssistant

assistant = NivaAssistant(safe_mode=False)
spoken_messages = []
assistant.tts.speak = lambda txt: spoken_messages.append(txt)

print("Processing command: 'Notepad open chesi Hello Somu ani type chey'")
task = assistant.process_command("Notepad open chesi Hello Somu ani type chey")
print("Task status right after process_command:", task.status)
print("Task steps count:", len(task.steps))
for i, s in enumerate(task.steps):
    print(f"  Step {i+1}: {s.description} | tool: {s.tool_name} | params: {s.parameters}")

# Wait for task execution thread to finish
time.sleep(3.0)
print("Task status after 3 seconds:", task.status)
for i, s in enumerate(task.steps):
    print(f"  Step {i+1} status: {s.status} | result: {s.result} | error: {s.error}")

print("Spoken messages:", spoken_messages)
assistant.shutdown()
