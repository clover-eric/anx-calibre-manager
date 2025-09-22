import base64
from mutagen.mp4 import MP4
import json

def extract_m4b_metadata(file_path):
    """
    Extracts metadata from an M4B file.
    """
    try:
        audio = MP4(file_path)
        metadata = {
            'title': audio.get('\xa9nam', ['Unknown Title'])[0],
            'artist': audio.get('\xa9ART', ['Unknown Artist'])[0],
            'album': audio.get('\xa9alb', [None])[0],
            'album_artist': audio.get('aART', [None])[0],
            'genre': audio.get('\xa9gen', [None])[0],
            'year': audio.get('\xa9day', [None])[0],
            'composer': audio.get('\xa9wrt', [None])[0],
            'description': audio.get('desc', [audio.get('ldes', [None])[0]])[0],
            'comment': audio.get('\xa9cmt', [None])[0],
            'duration': audio.info.length,
            'chapters': [],
            'cover': None
        }

        # Extract cover image
        if 'covr' in audio and audio['covr']:
            cover_data = audio['covr'][0]
            mime_type = 'image/jpeg' if cover_data.imageformat == 13 else 'image/png'
            metadata['cover'] = f"data:{mime_type};base64,{base64.b64encode(cover_data).decode('utf-8')}"

        # Extract chapters from Nero format tag
        if '----:com.apple.iTunes:chapters' in audio:
            nero_chapters_raw = audio['----:com.apple.iTunes:chapters'][0]
            nero_chapters_str = nero_chapters_raw.decode('utf-8')
            
            chapter_lines = nero_chapters_str.strip().split('\n')
            
            times = {}
            names = {}

            for line in chapter_lines:
                if line.startswith('CHAPTER'):
                    key, value = line.split('=', 1)
                    chapter_num_str = key[7:]
                    
                    if chapter_num_str.endswith('NAME'):
                        chapter_index = int(chapter_num_str[:-4])
                        names[chapter_index] = value
                    else:
                        chapter_index = int(chapter_num_str)
                        time_parts = value.split(':')
                        seconds_parts = time_parts[2].split('.')
                        
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        seconds = int(seconds_parts[0])
                        milliseconds = int(seconds_parts[1])
                        
                        total_seconds = (hours * 3600) + (minutes * 60) + seconds + (milliseconds / 1000)
                        times[chapter_index] = total_seconds

            sorted_indices = sorted(times.keys())

            for i in sorted_indices:
                start_time = times[i]
                end_time = metadata['duration']
                if i + 1 in sorted_indices:
                    end_time = times[i+1]
                
                metadata['chapters'].append({
                    'title': names.get(i, f'Chapter {i}'),
                    'start': start_time,
                    'end': end_time
                })

        return metadata
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {e}")
        return None
