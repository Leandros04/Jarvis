import time
import threading

import numpy as np
import sounddevice as sd
import pyttsx3
from faster_whisper import WhisperModel


# ============================================================
# CONFIGURATION
# ============================================================

SAMPLE_RATE = 16000
CHANNELS = 1

# Good compromise between accuracy and speed.
WHISPER_MODEL_SIZE = "base"

# Recording behaviour
CALIBRATION_SECONDS = 0.7
MAX_WAIT_FOR_SPEECH = 8.0
MAX_RECORD_SECONDS = 20.0
SILENCE_TO_STOP = 1.2

# Minimum threshold so a completely silent room
# doesn't create an absurdly low trigger threshold.
MIN_SPEECH_THRESHOLD = 0.008

# Multiply measured room noise by this amount.
NOISE_MULTIPLIER = 2.8


# ============================================================
# GLOBAL STATE
# ============================================================

_whisper_model = None
_tts_engine = None
_tts_lock = threading.Lock()


# ============================================================
# MICROPHONE INFORMATION
# ============================================================

def list_audio_devices():
    try:
        devices = sd.query_devices()

        result = []

        for index, device in enumerate(devices):

            result.append({
                "index": index,
                "name": device["name"],
                "inputs": device["max_input_channels"],
                "outputs": device["max_output_channels"],
                "default_samplerate": device["default_samplerate"],
            })

        return {
            "success": True,
            "devices": result,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_default_microphone():
    try:
        input_device, _ = sd.default.device

        info = sd.query_devices(
            input_device
        )

        return {
            "success": True,
            "index": input_device,
            "name": info["name"],
            "input_channels": info["max_input_channels"],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# WHISPER
# ============================================================

def load_whisper():
    global _whisper_model

    if _whisper_model is not None:
        return _whisper_model

    print(
        f"[VOICE] Loading Whisper model: "
        f"{WHISPER_MODEL_SIZE}"
    )

    print(
        "[VOICE] First launch may download "
        "the model."
    )

    _whisper_model = WhisperModel(
        WHISPER_MODEL_SIZE,
        device="cpu",
        compute_type="int8",
    )

    print(
        "[VOICE] Whisper ready."
    )

    return _whisper_model


# ============================================================
# AUDIO UTILITIES
# ============================================================

def _rms(audio):
    if len(audio) == 0:
        return 0.0

    audio = np.asarray(
        audio,
        dtype=np.float32
    )

    return float(
        np.sqrt(
            np.mean(
                np.square(audio)
            )
        )
    )


def calibrate_microphone():
    try:
        print(
            "[VOICE] Measuring room noise..."
        )

        audio = sd.rec(
            int(
                SAMPLE_RATE
                * CALIBRATION_SECONDS
            ),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
        )

        sd.wait()

        audio = audio.flatten()

        noise_level = _rms(
            audio
        )

        threshold = max(
            MIN_SPEECH_THRESHOLD,
            noise_level
            * NOISE_MULTIPLIER
        )

        print(
            f"[VOICE] Noise level: "
            f"{noise_level:.4f}"
        )

        print(
            f"[VOICE] Speech threshold: "
            f"{threshold:.4f}"
        )

        return {
            "success": True,
            "noise_level": noise_level,
            "threshold": threshold,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# RECORD UNTIL SILENCE
# ============================================================

def listen():
    try:
        calibration = (
            calibrate_microphone()
        )

        if not calibration.get(
            "success"
        ):
            return calibration

        threshold = calibration[
            "threshold"
        ]

        block_duration = 0.10

        block_size = int(
            SAMPLE_RATE
            * block_duration
        )

        recorded_blocks = []

        speech_started = False

        silence_time = 0.0

        start_time = time.time()

        print()
        print(
            "Listening..."
        )

        print(
            "Speak normally."
        )

        def callback(
            indata,
            frames,
            callback_time,
            status
        ):
            nonlocal speech_started
            nonlocal silence_time

            if status:
                pass

            block = (
                indata[:, 0]
                .copy()
            )

            volume = _rms(
                block
            )

            if speech_started:

                recorded_blocks.append(
                    block
                )

                if volume >= threshold:
                    silence_time = 0.0

                else:
                    silence_time += (
                        block_duration
                    )

            else:

                if volume >= threshold:

                    speech_started = True

                    silence_time = 0.0

                    recorded_blocks.append(
                        block
                    )

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=block_size,
            callback=callback,
        ):

            while True:

                elapsed = (
                    time.time()
                    - start_time
                )

                if (
                    not speech_started
                    and elapsed
                    >= MAX_WAIT_FOR_SPEECH
                ):
                    return {
                        "success": False,
                        "error": (
                            "No speech detected."
                        ),
                    }

                if (
                    speech_started
                    and silence_time
                    >= SILENCE_TO_STOP
                ):
                    break

                if (
                    elapsed
                    >= MAX_RECORD_SECONDS
                ):
                    break

                time.sleep(
                    0.05
                )

        if not recorded_blocks:
            return {
                "success": False,
                "error": (
                    "No audio was recorded."
                ),
            }

        audio = np.concatenate(
            recorded_blocks
        )

        print(
            "[VOICE] Recording complete."
        )

        return {
            "success": True,
            "audio": audio,
            "sample_rate": SAMPLE_RATE,
            "seconds": round(
                len(audio)
                / SAMPLE_RATE,
                2
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# TRANSCRIPTION
# ============================================================

def transcribe_audio(
    audio
):
    try:
        model = load_whisper()

        print(
            "[VOICE] Transcribing..."
        )

        segments, info = (
            model.transcribe(
                audio,
                beam_size=1,
                vad_filter=True,
            )
        )

        text_parts = []

        for segment in segments:

            text = (
                segment.text
                .strip()
            )

            if text:
                text_parts.append(
                    text
                )

        text = " ".join(
            text_parts
        ).strip()

        if not text:
            return {
                "success": False,
                "error": (
                    "Speech was detected, "
                    "but no words were "
                    "recognized."
                ),
            }

        return {
            "success": True,
            "text": text,
            "language": (
                info.language
            ),
            "language_probability": round(
                info.language_probability,
                3
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def listen_and_transcribe():
    recording = listen()

    if not recording.get(
        "success"
    ):
        return recording

    transcription = (
        transcribe_audio(
            recording["audio"]
        )
    )

    if not transcription.get(
        "success"
    ):
        return transcription

    return {
        "success": True,
        "text": transcription[
            "text"
        ],
        "language": transcription[
            "language"
        ],
        "language_probability": (
            transcription[
                "language_probability"
            ]
        ),
        "seconds": recording[
            "seconds"
        ],
    }


# ============================================================
# TEXT TO SPEECH
# ============================================================

def _load_tts():
    global _tts_engine

    if _tts_engine is not None:
        return _tts_engine

    engine = pyttsx3.init(
        "sapi5"
    )

    engine.setProperty(
        "rate",
        190
    )

    engine.setProperty(
        "volume",
        1.0
    )

    voices = engine.getProperty(
        "voices"
    )

    # Prefer a reasonably Jarvis-like
    # Microsoft male voice if installed.
    preferred_names = [
        "david",
        "mark",
        "george",
        "guy",
        "james",
    ]

    selected = None

    for preferred in (
        preferred_names
    ):

        for voice in voices:

            voice_name = (
                voice.name
                .lower()
            )

            if preferred in voice_name:

                selected = voice

                break

        if selected:
            break

    if selected:

        engine.setProperty(
            "voice",
            selected.id
        )

        print(
            f"[VOICE] TTS voice: "
            f"{selected.name}"
        )

    elif voices:

        engine.setProperty(
            "voice",
            voices[0].id
        )

        print(
            f"[VOICE] TTS voice: "
            f"{voices[0].name}"
        )

    _tts_engine = engine

    return engine


def speak(text):
    try:
        text = str(
            text
        ).strip()

        if not text:
            return {
                "success": False,
                "error": (
                    "Nothing to speak."
                ),
            }

        with _tts_lock:

            engine = _load_tts()

            engine.say(
                text
            )

            engine.runAndWait()

        return {
            "success": True,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# TEST MODE
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )

    print(
        "        JARVIS VOICE ENGINE TEST"
    )

    print(
        "=========================================="
    )

    print()

    microphone = (
        get_default_microphone()
    )

    if microphone.get(
        "success"
    ):

        print(
            "Microphone:"
        )

        print(
            microphone["name"]
        )

    else:

        print(
            "Microphone error:"
        )

        print(
            microphone["error"]
        )

        raise SystemExit

    print()

    # Load once now so the first
    # transcription isn't delayed later.
    load_whisper()

    print()

    speak(
        "Voice systems online."
    )

    while True:

        command = input(
            "\nPress ENTER to speak "
            "or type exit: "
        ).strip()

        if command.lower() in {
            "exit",
            "quit"
        }:
            break

        result = (
            listen_and_transcribe()
        )

        print()

        if not result.get(
            "success"
        ):

            print(
                "ERROR:",
                result.get(
                    "error"
                )
            )

            continue

        print(
            "YOU SAID:"
        )

        print(
            result["text"]
        )

        print()

        print(
            "Detected language:",
            result[
                "language"
            ]
        )

        speak(
            "I heard you say. "
            + result["text"]
        )

    speak(
        "Voice systems offline."
    )

    print(
        "\nVoice test ended."
    )