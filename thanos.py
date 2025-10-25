import os
import re
import time
import mmap
import datetime
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import tgcrypto
import subprocess
import concurrent.futures
from math import ceil
from utils import progress_bar
from pyrogram import Client, filters
from pyrogram.types import Message
from io import BytesIO
from pathlib import Path  
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
import math
import m3u8
from urllib.parse import urljoin
from vars import *  # Add this import
from db import Database



def get_duration(filename):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    return float(result.stdout)

def split_large_video(file_path, max_size_mb=1900):
    size_bytes = os.path.getsize(file_path)
    max_bytes = max_size_mb * 1024 * 1024

    if size_bytes <= max_bytes:
        return [file_path]  # No splitting needed

    duration = get_duration(file_path)
    parts = ceil(size_bytes / max_bytes)
    part_duration = duration / parts
    base_name = file_path.rsplit(".", 1)[0]
    output_files = []

    for i in range(parts):
        output_file = f"{base_name}_part{i+1}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-i", file_path,
            "-ss", str(int(part_duration * i)),
            "-t", str(int(part_duration)),
            "-c", "copy",
            output_file
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(output_file):
            output_files.append(output_file)

    return output_files


def duration(filename):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)


def get_mps_and_keys(api_url):
    response = requests.get(api_url)
    response_json = response.json()
    mpd = response_json.get('mpd_url')
    keys = response_json.get('keys')
    return mpd, keys


   
