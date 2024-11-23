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
