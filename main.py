import cv2
import dearpygui.dearpygui as dpg
import os
import subprocess
from config import (
    AUTOMATIC_OUTPUT_DIR, SOURCE_IMAGES_DIR, BEST_IMAGES_DIR,
    DEFAULT_FPS, BATCH_SIZE, THRESHOLD,
    RC_EXECUTABLE, DARKTABLE_EXECUTABLE
)
from image_analyzer import extract_frames, get_video_info, analyze_best_images, ImageData, calculate_blurriness
import logging
import threading
import shutil
import textwrap
import statistics
from datetime import datetime
import queue
import time
import re

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Update these constants for styling
FONT_SIZE = 16
WINDOW_PADDING = 20
ITEM_SPACING = 10
BUTTON_WIDTH = 200
INPUT_WIDTH = 200

# Add at the top of the file with other global variables
default_font = None
bold_font = None
light_font = None
italic_font = None

class AppState:
    def __init__(self):
        self.video_path = ""
        self.output_dir = AUTOMATIC_OUTPUT_DIR  # Use the new default output path
        self.fps = DEFAULT_FPS
        self.new_width = None
        self.video_info = {}
        self.extracted_frames = []
        self.current_step = 0
        self.batch_size = 10
        self.threshold = 1.5
        self.project_name = ""
        self.project_folder = ""
        self.min_images = 2  # Updated default value
        self.max_images = 7  # Updated default value

app_state = AppState()

def setup_font():
    """Setup and return font handles"""
    global default_font, bold_font, light_font, italic_font
    
    with dpg.font_registry():
        font_dir = os.path.join(os.path.dirname(__file__), "fonts")
        default_font = dpg.add_font(os.path.join(font_dir, "Inter_18pt-Medium.ttf"), size=18)
        bold_font = dpg.add_font(os.path.join(font_dir, "Inter_18pt-Bold.ttf"), size=18)
        light_font = dpg.add_font(os.path.join(font_dir, "Inter_18pt-ExtraLight.ttf"), size=18)
        italic_font = dpg.add_font(os.path.join(font_dir, "Inter_18pt-Italic.ttf"), size=18)
        
        dpg.bind_font(default_font)
    
    return default_font, bold_font, light_font, italic_font

def setup_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Background color (light mode)
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (250, 250, 250), category=dpg.mvThemeCat_Core)
            # Text color
            dpg.add_theme_color(dpg.mvThemeCol_Text, (10, 10, 10), category=dpg.mvThemeCat_Core)
            # Button colors
            dpg.add_theme_color(dpg.mvThemeCol_Button, (230, 230, 230), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (220, 220, 220), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (200, 200, 200), category=dpg.mvThemeCat_Core)
            # Input colors
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (240, 240, 240), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (230, 230, 230), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (220, 220, 220), category=dpg.mvThemeCat_Core)
            # Slider colors
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (100, 100, 100), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (80, 80, 80), category=dpg.mvThemeCat_Core)
            # Styles
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, WINDOW_PADDING, WINDOW_PADDING, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, ITEM_SPACING, ITEM_SPACING, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0.5, 0.5, category=dpg.mvThemeCat_Core)

    dpg.bind_theme(global_theme)

def wrap_text(text, width=50):
    return textwrap.fill(text, width=width)

def create_project_folder():
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    app_state.project_folder = os.path.join(app_state.output_dir, f"{app_state.project_name}-{timestamp}")
    os.makedirs(app_state.project_folder, exist_ok=True)
    logger.info(f"Created project folder: {app_state.project_folder}")

def update_project_name(sender, app_data, user_data):
    app_state.project_name = app_data
    if app_state.project_name:
        dpg.configure_item("next_button_0", enabled=True)
    else:
        dpg.configure_item("next_button_0", enabled=False)

def confirm_project_name():
    if app_state.project_name:  # Only proceed if there's a project name
        advance_to_next_step()

