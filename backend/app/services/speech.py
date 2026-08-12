"""Azure AI Speech integration: STT + Pronunciation Assessment (unscripted) + TTS.

Every function here expects/produces 16 kHz, 16-bit, mono PCM WAV audio — the
Speech SDK's default push-stream format, which avoids needing GStreamer on the
server to decode compressed formats (webm/opus etc.) coming from the browser.
The frontend recorder (`frontend/src/lib/wavRecorder.ts`) encodes to that
exact format.
"""

import azure.cognitiveservices.speech as speechsdk

from app.core.config import get_settings

_WAV_HEADER_SIZE = 44  # standard PCM WAV header written by our own frontend encoder
_WAV_SAMPLE_RATE = 16000
_WAV_BYTES_PER_SAMPLE = 2  # 16-bit mono


def wav_duration_seconds(wav_bytes: bytes) -> float:
    payload_bytes = max(0, len(wav_bytes) - _WAV_HEADER_SIZE)
    return payload_bytes / (_WAV_SAMPLE_RATE * _WAV_BYTES_PER_SAMPLE)


class TranscriptionError(RuntimeError):
    pass


class SynthesisError(RuntimeError):
    pass


def _require_azure_config() -> tuple[str, str]:
    settings = get_settings()
    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise RuntimeError("AZURE_SPEECH_KEY/AZURE_SPEECH_REGION is not configured")
    return settings.azure_speech_key, settings.azure_speech_region


def transcribe_and_assess(wav_bytes: bytes) -> tuple[str, dict[str, float]]:
    """Transcribe a WAV clip and score pronunciation without a reference script.

    Returns (transcript, {"accuracy": .., "fluency": .., "completeness": .., "pronunciation": ..}),
    each a 0-100 score from Azure's unscripted pronunciation assessment.
    """
    key, region = _require_azure_config()
    settings = get_settings()

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.speech_recognition_language = settings.azure_speech_language

    stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=stream)

    pronunciation_config = speechsdk.PronunciationAssessmentConfig(
        reference_text="",  # empty reference text = unscripted assessment of free speech
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Word,
        enable_miscue=False,
    )

    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    pronunciation_config.apply_to(recognizer)

    # Our own WAV encoder always writes a standard 44-byte header before the
    # raw PCM payload; strip it since the push stream is pre-configured for
    # raw 16 kHz/16-bit/mono samples.
    stream.write(wav_bytes[_WAV_HEADER_SIZE:])
    stream.close()

    result = recognizer.recognize_once()

    if result.reason != speechsdk.ResultReason.RecognizedSpeech:
        raise TranscriptionError(f"Speech not recognized (reason={result.reason})")

    assessment = speechsdk.PronunciationAssessmentResult(result)
    scores = {
        "accuracy": assessment.accuracy_score,
        "fluency": assessment.fluency_score,
        "completeness": assessment.completeness_score,
        "pronunciation": assessment.pronunciation_score,
    }
    return result.text, scores


def synthesize_speech(text: str) -> bytes:
    """Synthesize `text` to a 16 kHz/16-bit/mono PCM WAV byte string, in memory."""
    key, region = _require_azure_config()
    settings = get_settings()

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.speech_synthesis_voice_name = settings.azure_tts_voice
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
    )

    # audio_config=None keeps output in memory instead of routing to a local speaker.
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise SynthesisError(f"Speech synthesis failed (reason={result.reason})")

    return result.audio_data
