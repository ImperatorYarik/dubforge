import logging

import soundfile as sf
import torch
from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForSequenceClassification

logger = logging.getLogger(__name__)

# HuggingFace model — wav2vec2 fine-tuned on speech emotion recognition.
# Labels: angry, calm, disgust, fearful, happy, neutral, sad, surprised
MODEL_ID = "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"

_LABEL_MAP = {
    "angry":     "angry",
    "calm":      "neutral",
    "disgust":   "disgusted",
    "fearful":   "fearful",
    "happy":     "happy",
    "neutral":   "neutral",
    "sad":       "sad",
    "surprised": "surprise",
}

_model = None
_extractor = None


def _get_emotion_model():
    global _model, _extractor
    if _model is None:
        device = "cpu"
        logger.info(f"Loading emotion classifier on {device}...")
        _extractor = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_ID)
        _model = Wav2Vec2ForSequenceClassification.from_pretrained(MODEL_ID).to(device)
        _model.eval()
        logger.info("Emotion classifier ready")
    return _model, _extractor


def detect_emotion(segment_audio_path: str) -> tuple[str, float]:
    model, extractor = _get_emotion_model()
    device = next(model.parameters()).device

    audio, sampling_rate = sf.read(segment_audio_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    target_sr = extractor.sampling_rate  # 16000
    if sampling_rate != target_sr:
        import torchaudio
        waveform = torch.from_numpy(audio).unsqueeze(0)
        audio = torchaudio.functional.resample(waveform, sampling_rate, target_sr).squeeze(0).numpy()
        sampling_rate = target_sr

    inputs = extractor(audio, sampling_rate=sampling_rate, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        logits = model(**inputs).logits

    scores = torch.softmax(logits, dim=-1)[0]
    top_idx = scores.argmax().item()
    raw_label = model.config.id2label[top_idx].lower()
    emotion = _LABEL_MAP.get(raw_label, "neutral")
    score = float(scores[top_idx])
    logger.info(f"Emotion detected: {emotion} (raw={raw_label}, score={score:.2f})")
    return emotion, score