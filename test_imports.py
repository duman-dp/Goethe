# Simple test to check all imports work
print("Testing imports...")

try:
    import faster_whisper
    print("✅ faster-whisper OK")
except ImportError as e:
    print(f"❌ faster-whisper failed: {e}")

try:
    import yaml
    print("✅ yaml OK")
except ImportError as e:
    print(f"❌ yaml failed: {e}")

try:
    import ffmpeg
    print("✅ ffmpeg-python OK")
except ImportError as e:
    print(f"❌ ffmpeg-python failed: {e}")

print("Test complete!")
