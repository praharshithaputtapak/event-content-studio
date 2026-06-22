import os
import json
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont, ImageOps


VIDEO_FORMATS = {
    "feed_4_5": {"size": (1080, 1350), "dar": "4/5"},
    "reel_9_16": {"size": (1080, 1920), "dar": "9/16"},
}
DEFAULT_VIDEO_FORMAT = "feed_4_5"
VIDEO_SIZE = VIDEO_FORMATS[DEFAULT_VIDEO_FORMAT]["size"]
VIDEO_WIDTH, VIDEO_HEIGHT = VIDEO_SIZE


def _set_video_format(format_key):
    global VIDEO_SIZE, VIDEO_WIDTH, VIDEO_HEIGHT
    config = VIDEO_FORMATS.get(format_key, VIDEO_FORMATS[DEFAULT_VIDEO_FORMAT])
    VIDEO_SIZE = config["size"]
    VIDEO_WIDTH, VIDEO_HEIGHT = VIDEO_SIZE
    return config


def _ffmpeg_path():
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg is required to generate MP4 reels. Install FFmpeg and make sure it is available on PATH.")
    return path


def verify_ffmpeg_installation():
    ffmpeg = _ffmpeg_path()
    try:
        subprocess.run(
            [ffmpeg, "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError("FFmpeg was found, but it could not be started. Reinstall FFmpeg or check your PATH.") from error
    return ffmpeg


def _ffprobe_path():
    path = shutil.which("ffprobe")
    return path or ""


def _font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width):
    words = str(text or "").split()
    lines = []
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def _center_text(draw, y, text, font, fill, max_width=620, line_gap=8):
    lines = _wrap_text(draw, text, font, max_width)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        width = bbox[2] - bbox[0]
        draw.text(((VIDEO_SIZE[0] - width) / 2, y), line, font=font, fill=fill)
        y += bbox[3] - bbox[1] + line_gap
    return y


def _event_date(data):
    start_date = str(data.get("start_date") or "").strip()
    end_date = str(data.get("end_date") or "").strip()
    if end_date and end_date != start_date:
        return f"{start_date} to {end_date}"
    return start_date


def _fit_image(path, size):
    image = Image.open(path).convert("RGB")
    return ImageOps.contain(image, size)


def _paste_center(canvas, image, y=None):
    x = (VIDEO_WIDTH - image.width) // 2
    if y is None:
        y = (VIDEO_HEIGHT - image.height) // 2
    canvas.paste(image, (x, y))


def _make_title_slide(path, logo_path, event_name, organization_name):
    canvas = Image.new("RGB", VIDEO_SIZE, "#f8fafc")
    draw = ImageDraw.Draw(canvas)
    band = max(18, int(VIDEO_HEIGHT * 0.016))
    card_top = int(VIDEO_HEIGHT * 0.11)
    card_bottom = int(VIDEO_HEIGHT * 0.86)
    draw.rectangle((0, 0, VIDEO_WIDTH, band), fill="#0f172a")
    draw.rectangle((0, VIDEO_HEIGHT - band, VIDEO_WIDTH, VIDEO_HEIGHT), fill="#2563eb")
    draw.rounded_rectangle((80, card_top, VIDEO_WIDTH - 80, card_bottom), radius=34, fill="#ffffff", outline="#d1d5db", width=3)
    if logo_path and os.path.exists(logo_path):
        logo_size = min(300, int(VIDEO_HEIGHT * 0.2))
        logo = _fit_image(logo_path, (logo_size, logo_size))
        _paste_center(canvas, logo, card_top + int(VIDEO_HEIGHT * 0.08))
    org_y = card_top + int(VIDEO_HEIGHT * 0.36)
    title_y = org_y + int(VIDEO_HEIGHT * 0.09)
    y = _center_text(draw, org_y, organization_name, _font(42), "#475569", max_width=820, line_gap=12)
    _center_text(draw, max(title_y, y + 28), event_name, _font(68, bold=True), "#0f172a", max_width=850, line_gap=14)
    canvas.save(path, "JPEG", quality=95)


def _make_photo_slide(path, image_path, overlay_lines):
    canvas = Image.new("RGB", VIDEO_SIZE, "#0f172a")
    image_top = int(VIDEO_HEIGHT * 0.045)
    image_height = int(VIDEO_HEIGHT * 0.74)
    image = _fit_image(image_path, (VIDEO_WIDTH - 72, image_height))
    _paste_center(canvas, image, image_top + max(0, (image_height - image.height) // 2))
    draw = ImageDraw.Draw(canvas)
    footer_top = image_top + image_height + int(VIDEO_HEIGHT * 0.035)
    draw.rounded_rectangle((56, footer_top, VIDEO_WIDTH - 56, VIDEO_HEIGHT - 58), radius=28, fill="#ffffff")
    y = footer_top + 32
    for line in overlay_lines:
        if line:
            font_size = 38 if line == "Event Highlights" else 34
            y = _center_text(draw, y, line, _font(font_size, bold=True), "#111827", max_width=880, line_gap=7)
    canvas.save(path, "JPEG", quality=95)


def _contact_line(data):
    values = [
        data.get("contact_person"),
        data.get("contact_email"),
        data.get("contact_number"),
    ]
    return " | ".join(str(value).strip() for value in values if str(value or "").strip())


def _make_thank_you_slide(path, logo_path, organization_name, contact_info=""):
    canvas = Image.new("RGB", VIDEO_SIZE, "#ffffff")
    draw = ImageDraw.Draw(canvas)
    band = max(18, int(VIDEO_HEIGHT * 0.016))
    card_top = int(VIDEO_HEIGHT * 0.13)
    card_bottom = int(VIDEO_HEIGHT * 0.84)
    draw.rectangle((0, 0, VIDEO_WIDTH, band), fill="#2563eb")
    draw.rectangle((0, VIDEO_HEIGHT - band, VIDEO_WIDTH, VIDEO_HEIGHT), fill="#0f172a")
    draw.rounded_rectangle((90, card_top, VIDEO_WIDTH - 90, card_bottom), radius=34, fill="#f8fafc", outline="#d1d5db", width=3)
    if logo_path and os.path.exists(logo_path):
        logo_size = min(280, int(VIDEO_HEIGHT * 0.2))
        logo = _fit_image(logo_path, (logo_size, logo_size))
        _paste_center(canvas, logo, card_top + int(VIDEO_HEIGHT * 0.13))
    thanks_y = card_top + int(VIDEO_HEIGHT * 0.39)
    _center_text(draw, thanks_y, "Thank You", _font(84, bold=True), "#111827", max_width=860)
    y = _center_text(draw, thanks_y + int(VIDEO_HEIGHT * 0.105), organization_name, _font(44), "#475569", max_width=820)
    if contact_info:
        _center_text(draw, y + 42, contact_info, _font(31), "#475569", max_width=850)
    canvas.save(path, "JPEG", quality=95)


def _run_ffmpeg(args):
    try:
        subprocess.run(args, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        stdout = (error.stdout or "").strip()
        detail = stderr or stdout or str(error)
        raise RuntimeError(f"FFmpeg failed: {detail[-1200:]}") from error


def _media_duration(path):
    ffprobe = _ffprobe_path()
    if not ffprobe:
        return 0
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip() or 0)
    except (subprocess.CalledProcessError, ValueError):
        return 0


def _probe_mp4(path):
    ffprobe = _ffprobe_path()
    if not ffprobe or not os.path.exists(path):
        return {}
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration,size:stream=codec_type,codec_name,width,height",
                "-of",
                "json",
                path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout or "{}")
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}


def _has_audio_stream(path):
    streams = _probe_mp4(path).get("streams", [])
    return any(stream.get("codec_type") == "audio" for stream in streams)


def validate_generated_mp4(path, min_duration=1.0):
    if not os.path.exists(path):
        raise RuntimeError("MP4 generation did not create an output file.")
    if os.path.getsize(path) < 50000:
        raise RuntimeError("Generated MP4 is too small to be a valid playable video.")
    if not _ffprobe_path():
        raise RuntimeError("FFprobe is required to validate generated MP4 files. Install FFmpeg with FFprobe on PATH.")

    probe = _probe_mp4(path)
    streams = probe.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    duration = float((probe.get("format") or {}).get("duration") or 0)

    if duration < min_duration:
        raise RuntimeError("Generated MP4 has an invalid or missing duration.")
    if video_stream.get("codec_name") != "h264":
        raise RuntimeError("Generated MP4 is missing an H.264 video stream.")
    if audio_stream.get("codec_name") != "aac":
        raise RuntimeError("Generated MP4 is missing an AAC audio stream.")
    if int(video_stream.get("width") or 0) != VIDEO_WIDTH or int(video_stream.get("height") or 0) != VIDEO_HEIGHT:
        raise RuntimeError("Generated MP4 dimensions do not match the selected reel format.")

    return {
        "duration": duration,
        "size": int((probe.get("format") or {}).get("size") or os.path.getsize(path)),
        "width": VIDEO_WIDTH,
        "height": VIDEO_HEIGHT,
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": audio_stream.get("codec_name"),
    }


def _drawtext_escape(value):
    return str(value or "").replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def _drawtext_fontfile():
    for candidate in ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/calibrib.ttf"]:
        if os.path.exists(candidate):
            return candidate.replace(":", "\\:")
    return ""


def _display_aspect():
    for config in VIDEO_FORMATS.values():
        if config["size"] == VIDEO_SIZE:
            return config["dar"]
    return VIDEO_FORMATS[DEFAULT_VIDEO_FORMAT]["dar"]


def _video_overlay_filters(data):
    fontfile = _drawtext_fontfile()
    if not fontfile:
        return ""
    event_name = _drawtext_escape(data.get("event_name", "Event Highlights"))
    organization_name = _drawtext_escape(data.get("organization_name", ""))
    box_height = max(150, int(VIDEO_HEIGHT * 0.13))
    title_y = VIDEO_HEIGHT - box_height + 30
    org_y = VIDEO_HEIGHT - box_height + 92
    organization_filter = ""
    if organization_name:
        organization_filter = (
            f",drawtext=fontfile='{fontfile}':text='{organization_name}':"
            f"x=(w-text_w)/2:y={org_y}:fontsize=32:fontcolor=white:shadowcolor=black@0.55:shadowx=2:shadowy=2"
        )
    return (
        f"drawbox=x=0:y=h-{box_height}:w=w:h={box_height}:color=black@0.42:t=fill,"
        f"drawtext=fontfile='{fontfile}':text='{event_name}':"
        f"x=(w-text_w)/2:y={title_y}:fontsize=44:fontcolor=white:shadowcolor=black@0.6:shadowx=2:shadowy=2"
        f"{organization_filter},"
    )


def _image_to_segment(ffmpeg, image_path, output_path, duration=3.5):
    fade_out_start = max(duration - 0.35, 0)
    frame_count = max(int(duration * 30), 1)
    _run_ffmpeg(
        [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-i",
            image_path,
            "-f",
            "lavfi",
            "-t",
            str(duration),
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t",
            str(duration),
            "-vf",
            (
                f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
                f"zoompan=z='min(zoom+0.0008,1.06)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frame_count}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps=30,"
                f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start}:d=0.35,"
                f"setsar=1,setdar={_display_aspect()},format=yuv420p"
            ),
            "-r",
            "30",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-level",
            "4.0",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]
    )


