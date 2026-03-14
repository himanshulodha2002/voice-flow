"""Entry point: python -m voiceflow"""

from __future__ import annotations

import platform
import sys

from voiceflow.config import load_config
from voiceflow.log import setup_logging
from voiceflow.pipeline import VoiceTypePipeline
from voiceflow.app import VoiceFlowApp


def main() -> None:
    if platform.system() != "Darwin":
        print("Error: VoiceFlow requires macOS.")
        sys.exit(1)

    setup_logging()

    cfg = load_config()
    pipeline = VoiceTypePipeline(cfg)
    pipeline.run()  # non-blocking: starts listener + worker + model warmup

    app = VoiceFlowApp(pipeline)
    app.run()  # blocks on NSRunLoop


if __name__ == "__main__":
    main()
