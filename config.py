import os

# Default paths
SOURCE_IMAGES_DIR = "Source Images"
BEST_IMAGES_DIR = "Best Images"
AUTOMATIC_OUTPUT_DIR = r"C:\Users\Admin\Documents\Splats\Training data\Automatic" #This is where the project folder will be created

# Executable paths (can be overridden by environment variables)
RC_EXECUTABLE = os.getenv('RC_EXECUTABLE', r"C:\Program Files\Capturing Reality\RealityCapture\RealityCapture.exe")
DARKTABLE_EXECUTABLE = os.getenv('DARKTABLE_EXECUTABLE', r"C:\Program Files\darktable\bin\darktable.exe")

# Analysis settings
DEFAULT_FPS = 5
BATCH_SIZE = 10
THRESHOLD = 1.5
