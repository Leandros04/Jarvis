import time
import winsound

import numpy as np
import sounddevice as sd
import openwakeword
from openwakeword.model import Model


# ============================================================
# CONFIGURATION
# ============================================================

SAMPLE_RATE = 16000
CHANNELS = 1

# openWakeWord works efficiently with 80 ms frames.
CHUNK_SIZE = 1280

WAKEWORD_MODEL = "hey_jarvis"

# Default openWakeWord recommendation is around 0.5.
# Slightly higher = fewer accidental activations.
WAKEWORD_THRESHOLD = 0.60

# Voice activity filtering helps reject non-speech sounds.
VAD_THRESHOLD = 0.35

# Prevent an immediate second trigger.
COOLDOWN_SECONDS = 1.5


# ============================================================
# GLOBAL STATE
# ============================================================

_wake_model = None


# ============================================================
# MODEL SETUP
# ============================================================

def load_wakeword_model():
    global _wake_model

    if _wake_model is not None:
        return _wake_model

    print(
        "[WAKE] Preparing Hey Jarvis model..."
    )

    # Downloads only the Jarvis model plus the
    # feature models required by openWakeWord.
    # Files are cached locally afterward.
    openwakeword.utils.download_models(
        model_names=[
            WAKEWORD_MODEL
        ]
    )

    print(
        "[WAKE] Loading wake-word model..."
    )

    _wake_model = Model(
        wakeword_models=[
            WAKEWORD_MODEL
        ],
        inference_framework="onnx",
        vad_threshold=VAD_THRESHOLD,
    )

    print(
        "[WAKE] Wake-word model ready."
    )

    return _wake_model


# ============================================================
# MICROPHONE
# ============================================================

def get_default_microphone():
    try:
        input_device, _ = (
            sd.default.device
        )

        device = sd.query_devices(
            input_device
        )

        return {
            "success": True,
            "index": input_device,
            "name": device["name"],
            "input_channels": (
                device[
                    "max_input_channels"
                ]
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# BEEP
# ============================================================

def activation_beep():
    try:
        winsound.Beep(
            950,
            120
        )

    except Exception:
        pass


# ============================================================
# WAIT FOR "HEY JARVIS"
# ============================================================

def wait_for_wakeword(
    threshold=WAKEWORD_THRESHOLD
):
    try:
        model = (
            load_wakeword_model()
        )

        # Reset previous prediction history.
        model.reset()

        print()
        print(
            "[WAKE] Listening for "
            "\"Hey Jarvis\"..."
        )

        last_trigger = 0.0

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        ) as stream:

            while True:

                audio, overflowed = (
                    stream.read(
                        CHUNK_SIZE
                    )
                )

                if overflowed:
                    # Missing an occasional audio
                    # block is not fatal.
                    continue

                frame = np.asarray(
                    audio[:, 0],
                    dtype=np.int16
                )

                prediction = (
                    model.predict(
                        frame
                    )
                )

                if not prediction:
                    continue

                # We only loaded one model,
                # but this makes the code robust
                # if that changes later.
                best_model = max(
                    prediction,
                    key=prediction.get
                )

                best_score = float(
                    prediction[
                        best_model
                    ]
                )

                now = time.time()

                if (
                    best_score
                    >= threshold
                    and
                    (
                        now
                        - last_trigger
                    )
                    >= COOLDOWN_SECONDS
                ):

                    last_trigger = now

                    print()
                    print(
                        "[WAKE] HEY JARVIS detected"
                    )

                    print(
                        f"[WAKE] Score: "
                        f"{best_score:.3f}"
                    )

                    model.reset()

                    activation_beep()

                    return {
                        "success": True,
                        "model": best_model,
                        "score": best_score,
                    }

    except KeyboardInterrupt:
        return {
            "success": False,
            "cancelled": True,
            "error": (
                "Wake-word listening "
                "was interrupted."
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# CONTINUOUS TEST
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )
    print(
        "        JARVIS WAKE WORD TEST"
    )
    print(
        "=========================================="
    )
    print()

    microphone = (
        get_default_microphone()
    )

    if not microphone.get(
        "success"
    ):

        print(
            "Microphone error:"
        )

        print(
            microphone[
                "error"
            ]
        )

        raise SystemExit

    print(
        "Microphone:"
    )

    print(
        microphone["name"]
    )

    print()

    try:
        load_wakeword_model()

    except Exception as e:

        print(
            "Wake-word model error:"
        )

        print(
            e
        )

        raise SystemExit

    print()
    print(
        "Say \"Hey Jarvis\"."
    )

    print(
        "Press Ctrl+C to stop."
    )

    while True:

        result = (
            wait_for_wakeword()
        )

        if result.get(
            "cancelled"
        ):
            break

        if not result.get(
            "success"
        ):

            print(
                "ERROR:",
                result.get(
                    "error"
                )
            )

            break

        print()
        print(
            "Wake word detected successfully."
        )

        print(
            "Listening again..."
        )

    print()
    print(
        "Wake-word test ended."
    )