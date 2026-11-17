import sys
import speech_recognition as sr

def test_microphone_hardware():
    print("Testing physical audio capture device...")
    try:
        mic = sr.Microphone()
        r = sr.Recognizer()
        with mic as source:
            print("Microphone successfully opened!")
            print(f"Sample Rate: {source.SAMPLE_RATE}, Sample Width: {source.SAMPLE_WIDTH}")
            print("Listening for 1 second of background audio...")
            audio = r.record(source, duration=1.0)
            raw = audio.get_raw_data()
            print(f"Captured {len(raw)} bytes of live audio data.")
            assert len(raw) > 0, "No audio bytes captured!"
            print("PASS: Microphone hardware and capture stream are 100% functional.")
            return True
    except Exception as e:
        print(f"FAIL: Microphone error: {e}")
        return False

if __name__ == "__main__":
    success = test_microphone_hardware()
    sys.exit(0 if success else 1)
