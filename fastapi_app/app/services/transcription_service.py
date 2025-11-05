"""
Transcription service - handles the core transcription logic
Ported from the original infer.py RunPod implementation
"""
import ivrit
import types
import dataclasses
import logging
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger(__name__)

# Maximum size for grouped arrays (in characters)
MAX_STREAM_ELEMENT_SIZE = 500000

# Global variable to track currently loaded model
current_model = None


class TranscriptionService:
    """Service for handling transcription operations"""
    
    def __init__(self):
        self.current_model = None
    
    def transcribe(
        self,
        audio_url: Optional[str] = None,
        audio_file_path: Optional[str] = None,
        engine: str = 'faster-whisper',
        model: str = 'ivrit-ai/whisper-large-v3-turbo-ct2',
        language: str = 'he',
        diarize: bool = False,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """
        Perform transcription on audio file
        
        Args:
            audio_url: URL to audio file
            audio_file_path: Local or cloud storage path to audio file
            engine: Transcription engine ('faster-whisper' or 'stable-whisper')
            model: Model identifier
            language: Language code
            diarize: Enable speaker diarization
            options: Additional transcription options
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary containing transcription result with segments
        """
        global current_model
        
        # Validate engine
        if engine not in ['faster-whisper', 'stable-whisper']:
            raise ValueError(f"Engine should be 'faster-whisper' or 'stable-whisper', but is {engine}")
        
        # Check if we need to load a different model
        different_model = (
            not current_model or 
            current_model.engine != engine or 
            current_model.model != model
        )
        
        if different_model:
            logger.info(f'Loading new model: {engine} with {model}')
            current_model = ivrit.load_model(
                engine=engine,
                model=model,
                local_files_only=False  # Changed from True to allow downloading if needed
            )
            self.current_model = current_model
        else:
            logger.info(f'Reusing existing model: {engine} with {model}')
        
        # Prepare transcription arguments
        transcribe_args = {
            'language': language,
        }
        
        # Add audio source
        if audio_url:
            transcribe_args['url'] = audio_url
        elif audio_file_path:
            transcribe_args['path'] = audio_file_path
        else:
            raise ValueError("Either audio_url or audio_file_path must be provided")
        
        # Add additional options
        if options:
            transcribe_args.update(options)
        
        # Add diarization
        transcribe_args['diarize'] = diarize
        
        # Report progress
        if progress_callback:
            progress_callback(10)
        
        logger.info(f"Starting transcription with args: {transcribe_args}")
        
        # Perform transcription
        if diarize:
            # Non-streaming mode for diarization
            result = current_model.transcribe(**transcribe_args)
            segments = result['segments']
            
            if progress_callback:
                progress_callback(90)
            
            # Convert segments to dictionaries
            segments_list = []
            for seg in segments:
                if hasattr(seg, '__dict__'):
                    segments_list.append(dataclasses.asdict(seg))
                elif isinstance(seg, dict):
                    segments_list.append(seg)
                else:
                    segments_list.append({'text': str(seg)})
            
            return {
                'segments': segments_list,
                'text': self.extract_transcription_text(segments_list),
                'language': language
            }
        else:
            # Streaming mode
            transcribe_args['stream'] = True
            segments_gen = current_model.transcribe(**transcribe_args)
            
            if progress_callback:
                progress_callback(30)
            
            # Collect segments from generator
            segments_list = []
            
            if isinstance(segments_gen, types.GeneratorType):
                for seg in segments_gen:
                    if hasattr(seg, '__dict__'):
                        segments_list.append(dataclasses.asdict(seg))
                    elif isinstance(seg, dict):
                        segments_list.append(seg)
                    else:
                        segments_list.append({'text': str(seg)})
                    
                    # Update progress
                    if progress_callback and len(segments_list) % 10 == 0:
                        progress = min(30 + (len(segments_list) * 2), 90)
                        progress_callback(progress)
            else:
                # Handle list of segments
                for seg in segments_gen:
                    if hasattr(seg, '__dict__'):
                        segments_list.append(dataclasses.asdict(seg))
                    elif isinstance(seg, dict):
                        segments_list.append(seg)
                    else:
                        segments_list.append({'text': str(seg)})
            
            if progress_callback:
                progress_callback(90)
            
            return {
                'segments': segments_list,
                'text': self.extract_transcription_text(segments_list),
                'language': language
            }
    
    def extract_transcription_text(self, segments: List[Dict[str, Any]]) -> str:
        """
        Extract plain text from transcription segments
        
        Args:
            segments: List of transcription segments
            
        Returns:
            Concatenated text from all segments
        """
        if not segments:
            return ""
        
        text_parts = []
        for segment in segments:
            if isinstance(segment, dict) and 'text' in segment:
                text_parts.append(segment['text'])
            elif isinstance(segment, str):
                text_parts.append(segment)
        
        return ' '.join(text_parts).strip()
