"""Entry point: python -m voiceflow"""

from __future__ import annotations

import platform
import sys

from voiceflow.config import load_config
from voiceflow.pipeline import VoiceTypePipeline


def main() -> None:
    if platform.system() != "Darwin":
        print("Error: VoiceFlow requires macOS.")
        sys.exit(1)

    cfg = load_config()
    pipeline = VoiceTypePipeline(cfg)
    try:
        pipeline.run()
    except KeyboardInterrupt:
        print("\nShutting down.")
        pipeline.stop()


if __name__ == "__main__":
    main()
