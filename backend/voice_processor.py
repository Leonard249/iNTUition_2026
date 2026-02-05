from faster_whisper import WhisperModel
import tempfile
import os
from typing import Optional, Tuple
import numpy as np
import soundfile as sf

class VoiceProcessor:
    def __init__(self, model_size: str = "base", device: str = "cuda", compute_type: str = "float16"):
        # Load FasterWhisper model (runs locally, no API costs)
        self.model = WhisperModel(
            model_size,  # "base" is fast and accurate
            device=device,  # GPU or CPU
            compute_type=compute_type,  # Precision for speed
            download_root="./models"  # Where to cache the model
        )
    
    async def transcribe_audio(self, audio_data: bytes, language: Optional[str] = None) -> dict:
        """
        Convert voice audio to text
        Input: Raw audio bytes from microphone
        Output: {"text": "user said this", "segments": [...]}
        """
        
        # 1. Save audio to temporary file (Whisper needs file path)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            # 2. Transcribe with FasterWhisper
            segments, info = self.model.transcribe(
                tmp_path,  # Audio file path
                language=language,  # Optional: "en", "es", "fr", etc.
                beam_size=5,  # Balance between speed and accuracy
                vad_filter=True,  # Remove silence automatically
                vad_parameters=dict(
                    min_silence_duration_ms=500,  # 0.5 second silence = cut
                    threshold=0.5  # Voice detection sensitivity
                )
            )
            
            # 3. Process results
            transcript_segments = []
            full_text = ""
            
            for segment in segments:
                transcript_segments.append({
                    "text": segment.text,
                    "start": segment.start,  # Timestamp in seconds
                    "end": segment.end,
                    "confidence": getattr(segment, 'avg_logprob', 0.0)  # How sure Whisper is
                })
                full_text += segment.text + " "
            
            return {
                "text": full_text.strip(),  # Final transcription
                "segments": transcript_segments,  # Word-by-word timing
                "language": info.language,  # Detected language
                "language_probability": info.language_probability  # Confidence
            }
            
        finally:
            # 4. Clean up temp file
            os.unlink(tmp_path)
    
    async def process_audio_chunk(self, chunk_data: bytes, is_final: bool = False) -> dict:
        """For streaming audio (real-time transcription)"""
        # Currently simple - in production, accumulate chunks
        return await self.transcribe_audio(chunk_data)