def select_video(sender, app_data, user_data):
    try:
        file_path = subprocess.check_output([
            'powershell', '-command',
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$f = New-Object System.Windows.Forms.OpenFileDialog;"
            "$f.Filter = 'Video files (*.mp4;*.avi;*.mov;*.mkv)|*.mp4;*.avi;*.mov;*.mkv|All files (*.*)|*.*';"
            "if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $f.FileName } else { 'CANCELLED' }"
        ]).decode('utf-8').strip()

        if file_path and file_path != 'CANCELLED':
            app_state.video_path = file_path
            app_state.video_info = get_video_info(file_path)
            update_video_info()
            status_msg = f"Selected video:\n{wrap_text(os.path.basename(file_path))}"
            dpg.set_value("selected_video", status_msg)
            logger.info(status_msg)
            dpg.configure_item("next_button_1", enabled=True)
            advance_to_next_step()  # Automatically proceed to the next step
        else:
            dpg.set_value("selected_video", "No video selected.")
            logger.warning("No video selected.")
            dpg.configure_item("next_button_1", enabled=False)
    except Exception as e:
        error_msg = f"Error selecting video:\n{wrap_text(str(e))}"
        dpg.set_value("selected_video", error_msg)
        logger.error(error_msg)
        dpg.configure_item("next_button_1", enabled=False)

def update_video_info():
    info = app_state.video_info
    estimated_images = calculate_estimated_images(info['duration'], app_state.fps)
    video_info = f"Resolution: {info['resolution']}\n" \
                 f"Frame Rate: {info['frame_rate']:.2f} fps\n" \
                 f"Duration: {info['duration']:.2f} seconds\n" \
                 f"Total Frames: {info['total_frames']}\n" \
                 f"Estimated Images: {estimated_images}\n" \
                 f"Current FPS Setting: {app_state.fps}"
    dpg.set_value("video_info", wrap_text(video_info))
    logger.info(f"Video Info: {video_info}")

def calculate_estimated_images(duration, fps):
    return int(duration * fps)

