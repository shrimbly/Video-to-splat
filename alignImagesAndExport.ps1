# Define variables for paths and settings
$projectFile = "C:\Users\Admin\Documents\Splats\RC\Automation tests\test.rcproj"  # Path to save the project
$imagesFolder = "C:\Users\Admin\Documents\Splats\RC\Automation tests\images"       # Path to the folder containing the images
$exportFolder = "C:\Users\Admin\Documents\Splats\RC\Automation tests\output"      # Path to export the output files
$sparsePointCloudFile = "$exportFolder\sparsePointCloud.ply"                     # File for sparse point cloud export

# Check if RealityCapture executable exists
if (-not (Test-Path "C:\Program Files\Capturing Reality\RealityCapture\RealityCapture.exe")) {
    Write-Host "RealityCapture.exe not found at specified path"
    exit
}

Write-Host "Checking if images folder exists..."

# Check if images folder exists
if (-not (Test-Path $imagesFolder)) {
    Write-Host "Images folder not found: $imagesFolder"
    exit
}

# Check if the images folder contains images
$images = Get-ChildItem -Path $imagesFolder -Filter *.jpg
if ($images.Count -eq 0) {
    Write-Host "No images found in folder: $imagesFolder"
    exit
} else {
    Write-Host "Found $($images.Count) images in folder: $imagesFolder"
}

Write-Host "Launching RealityCapture CLI to align images, save project, and export sparse point cloud and camera parameters..."

# Simplified execution with all steps in one process
Start-Process -FilePath "C:\Program Files\Capturing Reality\RealityCapture\RealityCapture.exe" -ArgumentList @(
    "-newScene",                      # Create a new project
    "-addFolder", "`"$imagesFolder`"", # Add images folder
    "-align",                          # Align the images
    "-save", "`"$projectFile`"",       # Save the project after alignment
    "-exportSparsePointCloud", "`"$sparsePointCloudFile`"",  # Export the sparse point cloud
    "-exportRegistration", "`"$exportFolder\camera_params.csv`""  # Export camera parameters
    exit
) 
Write-Host "Donezo"