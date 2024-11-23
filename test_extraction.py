import os
import subprocess
import logging
from config import DEFAULT_FPS

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def extract_frames(video_path: str, output_dir: str, fps: int, new_width: int = None):
    logger.info(f"Starting frame extraction: video_path={video_path}, output_dir={output_dir}, fps={fps}, new_width={new_width}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate new height if new_width is provided
    if new_width:
        scale_filter = f"scale={new_width}:-1"
    else:
        scale_filter = "scale=iw:ih"
    
    logger.info(f"Using scale filter: {scale_filter}")
    
    # Use FFmpeg to extract frames
    ffmpeg_command = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"{scale_filter},fps={fps}",
        "-q:v", "2",  # High quality (lower is better)
        os.path.join(output_dir, "frame_%04d.jpg")
    ]
    
    logger.info(f"FFmpeg command: {' '.join(ffmpeg_command)}")
    
    try:
        subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        logger.info("FFmpeg process completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg process failed with return code {e.returncode}")
        logger.error(f"FFmpeg stderr: {e.stderr}")
        raise

    extracted_frames = [f for f in os.listdir(output_dir) if f.endswith('.jpg')]
    logger.info(f"Extracted {len(extracted_frames)} frames")

    return extracted_frames

def main():
    video_path = r"C:\Users\Admin\Documents\Splats\Training data\GoPro Videos\4k-48ss-24fps-iso200.MP4"
    output_dir = r"C:\Users\Admin\Documents\Splats\Training data\GoPro Videos\frame extractor testing"
    fps = DEFAULT_FPS
    new_width = 720  # Set to None if you don't want to resize

    try:
        extracted_frames = extract_frames(video_path, output_dir, fps, new_width)
        print(f"Successfully extracted {len(extracted_frames)} frames to {output_dir}")
    except Exception as e:
        print(f"Error extracting frames: {str(e)}")

if __name__ == "__main__":
    main()