def extract_frames_callback():
    if not app_state.video_path:
        status_msg = "Please select a video first."
        dpg.set_value("extract_status", status_msg)
        logger.warning(status_msg)
        return

    output_dir = os.path.join(app_state.project_folder, SOURCE_IMAGES_DIR)
    current_width = app_state.new_width if app_state.new_width and app_state.new_width > 0 else None
    
    logger.info(f"Starting extraction with settings:")
    logger.info(f"- Output directory: {output_dir}")
    logger.info(f"- FPS: {app_state.fps}")
    logger.info(f"- Target width: {current_width}")

    # Calculate total expected frames
    total_frames = calculate_estimated_images(app_state.video_info['duration'], app_state.fps)
    dpg.set_value("extract_status", f"Extraction started... (0/{total_frames} frames)")
    dpg.configure_item("extraction_progress", show=True)

    def extraction_thread():
        try:
            # Create a queue to receive progress updates
            progress_queue = queue.Queue()
            
            # Start a separate thread to update the UI
            def update_progress():
                last_update = 0
                while True:
                    try:
                        # Get all available updates
                        while True:
                            try:
                                frames_processed = progress_queue.get_nowait()
                                last_update = frames_processed
                            except queue.Empty:
                                break
                        
                        # Update UI with the latest count
                        if last_update > 0:
                            dpg.set_value("extract_status", 
                                f"Extracting frames... ({last_update}/{total_frames} frames)")
                            logger.debug(f"Updated UI with frame count: {last_update}")
                        
                        # Check if extraction is complete
                        if not extraction_running[0] and progress_queue.empty():
                            break
                            
                        time.sleep(0.1)  # Short sleep to prevent UI freezing
                        
                    except Exception as e:
                        logger.error(f"Error updating progress: {e}")
                        break

            extraction_running = [True]
            progress_thread = threading.Thread(target=update_progress, daemon=True)
            progress_thread.start()

            # Run the extraction
            extracted_frames = extract_frames(
                app_state.video_path, 
                output_dir, 
                app_state.fps, 
                new_width=current_width,
                progress_queue=progress_queue
            )

            # Signal that extraction is complete
            extraction_running[0] = False
            progress_thread.join()

            # Start sharpness calculation
            total_images = len(extracted_frames)
            app_state.extracted_frames = []
            
            def update_sharpness_progress():
                while True:
                    try:
                        frames_processed = sharpness_queue.get(timeout=0.5)
                        dpg.set_value("extract_status", 
                            f"Calculating image sharpness... ({frames_processed}/{total_images} images)")
                        logger.debug(f"Updated sharpness progress: {frames_processed}/{total_images}")
                        
                        if frames_processed >= total_images:
                            break
                    except queue.Empty:
                        if not sharpness_running[0]:
                            break
                    except Exception as e:
                        logger.error(f"Error updating sharpness progress: {e}")
                        break

            # Create new queue and thread for sharpness calculation
            sharpness_queue = queue.Queue()
            sharpness_running = [True]
            sharpness_thread = threading.Thread(target=update_sharpness_progress, daemon=True)
            sharpness_thread.start()

            # Process frames and update progress
            for i, frame in enumerate(extracted_frames):
                frame_path = os.path.join(output_dir, frame)
                sharpness_score = calculate_blurriness(frame_path)
                app_state.extracted_frames.append(
                    ImageData(frame, sharpness_score)
                )
                sharpness_queue.put(i + 1)
                logger.debug(f"Processed sharpness for frame {i+1}: {sharpness_score}")

            # Signal sharpness calculation is complete
            sharpness_running[0] = False
            sharpness_thread.join()
            
            status_msg = (
                f"Complete! Processed {len(app_state.extracted_frames)} images:\n"
                f"{wrap_text(output_dir)}"
            )
            dpg.set_value("extract_status", status_msg)
            logger.info(status_msg)
            dpg.configure_item("next_button_3", enabled=True)
            dpg.configure_item("extraction_progress", show=False)
            advance_to_next_step()

        except Exception as e:
            error_msg = f"Error processing frames:\n{wrap_text(str(e))}"
            dpg.set_value("extract_status", error_msg)
            logger.error(error_msg)
            dpg.configure_item("extraction_progress", show=False)

    extraction_thread = threading.Thread(target=extraction_thread)
    extraction_thread.start()

def update_fps(sender, app_data, user_data):
    app_state.fps = app_data
    logger.info(f"Updated frames per second to: {app_state.fps}")
    if app_state.video_info:
        update_video_info()
    else:
        dpg.set_value("video_info", f"Current FPS Setting: {app_state.fps}")

def update_new_width(sender, app_data, user_data):
    try:
        if app_data > 0:  # Only set width if greater than 0
            app_state.new_width = app_data
            logger.info(f"Updated new width to: {app_state.new_width}")
        else:
            app_state.new_width = None
            logger.info("New width cleared (set to None)")
    except (ValueError, TypeError):
        app_state.new_width = None
        logger.warning(f"Invalid width value: {app_data}")

def update_image_table():
    if not dpg.does_item_exist("image_table"):
        with dpg.table(header_row=True, policy=dpg.mvTable_SizingStretchProp,
                       borders_innerH=True, borders_outerH=True, borders_innerV=True,
                       borders_outerV=True, tag="image_table", parent="step_4_group"):
            # Add table columns with white text for header
            for label in ["Image", "Sharpness Score", "Badges"]:
                dpg.add_table_column(label=label)
                with dpg.theme() as header_theme:
                    with dpg.theme_component(dpg.mvTableColumn):
                        dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
                dpg.bind_item_theme(dpg.last_item(), header_theme)
    else:
        dpg.delete_item("image_table", children_only=True)
    
    for frame in app_state.extracted_frames:
        with dpg.table_row(parent="image_table"):
            dpg.add_text(frame.relative_path)
            dpg.add_text(f"{frame.blurriness_score:.2f}")
            dpg.add_text(", ".join(frame.badges) if frame.badges else "")