def exec(cmd):
        process = subprocess.run(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        output = process.stdout.decode()
        print(output)
        return output
        #err = process.stdout.decode()
def pull_run(work, cmds):
    with concurrent.futures.ThreadPoolExecutor(max_workers=work) as executor:
        print("Waiting for tasks to complete")
        fut = executor.map(exec,cmds)
async def aio(url,name):
    k = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(k, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return k


async def download(url,name):
    ka = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(ka, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return ka

async def pdf_download(url, file_name, chunk_size=1024 * 10):
    if os.path.exists(file_name):
        os.remove(file_name)
    r = requests.get(url, allow_redirects=True, stream=True)
    with open(file_name, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
    return file_name   
   

def parse_vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = []
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ",2)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info.append((i[0], i[2]))
            except:
                pass
    return new_info


def vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = dict()
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ",3)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    
                    # temp.update(f'{i[2]}')
                    # new_info.append((i[2], i[0]))
                    #  mp4,mkv etc ==== f"({i[1]})" 
                    
                    new_info.update({f'{i[2]}':f'{i[0]}'})

            except:
                pass
    return new_info


async def decrypt_and_merge_video(mpd_url, keys_string, output_path, output_name, quality="720"):
    try:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        cmd1 = f'yt-dlp -f "bv[height<={quality}]+ba/b" -o "{output_path}/file.%(ext)s" --allow-unplayable-format --no-check-certificate --external-downloader aria2c "{mpd_url}"'
        print(f"Running command: {cmd1}")
        os.system(cmd1)
        
        avDir = list(output_path.iterdir())
        print(f"Downloaded files: {avDir}")
        print("Decrypting")

        video_decrypted = False
        audio_decrypted = False

        for data in avDir:
            if data.suffix == ".mp4" and not video_decrypted:
                cmd2 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/video.mp4"'
                print(f"Running command: {cmd2}")
                os.system(cmd2)
                if (output_path / "video.mp4").exists():
                    video_decrypted = True
                data.unlink()
            elif data.suffix == ".m4a" and not audio_decrypted:
                cmd3 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/audio.m4a"'
                print(f"Running command: {cmd3}")
                os.system(cmd3)
                if (output_path / "audio.m4a").exists():
                    audio_decrypted = True
                data.unlink()

        if not video_decrypted or not audio_decrypted:
            raise FileNotFoundError("Decryption failed: video or audio file not found.")

        cmd4 = f'ffmpeg -i "{output_path}/video.mp4" -i "{output_path}/audio.m4a" -c copy "{output_path}/{output_name}.mp4"'
        print(f"Running command: {cmd4}")
        os.system(cmd4)
        if (output_path / "video.mp4").exists():
            (output_path / "video.mp4").unlink()
        if (output_path / "audio.m4a").exists():
            (output_path / "audio.m4a").unlink()
        
        filename = output_path / f"{output_name}.mp4"

        if not filename.exists():
            raise FileNotFoundError("Merged video file not found.")

        cmd5 = f'ffmpeg -i "{filename}" 2>&1 | grep "Duration"'
        duration_info = os.popen(cmd5).read()
        print(f"Duration info: {duration_info}")

        return str(filename)

    except Exception as e:
        print(f"Error during decryption and merging: {str(e)}")
        raise

async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if proc.returncode == 1:
        return False
    if stdout:
        return f'[stdout]\n{stdout.decode()}'
    if stderr:
        return f'[stderr]\n{stderr.decode()}'

    

def old_download(url, file_name, chunk_size = 1024 * 10 * 10):
    if os.path.exists(file_name):
        os.remove(file_name)
    r = requests.get(url, allow_redirects=True, stream=True)
    with open(file_name, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
    return file_name


def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.strftime("%H%M%S")
    return f"{date} {current_time}.mp4"


async def fast_download(url, name):
    """Fast direct download implementation without yt-dlp"""
    max_retries = 5
    retry_count = 0
    success = False
    
    while not success and retry_count < max_retries:
        try:
            if "m3u8" in url:
                # Handle m3u8 files
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        m3u8_text = await response.text()
                        
                    playlist = m3u8.loads(m3u8_text)
                    if playlist.is_endlist:
                        # Direct download of segments
                        base_url = url.rsplit('/', 1)[0] + '/'
                        
                        # Download all segments concurrently
                        segments = []
                        async with aiohttp.ClientSession() as session:
                            tasks = []
                            for segment in playlist.segments:
                                segment_url = urljoin(base_url, segment.uri)
                                task = asyncio.create_task(session.get(segment_url))
                                tasks.append(task)
                            
                            responses = await asyncio.gather(*tasks)
                            for response in responses:
                                segment_data = await response.read()
                                segments.append(segment_data)
                        
                        # Merge segments and save
                        output_file = f"{name}.mp4"
                        with open(output_file, 'wb') as f:
                            for segment in segments:
                                f.write(segment)
                        
                        success = True
                        return [output_file]
                    else:
                        # For live streams, fall back to ffmpeg
                        cmd = f'ffmpeg -hide_banner -loglevel error -stats -i "{url}" -c copy -bsf:a aac_adtstoasc -movflags +faststart "{name}.mp4"'
                        subprocess.run(cmd, shell=True)
                        if os.path.exists(f"{name}.mp4"):
                            success = True
                            return [f"{name}.mp4"]
            else:
                # For direct video URLs
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            output_file = f"{name}.mp4"
                            with open(output_file, 'wb') as f:
                                while True:
                                    chunk = await response.content.read(1024*1024)  # 1MB chunks
                                    if not chunk:
                                        break
                                    f.write(chunk)
                            success = True
                            return [output_file]
            
            if not success:
                print(f"\nAttempt {retry_count + 1} failed, retrying in 3 seconds...")
                retry_count += 1
                await asyncio.sleep(3)
                
        except Exception as e:
            print(f"\nError during attempt {retry_count + 1}: {str(e)}")
            retry_count += 1
            await asyncio.sleep(3)
    
    return None

async def download_video(url, cmd, name):
    retry_count = 0
    max_retries = 2

    while retry_count < max_retries:


        download_cmd = f'{cmd} -R 25 --fragment-retries 25 --external-downloader aria2c --downloader-args "aria2c: -x 16 -j 32"'
        print(download_cmd)
        logging.info(download_cmd)

        k = subprocess.run(download_cmd, shell=True)

        if k.returncode == 0:
            break  # success

        retry_count += 1
        print(f"⚠️ Download failed (attempt {retry_count}/{max_retries}), retrying in 5s...")
        await asyncio.sleep(5)

    try:
        if os.path.isfile(name):
            return name
        elif os.path.isfile(f"{name}.webm"):
            return f"{name}.webm"
        name = name.split(".")[0]
        if os.path.isfile(f"{name}.mkv"):
            return f"{name}.mkv"
        elif os.path.isfile(f"{name}.mp4"):
            return f"{name}.mp4"
        elif os.path.isfile(f"{name}.mp4.webm"):
            return f"{name}.mp4.webm"

        return name + ".mp4"
    except Exception as exc:
        logging.error(f"Error checking file: {exc}")
        return name 





async def send_vid(bot: Client, m: Message, cc, filename, thumb, name, prog, channel_id, watermark="Thanos", topic_thread_id: int = None):
    try:
        temp_thumb = None  # ✅ Ensure this is always defined for later cleanup

        thumbnail = thumb
        if thumb in ["/d", "no"] or not os.path.exists(thumb):
            temp_thumb = f"downloads/thumb_{os.path.basename(filename)}.jpg"
            
            # Generate thumbnail at 10s
            subprocess.run(
                f'ffmpeg -i "{filename}" -ss 00:00:10 -vframes 1 -q:v 2 -y "{temp_thumb}"',
                shell=True
            )

            # ✅ Only apply watermark if watermark != "/d"
            if os.path.exists(temp_thumb) and (watermark and watermark.strip() != "/d"):
                text_to_draw = watermark.strip()
                try:
                    # Probe image width for better scaling
                    probe_out = subprocess.check_output(
                        f'ffprobe -v error -select_streams v:0 -show_entries stream=width -of csv=p=0:s=x "{temp_thumb}"',
                        shell=True,
                        stderr=subprocess.DEVNULL,
                    ).decode().strip()
                    img_width = int(probe_out.split('x')[0]) if 'x' in probe_out else int(probe_out)
                except Exception:
                    img_width = 1280

                # Base size relative to width, then adjust by text length
                base_size = max(28, int(img_width * 0.075))
                text_len = len(text_to_draw)
                if text_len <= 3:
                    font_size = int(base_size * 1.25)
                elif text_len <= 8:
                    font_size = int(base_size * 1.0)
                elif text_len <= 15:
                    font_size = int(base_size * 0.85)
                else:
                    font_size = int(base_size * 0.7)
                font_size = max(32, min(font_size, 120))

                box_h = max(60, int(font_size * 1.6))

                # Simple escaping for single quotes in text
                safe_text = text_to_draw.replace("'", "\\'")

                text_cmd = (
                    f'ffmpeg -i "{temp_thumb}" -vf '
                    f'"drawbox=y=0:color=black@0.35:width=iw:height={box_h}:t=fill,'
                    f'drawtext=fontfile=font.ttf:text=\'{safe_text}\':fontcolor=white:'
                    f'fontsize={font_size}:x=(w-text_w)/2:y=(({box_h})-text_h)/2" '
                    f'-c:v mjpeg -q:v 2 -y "{temp_thumb}"'
                )
                subprocess.run(text_cmd, shell=True)
            
            thumbnail = temp_thumb if os.path.exists(temp_thumb) else None

        await prog.delete(True)  # ⏳ Remove previous progress message

        reply1 = await bot.send_message(channel_id, f" **Uploading Video:**\n<blockquote>{name}</blockquote>")
        reply = await m.reply_text(f"🖼 **Generating Thumbnail:**\n<blockquote>{name}</blockquote>")

        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        notify_split = None
        sent_message = None

        if file_size_mb < 2000:
            # 📹 Upload as single video
            dur = int(duration(filename))
            start_time = time.time()

            try:
                sent_message = await bot.send_video(
                    chat_id=channel_id,
                    video=filename,
                    caption=cc,
                    supports_streaming=True,
                    height=720,
                    width=1280,
                    thumb=thumbnail,
                    duration=dur,
                    progress=progress_bar,
                    progress_args=(reply, start_time)
                )
            except Exception:
                sent_message = await bot.send_document(
                    chat_id=channel_id,
                    document=filename,
                    caption=cc,
                    progress=progress_bar,
                    progress_args=(reply, start_time)
                )

            # ✅ Cleanup
            if os.path.exists(filename):
                os.remove(filename)
            await reply.delete(True)
            await reply1.delete(True)

        else:
            # ⚠️ Notify about splitting
            notify_split = await m.reply_text(
                f"⚠️ The video is larger than 2GB ({human_readable_size(os.path.getsize(filename))})\n"
                f"⏳ Splitting into parts before upload..."
            )

            parts = split_large_video(filename)

            try:
                first_part_message = None
                for idx, part in enumerate(parts):
                    part_dur = int(duration(part))
                    part_num = idx + 1
                    total_parts = len(parts)
                    part_caption = f"{cc}\n\n📦 Part {part_num} of {total_parts}"
                    part_filename = f"{name}_Part{part_num}.mp4"

                    upload_msg = await m.reply_text(f"📤 Uploading Part {part_num}/{total_parts}...")

                    try:
                        msg_obj = await bot.send_video(
                            chat_id=channel_id,
                            video=part,
                            caption=part_caption,
                            file_name=part_filename,
                            supports_streaming=True,
                            height=720,
                            width=1280,
                            thumb=thumbnail,
                            duration=part_dur,
                            progress=progress_bar,
                            progress_args=(upload_msg, time.time())
                        )
                        if first_part_message is None:
                            first_part_message = msg_obj
                    except Exception:
                        msg_obj = await bot.send_document(
                            chat_id=channel_id,
                            document=part,
                            caption=part_caption,
                            file_name=part_filename,
                            progress=progress_bar,
                            progress_args=(upload_msg, time.time())
                        )
                        if first_part_message is None:
                            first_part_message = msg_obj

                    await upload_msg.delete(True)
                    if os.path.exists(part):
                        os.remove(part)

            except Exception as e:
                raise Exception(f"Upload failed at part {idx + 1}: {str(e)}")

            # ✅ Final messages
            if len(parts) > 1:
                await m.reply_text("✅ Large video successfully uploaded in multiple parts!")

            # Cleanup after split
            await reply.delete(True)
            await reply1.delete(True)
            if notify_split:
                await notify_split.delete(True)
            if os.path.exists(filename):
                os.remove(filename)

            # Return first sent part message
            sent_message = first_part_message

        # 🧹 Cleanup generated thumbnail if applicable
        if thumb in ["/d", "no"] and temp_thumb and os.path.exists(temp_thumb):
            os.remove(temp_thumb)

        return sent_message

    except Exception as err:
        raise Exception(f"send_vid failed: {err}")