def _video_to_segment(ffmpeg, video_path, output_path, data):
    duration = _media_duration(video_path)
    has_audio = _has_audio_stream(video_path)
    fade_filters = "fade=t=in:st=0:d=0.35,"
    if duration > 0.7:
        fade_filters += f"fade=t=out:st={max(duration - 0.35, 0)}:d=0.35,"
    overlay_filters = _video_overlay_filters(data)
    base_filter = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps=30,{fade_filters}setsar=1,setdar={_display_aspect()},"
    )
    args = [
        ffmpeg,
        "-y",
        "-i",
        video_path,
    ]
    if not has_audio:
        args.extend(
            [
                "-f",
                "lavfi",
                "-t",
                str(duration if duration > 0 else 3.5),
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=44100",
            ]
        )
    args.extend(
        [
        "-vf",
        f"{base_filter}{overlay_filters}format=yuv420p",
        "-map",
        "0:v:0",
        "-map",
        "0:a:0" if has_audio else "1:a:0",
        "-c:v",
        "libx264",
        "-profile:v",
        "main",
        "-level",
        "4.0",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        output_path,
        ]
    )
    try:
        _run_ffmpeg(args)
    except RuntimeError:
        if not overlay_filters:
            raise
        vf_index = args.index("-vf") + 1
        args[vf_index] = f"{base_filter}format=yuv420p"
        _run_ffmpeg(args)