def update_batch_size(sender, app_data, user_data):
    app_state.batch_size = app_data
    logger.info(f"Updated batch size to: {app_state.batch_size}")

def update_min_images(sender, app_data, user_data):
    app_state.min_images = app_data
    logger.info(f"Updated minimum images to: {app_state.min_images}")

def update_max_images(sender, app_data, user_data):
    app_state.max_images = app_data
    logger.info(f"Updated maximum images to: {app_state.max_images}")

def select_best_images(sender, app_data, user_data):
    if not app_state.extracted_frames:
        status_msg = "Please extract frames first."
        dpg.set_value("best_images_status", status_msg)
        logger.warning(status_msg)
        return

    logger.info("Analyzing best images...")
    best_image_paths = analyze_best_images(
        app_state.extracted_frames,
        batch_size=app_state.batch_size,
        threshold=app_state.threshold,
        min_images=app_state.min_images,
        max_images=app_state.max_images
    )
    best_output_dir = os.path.join(app_state.project_folder, BEST_IMAGES_DIR)
    os.makedirs(best_output_dir, exist_ok=True)

    logger.info(f"Copying best images to: {best_output_dir}")
    for path in best_image_paths:
        src_path = os.path.join(app_state.project_folder, SOURCE_IMAGES_DIR, path)
        dst_path = os.path.join(best_output_dir, os.path.basename(path))
        shutil.copy2(src_path, dst_path)

    # Update imageData with 'Best' badge for selected images
    for frame in app_state.extracted_frames:
        if frame.relative_path in best_image_paths:
            frame.badges = frame.badges + ['Best'] if hasattr(frame, 'badges') else ['Best']

    status_msg = f"Copied {len(best_image_paths)} best images to:\n{wrap_text(best_output_dir)}"
    dpg.set_value("best_images_status", status_msg)
    logger.info(status_msg)
    logger.info(f"You can find the best images in:\n{wrap_text(os.path.abspath(best_output_dir))}")

    # Update the image table after all processing is done
    update_image_table()
    dpg.configure_item("next_button_4", enabled=True)

def update_results_table():
    dpg.delete_item("results_table", children_only=True)
    for frame in app_state.extracted_frames:
        with dpg.table_row(parent="results_table"):
            dpg.add_text(frame.relative_path)
            dpg.add_text(f"{frame.blurriness_score:.2f}")
            dpg.add_text(", ".join(frame.badges) if frame.badges else "")

def calculate_statistics():
    blurriness_scores = [frame.blurriness_score for frame in app_state.extracted_frames]
    best_images = [frame for frame in app_state.extracted_frames if 'Best' in frame.badges]
    
    stats = {
        "total_frames": len(app_state.extracted_frames),
        "best_images": len(best_images),
        "avg_blurriness": statistics.mean(blurriness_scores),
        "min_blurriness": min(blurriness_scores),
        "max_blurriness": max(blurriness_scores)
    }
    return stats

def update_results():
    update_results_table()
    stats = calculate_statistics()
    
    stats_text = (
        f"Total frames extracted: {stats['total_frames']}\n"
        f"Best images selected: {stats['best_images']}\n"
        f"Average blurriness score: {stats['avg_blurriness']:.2f}\n"
        f"Min blurriness score: {stats['min_blurriness']:.2f}\n"
        f"Max blurriness score: {stats['max_blurriness']:.2f}\n"
        f"\nProject folder:\n{wrap_text(app_state.project_folder)}\n"
        f"\nSource images directory:\n{wrap_text(os.path.join(app_state.project_folder, SOURCE_IMAGES_DIR))}\n"
        f"\nBest images directory:\n{wrap_text(os.path.join(app_state.project_folder, BEST_IMAGES_DIR))}"
    )
    dpg.set_value("results_stats", stats_text)

    # Add the new button for Reality Capture alignment
    if not dpg.does_item_exist("reality_capture_button"):
        dpg.add_button(
            label="Align images with Reality Capture",
            callback=run_reality_capture_alignment,
            width=BUTTON_WIDTH,
            parent="step_5_group"
        )
        dpg.add_text("", tag="reality_capture_status", wrap=550, parent="step_5_group")
        dpg.bind_item_font(dpg.last_item(), italic_font)

