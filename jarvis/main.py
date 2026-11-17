"""
NIVA — Universal AI-Powered Autonomous Computer Control System.
Main Application Entry Point.
"""

import argparse
import logging
import os
import sys

# Ensure local app package can be resolved
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.config import ASSISTANT_NAME

# Configure Logging
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level_str, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(f"{ASSISTANT_NAME}.Main")


def run_cli_mode(assistant, enable_voice: bool = True):
    """Interactive command-line execution mode."""
    print("=" * 65)
    print(f"  {ASSISTANT_NAME} — Universal Autonomous Computer Control Agent (CLI Mode)")
    print("  Type any command, or type 'stop', 'pause', 'resume', 'exit'.")
    print("=" * 65)

    def on_logged(role: str, text: str):
        if role == "assistant":
            print(f"[{ASSISTANT_NAME}]> {text}")
        elif role == "system":
            print(f" [SYSTEM]> {text}")
        elif role == "error":
            print(f"  [ERROR]> {text}")

    assistant.on_message_logged = on_logged
    assistant.tts.on_speaking_started = lambda text: print(f" [SPEAKING] \"{text}\"")
    assistant.tts.on_error = lambda err: print(f" [AUDIO ERROR] {err}")
    assistant.voice_listener.on_transcript_preview = lambda txt: print(f" [HEARD]> {txt}")
    assistant.voice_listener.on_status_change = lambda s: print(f" [MIC STATUS]> {s}")
    assistant.voice_listener.on_error = lambda err: print(f" [MIC ERROR]> {err}")

    if enable_voice:
        def cli_prompt() -> bool:
            try:
                ans = input("\n[NIVA] Microphone access required for hands-free voice control. Grant permission? (Y/n): ").strip().lower()
                return ans != "n"
            except Exception:
                return True
        assistant.startup_lifecycle(on_permission_needed=cli_prompt)

    try:
        while True:
            cmd = input("\n[USER]> ").strip()
            if not cmd:
                continue
            if cmd.lower() in ["exit", "quit", "q"]:
                break
            assistant.process_command(cmd)
    except (KeyboardInterrupt, EOFError):
        print(f"\nExiting {ASSISTANT_NAME}...")
    finally:
        assistant.shutdown()


def run_gui_mode(assistant, enable_voice: bool = True):
    """Launch full PySide6 Desktop GUI."""
    from PySide6.QtWidgets import QApplication
    from app.gui.main_window import MainWindow

    # Configure high-DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName(ASSISTANT_NAME)
    app.setOrganizationName("AI Agent Architecture")

    window = MainWindow(assistant)
    window.show()

    if not enable_voice:
        assistant.voice_listener.mic_enabled = False

    logger.info(f"{ASSISTANT_NAME} GUI loaded and active.")
    sys.exit(app.exec())


def main():
    parser = argparse.ArgumentParser(description=f"{ASSISTANT_NAME} Universal Computer Agent")
    parser.add_argument("--gui", action="store_true", default=False, help="Run full desktop GUI interface (default)")
    parser.add_argument("--cli", action="store_true", default=False, help="Run in terminal CLI mode without GUI")
    parser.add_argument("--voice", action="store_true", default=True, help="Enable hands-free voice control (default)")
    parser.add_argument("--no-voice", action="store_true", default=False, help="Disable voice listening at launch")
    parser.add_argument("--safe-mode", action="store_true", default=True, help="Enable confirmation for destructive actions")
    args = parser.parse_args()

    enable_voice = args.voice and not args.no_voice

    logger.info(f"Booting {ASSISTANT_NAME} Core System...")

    from app.core.assistant import NivaAssistant
    assistant = NivaAssistant(safe_mode=args.safe_mode)

    if args.cli:
        run_cli_mode(assistant, enable_voice=enable_voice)
    else:
        run_gui_mode(assistant, enable_voice=enable_voice)


if __name__ == "__main__":
    main()