def generate_reel_mp4(data, output_path, logo_path="", photo_paths=None, video_paths=None, format_key=DEFAULT_VIDEO_FORMAT):
    _set_video_format(format_key or DEFAULT_VIDEO_FORMAT)
    ffmpeg = verify_ffmpeg_installation()
    photo_paths = [path for path in (photo_paths or []) if os.path.exists(path)]
    video_paths = [path for path in (video_paths or []) if os.path.exists(path)]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="event_reel_") as temp_dir:
        title_slide = os.path.join(temp_dir, "title.jpg")
        thanks_slide = os.path.join(temp_dir, "thanks.jpg")
        _make_title_slide(title_slide, logo_path, data.get("event_name", "Event"), data.get("organization_name", ""))
        _make_thank_you_slide(thanks_slide, logo_path, data.get("organization_name", ""), _contact_line(data))

        overlay_lines = [
            "Event Highlights",
            data.get("event_name", ""),
            _event_date(data),
            data.get("location", ""),
        ]
        slide_paths = []
        for index, photo_path in enumerate(photo_paths, start=1):
            slide_path = os.path.join(temp_dir, f"photo_{index}.jpg")
            _make_photo_slide(slide_path, photo_path, overlay_lines)
            slide_paths.append(slide_path)

        segments = []
        title_segment = os.path.join(temp_dir, "slide_title.mp4")
        _image_to_segment(ffmpeg, title_slide, title_segment, duration=3.0)
        segments.append(title_segment)

        max_media_count = max(len(slide_paths), len(video_paths))
        for index in range(max_media_count):
            if index < len(slide_paths):
                segment = os.path.join(temp_dir, f"photo_{index + 1}.mp4")
                _image_to_segment(ffmpeg, slide_paths[index], segment, duration=3.5)
                segments.append(segment)
            if index < len(video_paths):
                segment = os.path.join(temp_dir, f"video_{index + 1}.mp4")
                _video_to_segment(ffmpeg, video_paths[index], segment, data)
                segments.append(segment)

        thanks_segment = os.path.join(temp_dir, "slide_closing.mp4")
        _image_to_segment(ffmpeg, thanks_slide, thanks_segment, duration=3.0)
        segments.append(thanks_segment)

        concat_path = os.path.join(temp_dir, "concat.txt")
        with open(concat_path, "w", encoding="utf-8") as file:
            for segment in segments:
                file.write(f"file '{segment.replace('\\', '/')}'\n")

        _run_ffmpeg(
            [
                ffmpeg,
                "-y",
                "-fflags",
                "+genpts",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_path,
                "-map",
                "0:v:0",
                "-map",
                "0:a:0",
                "-vf",
                "scale=in_range=pc:out_range=tv,format=yuv420p",
                "-c:v",
                "libx264",
                "-profile:v",
                "main",
                "-level",
                "4.0",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-pix_fmt",
                "yuv420p",
                "-color_range",
                "tv",
                "-movflags",
                "+faststart",
                "-avoid_negative_ts",
                "make_zero",
                output_path,
            ]
        )

    validate_generated_mp4(output_path)
    return output_path
