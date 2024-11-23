# Video Frame Extractor and Image Analysis Tool

A powerful desktop application for extracting high-quality frames from videos and analyzing them for photogrammetry purposes. Built with Python and DearPyGui, this tool helps automate the process of selecting the best frames for 3D reconstruction.

## Features

### Video Processing
- Extract frames from videos at customizable FPS rates
- Optional frame resizing while maintaining aspect ratio
- Progress tracking during extraction
- Support for common video formats (MP4, AVI, MOV, MKV)

### Image Analysis
- Automatic blur detection using Laplacian variance
- Batch processing of images
- Smart selection of best frames based on quality metrics
- Configurable minimum and maximum image selection
- Detailed statistics and analysis results

### Integration
- Direct integration with RealityCapture for 3D reconstruction
- Darktable integration for advanced image processing
- Automatic project organization and file management

## Requirements

### Software Dependencies
- Python 3.7+
- FFmpeg (must be in system PATH)
- RealityCapture (optional, for 3D reconstruction)
- Darktable (optional, for image processing)

### Python Packages

## Installation Guide

### Basic Installation

1. **Install Python**
   - Download Python 3.7+ from [python.org](https://python.org)
   - During installation, check "Add Python to PATH"
   - Verify installation:
   ```powershell
   python --version
   ```

2. **Install FFmpeg**
   - Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Extract the zip file
   - Add FFmpeg to PATH:
     - Copy the path to ffmpeg/bin folder
     - Open System Properties → Advanced → Environment Variables
     - Add to System PATH
   - Verify installation:
   ```powershell
   ffmpeg -version
   ```

3. **Clone Repository**
   ```powershell
   git clone https://github.com/shrimbly/Video-to-splat.git
   cd Video-to-splat
   ```

4. **Create Virtual Environment**
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

5. **Install Dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

### Advanced Installation (Optional)

1. **RealityCapture Integration**
   - Install RealityCapture
   - Update `config.py` with RC path:
   ```python
   RC_EXECUTABLE = r"C:\Program Files\Capturing Reality\RealityCapture\RealityCapture.exe"
   ```

2. **Darktable Integration**
   - Download Darktable from [darktable.org](https://darktable.org/install/)
   - Install and update `config.py`:
   ```python
   DARKTABLE_EXECUTABLE = r"C:\Program Files\darktable\bin\darktable.exe"
   ```

3. **Configure Output Directories**
   - Open `config.py`
   - Set your preferred paths:
   ```python
   AUTOMATIC_OUTPUT_DIR = r"path\to\your\output\directory"
   SOURCE_IMAGES_DIR = "Source Images"
   BEST_IMAGES_DIR = "Best Images"
   ```

### Troubleshooting

1. **FFmpeg Not Found**
   - Ensure FFmpeg is in PATH
   - Restart terminal/IDE after PATH changes
   - Try using full path in config

2. **Import Errors**
   - Verify virtual environment is activated
   - Reinstall requirements:
   ```powershell
   pip install --upgrade -r requirements.txt
   ```

3. **Permission Issues**
   - Run terminal as administrator
   - Check folder permissions
   - Verify write access to output directories

4. **Video Processing Errors**
   - Ensure video codec is supported
   - Check available disk space
   - Verify video file isn't corrupted