def run_reality_capture_alignment():
    try:
        # Define paths
        parent_dir = app_state.project_folder
        project_file = os.path.join(parent_dir, "rc_project.rcproj")
        images_folder = os.path.join(parent_dir, BEST_IMAGES_DIR)
        export_folder = os.path.join(parent_dir, "RC_Export")
        sparse_point_cloud_file = os.path.join(export_folder, "sparsePointCloud.ply")

        # Print debug information
        logger.info(f"Parent directory: {parent_dir}")
        logger.info(f"Project file: {project_file}")
        logger.info(f"Images folder: {images_folder}")
        logger.info(f"Export folder: {export_folder}")

        # Ensure export folder exists
        os.makedirs(export_folder, exist_ok=True)

        # Check if RealityCapture executable exists
        if not os.path.exists(RC_EXECUTABLE):
            raise FileNotFoundError(f"RealityCapture.exe not found at path: {RC_EXECUTABLE}")

        # Check if images folder exists and contains images
        if not os.path.exists(images_folder):
            raise FileNotFoundError(f"Images folder not found: {images_folder}")

        images = [f for f in os.listdir(images_folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not images:
            raise ValueError(f"No images found in folder: {images_folder}")

        logger.info(f"Found {len(images)} images in folder: {images_folder}")
        logger.info(f"First few images: {images[:5]}")

        # Construct RealityCapture command
        rc_command = [
            RC_EXECUTABLE,
            "-newScene",
            "-addFolder", images_folder,  # Remove quotes around the path
            "-align",
            "-save", project_file,  # Remove quotes around the path
            "-exportSparsePointCloud", sparse_point_cloud_file,  # Remove quotes around the path
            "-exportRegistration", os.path.join(export_folder, "camera_params.csv"),  # Remove quotes around the path
        ]

        # Print the command for debugging
        logger.info(f"RealityCapture command: {' '.join(rc_command)}")

        # Run RealityCapture command using Popen
        logger.info("Launching RealityCapture CLI to align images, save project, and export sparse point cloud and camera parameters...")
        process = subprocess.Popen(rc_command)
        
        # Wait for the process to complete
        process.wait()

        # Check if the process completed successfully
        if process.returncode == 0:
            logger.info("Reality Capture alignment completed successfully")
            
            # Move crmeta.db file
            crmeta_src = os.path.join(images_folder, "crmeta.db")
            crmeta_dst = os.path.join(export_folder, "crmeta.db")
            
            if os.path.exists(crmeta_src):
                shutil.move(crmeta_src, crmeta_dst)
                logger.info(f"Moved crmeta.db from {crmeta_src} to {crmeta_dst}")
                status_msg = (
                    "Alignment completed successfully!\n"
                    f"Project saved to: {project_file}\n"
                    f"Exports saved to: {export_folder}\n"
                    f"crmeta.db moved to: {crmeta_dst}"
                )
            else:
                logger.warning(f"crmeta.db not found in {images_folder}")
                status_msg = (
                    "Alignment completed successfully!\n"
                    f"Project saved to: {project_file}\n"
                    f"Exports saved to: {export_folder}\n"
                    "Note: crmeta.db was not found in the best images folder."
                )
        else:
            logger.error("Reality Capture alignment failed")
            status_msg = "Reality Capture alignment failed. Check the logs for more information."

        dpg.set_value("reality_capture_status", status_msg)

    except FileNotFoundError as e:
        error_msg = f"Error: {str(e)}"
        logger.error(error_msg)
        dpg.set_value("reality_capture_status", error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        dpg.set_value("reality_capture_status", error_msg)

def open_darktable():
    def run_darktable():
        try:
            best_images_dir = os.path.join(app_state.project_folder, BEST_IMAGES_DIR)
            
            # Check if Darktable executable exists
            if not os.path.exists(DARKTABLE_EXECUTABLE):
                raise FileNotFoundError(f"Darktable.exe not found at path: {DARKTABLE_EXECUTABLE}")

            # Check if best images directory exists and contains images
            if not os.path.exists(best_images_dir):
                raise FileNotFoundError(f"Best images directory not found: {best_images_dir}")

            images = [f for f in os.listdir(best_images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if not images:
                raise ValueError(f"No images found in directory: {best_images_dir}")

            logger.info(f"Found {len(images)} images in directory: {best_images_dir}")

            # Construct Darktable command
            darktable_command = [DARKTABLE_EXECUTABLE, best_images_dir]

            # Print the command for debugging
            logger.info(f"Darktable command: {' '.join(darktable_command)}")

            # Run Darktable command using Popen
            logger.info("Launching Darktable with best images directory...")
            subprocess.Popen(darktable_command)

            logger.info("Darktable opened successfully")
        except FileNotFoundError as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            dpg.set_value("darktable_status", error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            dpg.set_value("darktable_status", error_msg)

    # Run the Darktable command in a separate thread
    threading.Thread(target=run_darktable).start()

def advance_to_next_step():
    if app_state.current_step == 0:
        create_project_folder()
    if app_state.current_step < 6:
        app_state.current_step += 1
        update_window_visibility()
        if app_state.current_step == 6:
            update_results()
        elif app_state.current_step == 3:
            # Automatically start extraction when reaching step 4
            extract_frames_callback()
        elif app_state.current_step == 1:
            select_video(None, None, None)
        elif app_state.current_step == 2:
            dpg.focus_item("new_width_input")

# Update the create_step_3_group function to remove the "Start Extraction" button
def create_step_3_group():
    with dpg.group(tag="step_3_group", show=False):
        create_step_title(4, "Extract Frames", "step_3_group")
        dpg.add_text("Status:", tag="extract_status", wrap=550)
        dpg.bind_item_font(dpg.last_item(), italic_font)
        
        # Add a progress indicator (hidden by default)
        with dpg.group(horizontal=True, tag="extraction_progress", show=False):
            dpg.add_loading_indicator()
            
        dpg.add_button(
            label="Next",
            callback=lambda: advance_to_next_step(),
            width=BUTTON_WIDTH,
            enabled=False,
            tag="next_button_3"
        )

def update_window_visibility():
    for i in range(0, 7):
        if dpg.does_item_exist(f"step_{i}_group"):
            dpg.configure_item(f"step_{i}_group", show=(i == app_state.current_step))

def create_step_title(step_num: int, title: str, parent: str) -> None:
    """Create a consistently styled step title"""
    with dpg.group(horizontal=True, parent=parent):
        # Step number in blue
        dpg.add_text(f"Step {step_num}:", color=(52, 140, 215))
        dpg.bind_item_font(dpg.last_item(), bold_font)
        # Title text
        dpg.add_text(title)
        dpg.bind_item_font(dpg.last_item(), bold_font)
    dpg.add_spacer(height=8, parent=parent)

def run_gui():
    dpg.create_context()

    setup_font()
    setup_theme()

    # Add key handler for the entire window
    with dpg.handler_registry():
        dpg.add_key_press_handler(dpg.mvKey_Return, callback=lambda: confirm_project_name())

    with dpg.window(label="Video Frame Extractor", width=600, height=400, pos=(10, 10), tag="main_window"):
        # Step 1: Name Project
        with dpg.group(tag="step_0_group"):
            create_step_title(1, "Name Your Project", "step_0_group")
            
            project_name_input = dpg.add_input_text(
                label="Project Name", 
                callback=update_project_name,
                width=INPUT_WIDTH,
                tag="project_name_input"
            )
            
            dpg.add_button(
                label="Next", 
                callback=confirm_project_name,
                width=BUTTON_WIDTH, 
                enabled=False, 
                tag="next_button_0"
            )

        # Step 2: Select Video
        with dpg.group(tag="step_1_group", show=False):
            create_step_title(2, "Select Video and Output", "step_1_group")
            dpg.add_button(label="Select Video", callback=select_video, width=BUTTON_WIDTH)
            dpg.add_text("", tag="selected_video", wrap=550)
            dpg.bind_item_font(dpg.last_item(), italic_font)
            dpg.add_button(label="Next", callback=lambda: advance_to_next_step(), width=BUTTON_WIDTH, enabled=False, tag="next_button_1")

        # Step 3: Video Settings
        with dpg.group(tag="step_2_group", show=False):
            create_step_title(3, "Video Info and Settings", "step_2_group")
            dpg.add_text("Video Info:", tag="video_info", wrap=550)
            dpg.bind_item_font(dpg.last_item(), light_font)
            dpg.add_input_int(
                label="Frames per Second", 
                default_value=DEFAULT_FPS, 
                callback=update_fps, 
                tag="fps_input", 
                width=INPUT_WIDTH
            )
            dpg.add_input_int(  # Changed to input_int for better validation
                label="New Width (optional)", 
                callback=update_new_width,
                tag="new_width_input", 
                width=INPUT_WIDTH,
                default_value=0  # 0 means no resizing
            )
            dpg.add_button(
                label="Apply Settings & Continue", 
                callback=lambda: advance_to_next_step(),
                width=BUTTON_WIDTH, 
                tag="next_button_2"
            )

        # Step 4: Extract Frames
        create_step_3_group()

        # Step 5: Select Best Images
        with dpg.group(tag="step_4_group", show=False):
            create_step_title(5, "Select Best Images", "step_4_group")
            dpg.add_input_int(label="Batch Size", default_value=app_state.batch_size, callback=update_batch_size, width=INPUT_WIDTH)
            dpg.add_input_int(label="Minimum Images", default_value=app_state.min_images, callback=update_min_images, width=INPUT_WIDTH)
            dpg.add_input_int(label="Maximum Images", default_value=app_state.max_images, callback=update_max_images, width=INPUT_WIDTH)
            dpg.add_button(label="Select Best Images", callback=select_best_images, width=BUTTON_WIDTH)
            dpg.add_text("Status:", tag="best_images_status", wrap=550)
            dpg.bind_item_font(dpg.last_item(), italic_font)
            dpg.add_button(label="Next", callback=lambda: advance_to_next_step(), width=BUTTON_WIDTH, enabled=False, tag="next_button_4")

        # Step 6: Results
        with dpg.group(tag="step_5_group", show=False):
            create_step_title(6, "Results", "step_5_group")
            dpg.add_text("Statistics:", color=(10, 10, 10))
            dpg.bind_item_font(dpg.last_item(), bold_font)
            dpg.add_text("", tag="results_stats", wrap=550)
            dpg.bind_item_font(dpg.last_item(), light_font)

            dpg.add_button(
                label="Align images",
                callback=run_reality_capture_alignment,
                width=BUTTON_WIDTH
            )
            dpg.add_text("", tag="reality_capture_status", wrap=550)
            dpg.bind_item_font(dpg.last_item(), italic_font)

            dpg.add_button(
                label="Open in Darktable",
                callback=open_darktable,
                width=BUTTON_WIDTH
            )
            dpg.add_text("", tag="darktable_status", wrap=550)
            dpg.bind_item_font(dpg.last_item(), italic_font)

    dpg.create_viewport(title="Video Frame Extractor", width=620, height=440)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    dpg.set_primary_window("main_window", True)
    
    # Set focus to the project name input field
    dpg.focus_item(project_name_input)
    
    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


def main():
    # Check if FFmpeg is installed
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("Error: FFmpeg is not installed or not in the system PATH.")
        logger.error("Please install FFmpeg and make sure it's accessible from the command line.")
        return

    run_gui()

if __name__ == "__main__":
    main()
