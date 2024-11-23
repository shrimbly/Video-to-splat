import os
import cv2
import numpy as np
import subprocess
from typing import List, Tuple
import logging
import re

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ImageData:
    def __init__(self, relative_path: str, blurriness_score: float = None):
        self.relative_path = relative_path
        self.blurriness_score = blurriness_score
        self.badges = []

def calculate_blurriness(image_path: str) -> float:
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        logger.warning(f"Failed to read image: {image_path}")
        return None
    
    score = cv2.Laplacian(img, cv2.CV_64F).var()
    logger.debug(f"Calculated blurriness score for {image_path}: {score}")
    return score

def process_batch(image_data: List[ImageData], batch_size: int = 10) -> List[Tuple[str, float]]:
    batch_scores = []
    for img in image_data[:batch_size]:
        if img.blurriness_score is None:
            img.blurriness_score = calculate_blurriness(img.relative_path)
        if img.blurriness_score is None:
            logger.warning(f"Failed to calculate blurriness score for {img.relative_path}")
        batch_scores.append((img.relative_path, img.blurriness_score))
    logger.debug(f"Processed batch scores: {batch_scores}")
    return batch_scores

def select_best_images(batch_scores: List[Tuple[str, float]], threshold: float, min_images: int, max_images: int) -> List[str]:
    # Filter out None values
    valid_scores = [(path, score) for path, score in batch_scores if score is not None]
    
    if not valid_scores:
        logger.warning("No valid scores in batch")
        return []

    scores = [score for _, score in valid_scores]
    mean_score = np.mean(scores)
    std_dev = np.std(scores)

    logger.debug(f"Batch stats: mean={mean_score}, std_dev={std_dev}, threshold={threshold}")

    # Sort scores in descending order (higher score is better)
    sorted_scores = sorted(valid_scores, key=lambda x: x[1], reverse=True)
    logger.debug(f"Sorted scores: {sorted_scores}")

    selected_paths = []
    if std_dev > threshold * mean_score:
        logger.debug("High variability in scores")
        selected_paths = [path for path, score in sorted_scores if score > mean_score + std_dev]
    else:
        logger.debug("Low variability in scores")
        selected_paths = [path for path, score in sorted_scores if score > mean_score]

    # Ensure the number of selected images is within the specified range
    if len(selected_paths) < min_images:
        selected_paths = [path for path, _ in sorted_scores[:min_images]]
    elif len(selected_paths) > max_images:
        selected_paths = selected_paths[:max_images]

    logger.debug(f"Selected paths: {selected_paths}")
    return selected_paths

def analyze_best_images(image_data: List[ImageData], batch_size: int = 10, threshold: float = 1.5, min_images: int = 2, max_images: int = 7) -> List[str]:
    best_image_paths = []
    for i in range(0, len(image_data), batch_size):
        batch = image_data[i:i+batch_size]
        batch_scores = process_batch(batch, batch_size)
        selected_paths = select_best_images(batch_scores, threshold, min_images, max_images)
        best_image_paths.extend(selected_paths)
    logger.info(f"Total best image paths: {len(best_image_paths)}")
    return best_image_paths

def extract_frames(video_path, output_dir, fps, new_width=None, progress_queue=None):
    """Extract frames from video with progress updates"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Create FFmpeg command
    ffmpeg_cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f'fps={fps}'
    ]
    
    if new_width:
        ffmpeg_cmd[-1] = f'fps={fps},scale={new_width}:-1'
    
    ffmpeg_cmd.extend([
        os.path.join(output_dir, 'frame_%06d.jpg'),
        '-hide_banner',
        '-stats',
        '-loglevel', 'info'
    ])

    logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")

    # Start FFmpeg process
    process = subprocess.Popen(
        ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )

    frames_processed = 0
    
    # Read FFmpeg output in real-time from stderr
    while True:
        line = process.stderr.readline()
        if not line and process.poll() is not None:
            break
            
        if 'frame=' in line:
            try:
                frame_match = re.search(r'frame=\s*(\d+)', line)
                if frame_match and progress_queue is not None:
                    frames_processed = int(frame_match.group(1))
                    progress_queue.put(frames_processed)
                    logger.debug(f"Put frame {frames_processed} in queue")
            except Exception as e:
                logger.error(f"Error parsing FFmpeg output: {e}")
        
        # Also log the raw FFmpeg output for debugging
        logger.debug(f"FFmpeg output: {line.strip()}")

    process.wait()

    if process.returncode != 0:
        error_output = process.stderr.read()
        raise RuntimeError(f"FFmpeg failed with error: {error_output}")

    # Get list of extracted frames
    extracted_frames = sorted([
        f for f in os.listdir(output_dir)
        if f.startswith('frame_') and f.endswith('.jpg')
    ])

    # Put one final update to ensure we show 100% completion
    if progress_queue is not None:
        progress_queue.put(len(extracted_frames))

    return extracted_frames

def get_video_info(video_path: str) -> dict:
    try:
        result = subprocess.run([
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-count_packets',
            '-show_entries', 'stream=width,height,r_frame_rate,nb_read_packets',
            '-of', 'csv=p=0',
            video_path
        ], capture_output=True, text=True, check=True)
        
        width, height, frame_rate, total_frames = result.stdout.strip().split(',')
        frame_rate = eval(frame_rate)  # This safely evaluates the fraction
        
        return {
            'resolution': f"{width}x{height}",
            'frame_rate': frame_rate,
            'total_frames': int(total_frames),
            'duration': int(total_frames) / frame_rate
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting video info: {e}")
        logger.error(f"ffprobe stderr: {e.stderr}")
        raise RuntimeError(f"Failed to get video info: {e}")
