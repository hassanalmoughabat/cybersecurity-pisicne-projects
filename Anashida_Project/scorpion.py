import os
import sys
import time
import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def get_human_readable_time(timestamp):
    """Convert timestamp to human-readable time"""
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def get_exif_data(image):
    """Extract EXIF data from image"""
    exif_data = {}
    try:
        if hasattr(image, '_getexif'):
            exif_info = image._getexif()
            if exif_info:
                for tag, value in exif_info.items():
                    decoded = TAGS.get(tag, tag)
                    if decoded == "GPSInfo":
                        gps_data = {}
                        for gps_tag in value:
                            gps_decoded = GPSTAGS.get(gps_tag, gps_tag)
                            gps_data[gps_decoded] = value[gps_tag]
                        exif_data[decoded] = gps_data
                    else:
                        exif_data[decoded] = value
    except Exception as e:
        print(f"Error getting EXIF data: {str(e)}")
    return exif_data

def get_basic_info(file_path):
    try:
        stat_info = os.stat(file_path)
        basic_info = {
            "File Name": os.path.basename(file_path),
            "File Size": f"{stat_info.st_size / 1024:.2f} KB",
            "Created": get_human_readable_time(stat_info.st_ctime),
            "Modified": get_human_readable_time(stat_info.st_mtime),
            "Accessed": get_human_readable_time(stat_info.st_atime),
        }
        return basic_info
    except Exception as e:
        print(f"Error getting basic info: {str(e)}")
        return {}

def process_image(file_path):
    """Process a single image file and extract metadata"""
    print(f"\n{'=' * 50}")
    print(f"IMAGE METADATA: {file_path}")
    print(f"{'=' * 50}")
    
    basic_info = get_basic_info(file_path)
    if basic_info:
        print("\nBASIC INFORMATION:")
        print("-" * 20)
        for key, value in basic_info.items():
            print(f"{key}: {value}")
    
    try:
        with Image.open(file_path) as img:
            print("\nIMAGE PROPERTIES:")
            print("-" * 20)
            print(f"Format: {img.format}")
            print(f"Mode: {img.mode}")
            print(f"Dimensions: {img.width} x {img.height} pixels")
            
            exif_data = get_exif_data(img)
            if exif_data:
                print("\nEXIF DATA:")
                print("-" * 20)
                for key, value in exif_data.items():
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='replace')
                        except:
                            value = str(value)
                    elif key == 'GPSInfo':
                        print(f"{key}:")
                        for gps_key, gps_value in value.items():
                            print(f"  {gps_key}: {gps_value}")
                        continue
                    
                    print(f"{key}: {value}")
            else:
                print("\nNo EXIF data found")
                
    except Exception as e:
        print(f"Error processing image: {str(e)}")

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} FILE1 [FILE2 ...]")
        sys.exit(1)
    
    file_paths = sys.argv[1:]
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    for file_path in file_paths:
        if not os.path.exists(file_path):
            print(f"Error: File not found - {file_path}")
            continue
            
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in valid_extensions:
            print(f"Warning: {file_path} is not a supported image format")
            continue
            
        process_image(file_path)

if __name__ == "__main__":
    main()