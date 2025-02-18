import os
import yt_dlp
import sys
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from PIL import Image
from colorama import Fore, Style, init
import re

init(autoreset=True)

def convert_youtube_music_url(youtube_url):
    """Converts YouTube Music playlist links to regular YouTube links."""
    if "music.youtube.com/playlist" in youtube_url:
        youtube_url = re.sub(r"music\.youtube\.com", "www.youtube.com", youtube_url)
        print(Fore.YELLOW + f"Converted YouTube Music link to: {youtube_url}" + Style.RESET_ALL)
    return youtube_url

def download_mp3(youtube_url, output_folder="downloads"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    youtube_url = convert_youtube_music_url(youtube_url)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'writethumbnail': True,
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        'quiet': True,
        'noplaylist': False  
    }

    print(Fore.CYAN + "Starting download..." + Style.RESET_ALL)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(youtube_url, download=True)
        except yt_dlp.utils.DownloadError as e:
            print(Fore.RED + f"Error: {clean_error_message(str(e))}" + Style.RESET_ALL)
            print(Fore.YELLOW + "Continuing with available downloads..." + Style.RESET_ALL)
            return process_existing_files(output_folder)

        if 'entries' in info:  # If it's a playlist
            for entry in info['entries']:
                if not entry or entry.get('url') is None:
                    print(Fore.YELLOW + f"Skipping unavailable video: {entry.get('title', 'Unknown Video')}" + Style.RESET_ALL)
                    continue
                
                title = entry.get('title', 'audio')
                mp3_path = os.path.join(output_folder, f"{title}.mp3")
                thumbnail_path = find_thumbnail(output_folder, title)

                if thumbnail_path:
                    embed_thumbnail(mp3_path, thumbnail_path)

            cleanup_thumbnails(output_folder)

        else:  # Single video case
            title = info.get('title', 'audio')
            mp3_path = os.path.join(output_folder, f"{title}.mp3")
            thumbnail_path = find_thumbnail(output_folder, title)

            if thumbnail_path:
                embed_thumbnail(mp3_path, thumbnail_path)
                cleanup_thumbnails(output_folder)

    print(Fore.GREEN + "Download complete!" + Style.RESET_ALL)

def clean_error_message(error_text):
    """Extracts a readable error message from yt-dlp's output."""
    if "Private video" in error_text:
        return "This video is private. Sign in to access it."
    if "Video unavailable" in error_text:
        return "This video is unavailable."
    if "Incomplete data received" in error_text:
        return "YouTube did not provide complete data. Retrying failed."
    return error_text.split('\n')[0]  

def process_existing_files(output_folder):
    """If errors occur, still embed album covers in already downloaded MP3s."""
    print(Fore.YELLOW + "Processing existing MP3s and thumbnails..." + Style.RESET_ALL)

    for file in os.listdir(output_folder):
        if file.endswith(".mp3"):
            title = os.path.splitext(file)[0]
            mp3_path = os.path.join(output_folder, file)
            thumbnail_path = find_thumbnail(output_folder, title)

            if thumbnail_path:
                embed_thumbnail(mp3_path, thumbnail_path)

    cleanup_thumbnails(output_folder)
    print(Fore.GREEN + "Processing complete!" + Style.RESET_ALL)

def find_thumbnail(output_folder, title):
    """Finds the correct thumbnail for each MP3 file."""
    for ext in ('jpg', 'jpeg', 'png', 'webp'):
        path = os.path.join(output_folder, f"{title}.{ext}")
        if os.path.exists(path):
            if ext == 'webp':  
                converted_path = path.replace('.webp', '.jpg')
                Image.open(path).convert("RGB").save(converted_path, "JPEG")
                return converted_path
            return path
    return None  # If no image is found

def embed_thumbnail(mp3_path, thumbnail_path):
    """Embeds the specific thumbnail into its matching MP3 file."""
    print(Fore.MAGENTA + f"Embedding thumbnail into {mp3_path}..." + Style.RESET_ALL)
    try:
        audio = MP3(mp3_path, ID3=ID3)
    except error:
        audio = MP3(mp3_path)
        audio.add_tags()
    
    if audio.tags is None:
        audio.add_tags()
    
    with open(thumbnail_path, 'rb') as img:
        audio.tags.add(
            APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=img.read()
            )
        )
    
    audio.save(v2_version=3)
    print(Fore.GREEN + "Thumbnail embedded!" + Style.RESET_ALL)

def cleanup_thumbnails(output_folder):
    """Deletes all remaining thumbnail images."""
    deleted_anything = False
    for ext in ('jpg', 'jpeg', 'png', 'webp'):
        for file in os.listdir(output_folder):
            if file.endswith(f".{ext}"):
                path = os.path.join(output_folder, file)
                os.remove(path)
                deleted_anything = True
                print(Fore.RED + f"Deleted: {path}" + Style.RESET_ALL)

    if not deleted_anything:
        print(Fore.YELLOW + "No leftover thumbnails found to delete." + Style.RESET_ALL)

if __name__ == "__main__":
    url = input(Fore.BLUE + "Enter YouTube video or playlist URL: " + Style.RESET_ALL)
    download_mp3(url)
