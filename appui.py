import base64
import hashlib
import colorsys
import json
import logging
import os
import secrets
import shutil
import stat
from datetime import date, datetime, timedelta

import streamlit as st

from content_generator import (
    build_caption,
    build_brochure_preview_html,
    build_flyer_preview_html,
    build_report_preview_html,
    create_project_folder,
    generate_brochure_pdf,
    generate_flyer_pdf,
    generate_report_pdf,
)
from video_generator import generate_reel_mp4, validate_generated_mp4, verify_ffmpeg_installation


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

OUTPUTS_DIR = "outputs"
ASSETS_DIR = "assets"
PROJECTS_DIR = "generated_projects"
USERS_FILE = "users.json"
APP_PAGES = {"auth", "welcome", "content_creation", "history", "output"}
REMEMBER_DAYS = 30
DEFAULT_THEME = {
    "theme_mode": "Light",
    "background_color": "#FFFFFF",
    "text_color": "#111827",
    "button_color": "#2563EB",
}
DEFAULT_OUTPUTS = ["Flyer", "Brochure", "Report", "Caption", "Reel Content"]
REEL_FORMAT_OPTIONS = {
    "Instagram Feed Video (4:5)": "feed_4_5",
    "Instagram Reel / Shorts (9:16)": "reel_9_16",
}
DEFAULT_REEL_FORMAT_LABEL = "Instagram Feed Video (4:5)"


logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


st.set_page_config(page_title="Event Content Studio", layout="wide")


def init_state():
    defaults = {
        "page": "welcome",
        "generated_data": {},
        "current_project_folder": "",
        "theme_mode": "Light",
        "theme_background_color": DEFAULT_THEME["background_color"],
        "theme_text_color": DEFAULT_THEME["text_color"],
        "theme_button_color": DEFAULT_THEME["button_color"],
        "theme_preferences_loaded": False,
        "last_saved_theme": {},
        "current_user": {},
        "edit_project_path": "",
        "edit_project_data": {},
        "navigation_initialized": False,
        "output_success_message": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def query_page_value():
    try:
        page = st.query_params.get("page", "")
    except Exception:
        return ""
    if isinstance(page, list):
        page = page[0] if page else ""
    return page if page in APP_PAGES else ""


def sync_page_from_query():
    page = query_page_value()
    if page and page != "auth":
        st.session_state.page = page
    elif not st.session_state.navigation_initialized:
        st.query_params["page"] = st.session_state.page
    st.session_state.navigation_initialized = True


def navigate_to(page, rerun=True):
    if page not in APP_PAGES:
        page = "welcome"
    current_page = st.session_state.get("page")
    current_query_page = query_page_value()
    if page == current_page and (page == "auth" or current_query_page == page):
        return
    st.session_state.page = page
    if page == "auth":
        st.query_params.clear()
    else:
        st.query_params["page"] = page
    if rerun:
        st.rerun()


def ensure_base_folders():
    for folder in [
        OUTPUTS_DIR,
        os.path.join(ASSETS_DIR, "photos"),
        os.path.join(ASSETS_DIR, "videos"),
        os.path.join(ASSETS_DIR, "documents"),
        os.path.join(ASSETS_DIR, "logos"),
        os.path.join(ASSETS_DIR, "sponsors"),
        PROJECTS_DIR,
    ]:
        os.makedirs(folder, exist_ok=True)


def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file, indent=4)


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return salt, digest


def hash_token(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def query_param_value(name):
    try:
        value = st.query_params.get(name, "")
    except Exception:
        return ""
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "")


def current_user():
    return st.session_state.get("current_user") or {}


def current_user_email():
    return current_user().get("email", "")


def current_user_id():
    return current_user().get("user_id", "")


def is_logged_in():
    return bool(current_user_email())


def user_project_matches(data):
    owner_id = data.get("owner_user_id")
    owner_email = data.get("owner_email")
    return bool(owner_id and owner_id == current_user_id()) or bool(owner_email and owner_email == current_user_email())


def find_user_by_email(users, email):
    normalized = str(email or "").strip().lower()
    for user in users:
        if user.get("email", "").lower() == normalized:
            return user
    return None


def set_current_user(user):
    st.session_state.current_user = {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"],
    }
    load_user_preferences(user)


def user_preferences(user):
    preferences = user.get("preferences")
    return preferences if isinstance(preferences, dict) else {}


def load_user_preferences(user):
    preferences = user_preferences(user)
    theme = preferences.get("theme", {})
    if not isinstance(theme, dict):
        theme = {}
    saved_mode = theme.get("mode", DEFAULT_THEME["theme_mode"])
    st.session_state.theme_mode = saved_mode if saved_mode in ["Light", "Dark"] else DEFAULT_THEME["theme_mode"]
    if st.session_state.theme_mode == "Dark":
        st.session_state.theme_background_color = "#0B1220"
        st.session_state.theme_text_color = "#F8FAFC"
        st.session_state.theme_button_color = "#38BDF8"
    else:
        st.session_state.theme_background_color = DEFAULT_THEME["background_color"]
        st.session_state.theme_text_color = DEFAULT_THEME["text_color"]
        st.session_state.theme_button_color = DEFAULT_THEME["button_color"]
    st.session_state.last_saved_theme = {
        "mode": st.session_state.theme_mode,
        "background_color": st.session_state.theme_background_color,
        "text_color": st.session_state.theme_text_color,
        "button_color": st.session_state.theme_button_color,
    }
    st.session_state.last_expected_output = [
        item for item in preferences.get("last_expected_output", DEFAULT_OUTPUTS) if item in DEFAULT_OUTPUTS
    ] or DEFAULT_OUTPUTS
    st.session_state.theme_preferences_loaded = True
    st.session_state.reset_theme_widgets = True


def update_current_user_preferences(updates):
    if not is_logged_in():
        return
    users = load_users()
    changed = False
    for user in users:
        if user.get("user_id") == current_user_id():
            preferences = user.get("preferences")
            if not isinstance(preferences, dict):
                preferences = {}
            for key, value in updates.items():
                if preferences.get(key) != value:
                    preferences[key] = value
                    changed = True
            user["preferences"] = preferences
            break
    if changed:
        save_users(users)


def save_theme_preferences(mode, background_color, text_color, button_color):
    update_current_user_preferences(
        {
            "theme": {
                "mode": mode,
                "background_color": background_color,
                "text_color": text_color,
                "button_color": button_color,
            }
        }
    )


def save_last_expected_output(expected_output):
    update_current_user_preferences({"last_expected_output": expected_output})


def create_remember_token(user_id):
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(days=REMEMBER_DAYS)).isoformat(timespec="seconds")
    users = load_users()
    for user in users:
        if user.get("user_id") == user_id:
            user["remember_token_hash"] = hash_token(token)
            user["remember_token_expires_at"] = expires_at
            break
    save_users(users)
    return token


def clear_remember_token(user_id):
    if not user_id:
        return
    users = load_users()
    changed = False
    for user in users:
        if user.get("user_id") == user_id:
            if user.pop("remember_token_hash", None) is not None:
                changed = True
            if user.pop("remember_token_expires_at", None) is not None:
                changed = True
            break
    if changed:
        save_users(users)


def restore_remembered_login():
    if is_logged_in():
        return
    token = query_param_value("remember_token")
    if not token:
        return
    users = load_users()
    token_hash = hash_token(token)
    now = datetime.now()
    for user in users:
        if user.get("remember_token_hash") != token_hash:
            continue
        try:
            expires_at = datetime.fromisoformat(user.get("remember_token_expires_at", ""))
        except ValueError:
            expires_at = now - timedelta(seconds=1)
        if expires_at <= now:
            clear_remember_token(user.get("user_id"))
            st.query_params.clear()
            return
        set_current_user(user)
        return


def render_auth_page():
    st.markdown(
        """
        <section class="studio-hero studio-page">
          <div class="studio-eyebrow">Secure Workspace</div>
          <h1>Event Content Studio</h1>
          <p>Login or create an account to keep your event projects, media, generated PDFs, and MP4 reels private.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("login-form"):
            email = st.text_input("Email", key="login-email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", key="login-password", placeholder="Enter your password")
            remember_me = st.checkbox("Remember Me", key="login-remember-me")
            submitted = st.form_submit_button("Login")
        if submitted:
            users = load_users()
            user = find_user_by_email(users, email)
            if not user:
                st.error("No account found for this email.")
                return
            _, digest = hash_password(password, user.get("salt"))
            if digest != user.get("password_hash"):
                st.error("Incorrect password.")
                return
            set_current_user(user)
            if remember_me:
                st.query_params["remember_token"] = create_remember_token(user["user_id"])
            else:
                clear_remember_token(user["user_id"])
            navigate_to("welcome")

    with register_tab:
        with st.form("register-form"):
            name = st.text_input("Name", key="register-name", placeholder="Your full name")
            email = st.text_input("Email", key="register-email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", key="register-password", placeholder="Create a password")
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="register-confirm-password",
                placeholder="Re-enter your password",
            )
            submitted = st.form_submit_button("Create Account")
        if submitted:
            if not name.strip() or not email.strip() or not password:
                st.error("Please enter name, email, and password.")
                return
            if password != confirm_password:
                st.error("Passwords do not match.")
                return
            users = load_users()
            if find_user_by_email(users, email):
                st.error("An account with this email already exists.")
                return
            salt, digest = hash_password(password)
            user = {
                "user_id": secrets.token_hex(12),
                "name": name.strip(),
                "email": email.strip().lower(),
                "salt": salt,
                "password_hash": digest,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            users.append(user)
            save_users(users)
            set_current_user(user)
            navigate_to("welcome")


def render_account_controls():
    if not is_logged_in():
        return
    page_labels = {
        "welcome": "Dashboard",
        "content_creation": "Create Project",
        "history": "Project History",
        "output": "Generated Outputs",
    }
    st.markdown(
        f"""
        <nav class="studio-nav">
          <div>
            <div class="studio-nav-brand">Event Content Studio</div>
            <div class="studio-nav-meta">{page_labels.get(st.session_state.page, "Dashboard")}</div>
          </div>
          <div class="studio-nav-meta">Signed in as {current_user().get("name", "User")}</div>
        </nav>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
          <div class="sidebar-logo">ECS</div>
          <div>
            <div class="sidebar-app-name">Event Content Studio</div>
            <div class="sidebar-user">{current_user().get("name", "User")}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown('<div class="sidebar-label">Workspace</div>', unsafe_allow_html=True)
    if st.sidebar.button("[D] Dashboard", key="nav-dashboard", type="primary" if st.session_state.page == "welcome" else "secondary"):
        navigate_to("welcome", rerun=False)
    if st.sidebar.button(
        "+ Create Project",
        key="nav-create",
        type="primary" if st.session_state.page == "content_creation" else "secondary",
    ):
        st.session_state.edit_project_path = ""
        st.session_state.edit_project_data = {}
        navigate_to("content_creation", rerun=False)
    if st.sidebar.button("[H] History", key="nav-history", type="primary" if st.session_state.page == "history" else "secondary"):
        navigate_to("history", rerun=False)
    if st.sidebar.button("[S] Settings", key="nav-settings"):
        st.sidebar.info("Theme preferences are saved automatically.")
    st.sidebar.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
    st.sidebar.caption(f"Signed in as {current_user().get('email')}")
    if st.sidebar.button("[X] Logout", key="nav-logout"):
        clear_remember_token(current_user_id())
        st.session_state.current_user = {}
        st.session_state.generated_data = {}
        st.session_state.current_project_folder = ""
        st.session_state.edit_project_path = ""
        st.session_state.edit_project_data = {}
        st.session_state.theme_preferences_loaded = False
        navigate_to("auth")


def read_project_data(project_path):
    data_path = os.path.join(project_path, "event_data.json")
    if not os.path.exists(data_path):
        return {}
    with open(data_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    data["project_folder"] = data.get("project_folder") or project_path
    return data


def list_user_projects():
    if not os.path.exists(PROJECTS_DIR) or not is_logged_in():
        return []

    projects = []
    for name in os.listdir(PROJECTS_DIR):
        project_path = os.path.join(PROJECTS_DIR, name)
        if not os.path.isdir(project_path):
            continue
        data = read_project_data(project_path)
        if data and user_project_matches(data):
            projects.append(name)
    projects.sort(reverse=True)
    return projects


def project_output_stats(project_names):
    stats = {
        "total": len(project_names),
        "flyers": 0,
        "reports": 0,
        "reels": 0,
    }
    for project in project_names:
        project_path = os.path.join(PROJECTS_DIR, project)
        if os.path.exists(os.path.join(project_path, "flyer.pdf")):
            stats["flyers"] += 1
        if os.path.exists(os.path.join(project_path, "report.pdf")):
            stats["reports"] += 1
        if os.path.exists(os.path.join(project_path, "reel_content.mp4")) or os.path.exists(
            os.path.join(project_path, "reel_video.mp4")
        ):
            stats["reels"] += 1
    return stats


def recent_project_cards(project_names, limit=3):
    cards = []
    for project in project_names[:limit]:
        project_path = os.path.join(PROJECTS_DIR, project)
        data = read_project_data(project_path)
        if not data:
            continue
        outputs = []
        if os.path.exists(os.path.join(project_path, "flyer.pdf")):
            outputs.append("Flyer")
        if os.path.exists(os.path.join(project_path, "brochure.pdf")):
            outputs.append("Brochure")
        if os.path.exists(os.path.join(project_path, "report.pdf")):
            outputs.append("Report")
        if os.path.exists(os.path.join(project_path, "reel_content.mp4")) or os.path.exists(
            os.path.join(project_path, "reel_video.mp4")
        ):
            outputs.append("Reel")
        cards.append(
            {
                "name": data.get("event_name", project),
                "date": data.get("start_date", data.get("project_timestamp", "")),
                "venue": data.get("location", ""),
                "outputs": ", ".join(outputs) if outputs else "Draft",
            }
        )
    return cards


def parse_date_value(value):
    if not value:
        return date.today()
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def parse_time_value(value):
    if not value:
        return None
    for fmt in ["%I:%M %p", "%H:%M:%S", "%H:%M"]:
        try:
            return datetime.strptime(str(value), fmt).time()
        except ValueError:
            continue
    return None


def form_time_value(value, fallback):
    return parse_time_value(value) or datetime.strptime(fallback, "%H:%M").time()


def save_uploaded_files(uploaded_files, folder, legacy_folder):
    names = []
    if not uploaded_files:
        return names

    os.makedirs(folder, exist_ok=True)
    os.makedirs(legacy_folder, exist_ok=True)

    for uploaded_file in uploaded_files:
        names.append(uploaded_file.name)
        data = uploaded_file.getbuffer()
        for target_folder in [folder, legacy_folder]:
            target_path = os.path.join(target_folder, uploaded_file.name)
            with open(target_path, "wb") as file:
                file.write(data)
            if not os.path.exists(target_path) or os.path.getsize(target_path) != len(data):
                raise IOError(f"Upload was not saved correctly: {target_path}")

    return names


def save_single_upload(uploaded_file, folder, legacy_folder):
    if not uploaded_file:
        return "", ""

    os.makedirs(folder, exist_ok=True)
    os.makedirs(legacy_folder, exist_ok=True)
    data = uploaded_file.getbuffer()

    project_path = os.path.join(folder, uploaded_file.name)
    for target_path in [project_path, os.path.join(legacy_folder, uploaded_file.name)]:
        with open(target_path, "wb") as file:
            file.write(data)
        if not os.path.exists(target_path) or os.path.getsize(target_path) != len(data):
            raise IOError(f"Upload was not saved correctly: {target_path}")

    return uploaded_file.name, project_path


def existing_media_paths(project_folder, media_folder, names):
    paths = []
    for name in names or []:
        path = os.path.abspath(os.path.join(project_folder, "assets", media_folder, name))
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            paths.append(path)
        else:
            logger.warning("Skipping missing or empty uploaded %s file: %s", media_folder, path)
    return paths


def file_bytes(path):
    with open(path, "rb") as file:
        return file.read()


def delete_project_folder(project_path):
    projects_root = os.path.abspath(PROJECTS_DIR)
    target_path = os.path.abspath(project_path)

    if os.path.commonpath([projects_root, target_path]) != projects_root:
        raise ValueError("Project path is outside the history folder.")

    def make_writable(path):
        try:
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
        except OSError:
            pass

    def retry_after_permission_error(function, path, exc_info):
        make_writable(path)
        function(path)

    if os.path.isdir(target_path):
        for root, dirs, files in os.walk(target_path):
            make_writable(root)
            for name in dirs + files:
                make_writable(os.path.join(root, name))

        try:
            shutil.rmtree(target_path, onexc=retry_after_permission_error)
        except TypeError:
            shutil.rmtree(target_path, onerror=retry_after_permission_error)


def image_data_uri(path):
    if not path or not os.path.exists(path):
        return ""

    extension = os.path.splitext(path)[1].lower().replace(".", "")
    mime = "jpeg" if extension in ["jpg", "jpeg"] else "png"
    encoded = base64.b64encode(file_bytes(path)).decode("utf-8")
    return f"data:image/{mime};base64,{encoded}"


def image_data_uris(paths):
    return [uri for uri in [image_data_uri(path) for path in paths] if uri]


def hex_to_rgb(hex_color):
    value = str(hex_color or "").strip().lstrip("#")
    if len(value) != 6:
        return (255, 255, 255)
    try:
        return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        return (255, 255, 255)


def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*[max(0, min(255, int(value))) for value in rgb])


def readable_text_color(background_color):
    red, green, blue = [value / 255 for value in hex_to_rgb(background_color)]
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#111827" if luminance > 0.56 else "#FFFFFF"


def contrast_ratio(first_color, second_color):
    def relative_luminance(hex_color):
        channels = []
        for value in hex_to_rgb(hex_color):
            channel = value / 255
            channels.append(channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    first = relative_luminance(first_color)
    second = relative_luminance(second_color)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def color_variant(hex_color, lightness_delta):
    red, green, blue = [value / 255 for value in hex_to_rgb(hex_color)]
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    lightness = max(0.06, min(0.94, lightness + lightness_delta))
    new_red, new_green, new_blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return rgb_to_hex((new_red * 255, new_green * 255, new_blue * 255))


def theme_palette(background_color, text_color, button_color):
    if contrast_ratio(background_color, text_color) < 4.5:
        text_color = readable_text_color(background_color)
    button_text = readable_text_color(button_color)
    card_color = color_variant(background_color, 0.08 if readable_text_color(background_color) == "#FFFFFF" else -0.04)
    panel_color = color_variant(background_color, 0.13 if readable_text_color(background_color) == "#FFFFFF" else -0.07)
    border_color = color_variant(text_color, 0.46 if readable_text_color(background_color) == "#111827" else -0.35)
    muted_color = color_variant(text_color, 0.24 if readable_text_color(background_color) == "#FFFFFF" else -0.25)
    button_hover = color_variant(button_color, -0.08 if button_text == "#FFFFFF" else 0.08)
    return {
        "background": background_color,
        "text": text_color,
        "button": button_color,
        "button_text": button_text,
        "button_hover": button_hover,
        "card": card_color,
        "panel": panel_color,
        "border": border_color,
        "muted": muted_color,
    }


def render_uploaded_media_preview(photos, videos, edit_data=None):
    edit_data = edit_data or {}
    existing_folder = edit_data.get("project_folder") or st.session_state.get("edit_project_path", "")
    existing_photo_paths = [
        os.path.join(existing_folder, "assets", "photos", name)
        for name in edit_data.get("photos", [])
        if existing_folder and os.path.exists(os.path.join(existing_folder, "assets", "photos", name))
    ]
    existing_video_paths = [
        os.path.join(existing_folder, "assets", "videos", name)
        for name in edit_data.get("videos", [])
        if existing_folder and os.path.exists(os.path.join(existing_folder, "assets", "videos", name))
    ]
    if not photos and not videos and not existing_photo_paths and not existing_video_paths:
        return

    st.subheader("Media Preview")
    if photos or existing_photo_paths:
        st.caption("Uploaded photos")
        preview_photos = list(existing_photo_paths) + list(photos or [])
        columns = st.columns(min(3, max(1, len(preview_photos))))
        for index, photo in enumerate(preview_photos):
            with columns[index % len(columns)]:
                st.image(photo, use_container_width=True)

    if videos or existing_video_paths:
        st.caption("Uploaded videos")
        for video in list(existing_video_paths) + list(videos or []):
            st.video(video)


def render_preview_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"], .stApp {
            font-family: 'Inter', Arial, sans-serif !important;
        }
        .block-container {
            padding-top: 1.45rem;
            padding-bottom: 3.5rem;
            max-width: 1220px;
        }
        .studio-card {
            border: 1px solid rgba(148, 163, 184, 0.35);
            border-radius: 8px;
            padding: 18px;
            background: rgba(255, 255, 255, 0.72);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }
        .metric-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin: 22px 0;
        }
        .metric-row .studio-card b {
            display: block;
            font-size: 26px;
            color: #2563eb !important;
        }
        .preview {
            font-family: Arial, sans-serif;
            border-radius: 8px;
            padding: 30px;
            color: #111827;
            background: #ffffff;
            border: 1px solid #d1d5db;
            max-width: 920px;
            margin: 0 auto;
        }
        .preview h1 {
            font-size: 34px;
            line-height: 1.15;
            margin: 6px 0 10px;
            color: #111827 !important;
        }
        .preview h2 {
            font-size: 18px;
            margin-top: 24px;
            color: #2563eb !important;
        }
        .preview p, .preview span, .preview b, .preview footer {
            color: #111827 !important;
        }
        .preview .eyebrow {
            text-transform: uppercase;
            letter-spacing: 0;
            font-size: 12px;
            color: #6b7280 !important;
            margin: 0;
        }
        .preview-header-block {
            text-align: center;
            margin-bottom: 14px;
        }
        .logo {
            width: 148px;
            height: 148px;
            object-fit: contain;
            display: block;
            margin: 0 auto 14px;
        }
        .preview-photo {
            width: 100%;
            max-height: 260px;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid #d1d5db;
            margin-top: 14px;
            margin-left: auto;
            margin-right: auto;
            display: block;
        }
        .photo-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
            margin: 12px 0 18px;
        }
        .photo-grid figure {
            margin: 0;
        }
        .grid-photo {
            width: 100%;
            height: 160px;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid #d1d5db;
        }
        .page-divider {
            border-top: 2px dashed #d1d5db;
            margin: 26px 0;
        }
        .banner {
            background: #eff6ff;
            border-left: 5px solid #2563eb;
            padding: 14px;
            margin: 18px 0;
            font-weight: 700;
            color: #1f2937 !important;
        }
        .detail-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 16px;
        }
        .detail-grid div {
            background: #f3f4f6;
            padding: 14px;
            border-radius: 8px;
        }
        .detail-grid b, .detail-grid span {
            display: block;
        }
        .flyer-preview {
            text-align: left;
            background: #ffffff;
            min-height: 880px;
            aspect-ratio: 210 / 297;
            padding: 28px;
            overflow: hidden;
            border: 8px solid #1d4ed8;
            max-width: 620px;
        }
        .flyer-preview .preview-header-block {
            margin-bottom: 12px;
            background: #f8fafc;
            border: 1px solid #1d4ed8;
            border-radius: 8px;
            padding: 14px 18px 12px;
        }
        .flyer-preview .logo {
            width: 160px;
            height: 160px;
            margin-bottom: 8px;
        }
        .flyer-preview h1 {
            font-size: 42px;
            line-height: 1.05;
            text-align: center;
            color: #1d4ed8 !important;
        }
        .flyer-preview h2 {
            margin-top: 12px;
            font-size: 15px;
            line-height: 1.2;
        }
        .flyer-preview ul {
            margin-top: 6px;
            padding-left: 18px;
        }
        .flyer-preview .detail-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
            margin-top: 10px;
        }
        .flyer-preview .detail-grid div {
            background: #fff7ed;
            border: 1px solid #f97316;
            padding: 10px;
        }
        .flyer-preview .detail-grid b {
            color: #1d4ed8 !important;
            font-size: 12px;
            text-transform: uppercase;
        }
        .flyer-preview .preview-photo {
            max-height: 215px;
            margin-top: 8px;
        }
        .report-preview .logo {
            width: 220px;
            height: 220px;
        }
        .report-preview h1 {
            color: #111111 !important;
        }
        .report-preview h2 {
            color: #333333 !important;
        }
        .report-preview .banner {
            background: #ffffff;
            border-left: 0;
            border-top: 1px solid #d1d5db;
            border-bottom: 1px solid #d1d5db;
            color: #222222 !important;
            text-align: center;
            font-weight: 600;
        }
        .brochure-preview .logo {
            width: 154px;
            height: 154px;
        }
        .flyer-lower-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-top: 14px;
        }
        .flyer-block {
            background: #f8fafc;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            padding: 12px 14px;
            min-height: 112px;
        }
        .flyer-block h2,
        .flyer-info-block h2 {
            margin-top: 0;
        }
        .flyer-bottom-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-top: 14px;
            border-top: 6px solid #1d4ed8;
            padding-top: 10px;
        }
        .flyer-bottom-grid.no-supporters {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .flyer-info-block {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 10px 12px;
            min-height: 92px;
        }
        .footer-organization {
            text-align: center;
        }
        .footer-logo {
            width: 72px;
            height: 72px;
            object-fit: contain;
            display: block;
            margin: 0 auto 6px;
        }
        .sponsor-strip {
            border-top: 0;
            margin-top: 0;
            padding-top: 0;
        }
        .sponsor-strip b {
            display: block;
            margin-bottom: 8px;
        }
        .sponsor-strip img {
            width: 38px;
            height: 26px;
            object-fit: contain;
            margin-right: 10px;
            vertical-align: middle;
        }
        .sponsor-logo {
            width: 50px;
            height: 34px;
            object-fit: contain;
            margin-right: 10px;
            vertical-align: middle;
        }
        @media (max-width: 760px) {
            .metric-row, .detail-grid, .flyer-columns, .photo-grid, .flyer-lower-grid, .flyer-bottom-grid {
                grid-template-columns: 1fr;
            }
            .preview, .flyer-preview {
                padding: 20px;
            }
        }
        .studio-hero {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 62%, #eff6ff 100%);
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            padding: 30px 34px;
            box-shadow: 0 16px 42px rgba(15, 23, 42, 0.08);
            margin-bottom: 24px;
        }
        .studio-hero h1 {
            color: #0f172a !important;
            font-size: 42px;
            line-height: 1.08;
            margin: 0 0 10px;
            letter-spacing: 0;
        }
        .studio-hero p {
            color: #475569 !important;
            max-width: 760px;
            font-size: 16px;
            line-height: 1.62;
            margin: 0;
        }
        .studio-eyebrow {
            color: #2563eb !important;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .studio-card {
            background: #ffffff;
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
        }
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 4px 18px;
            margin-bottom: 8px;
        }
        .sidebar-logo {
            width: 42px;
            height: 42px;
            border-radius: 8px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #2563eb, #0f766e);
            color: #ffffff !important;
            font-weight: 800;
            font-size: 13px;
            box-shadow: 0 12px 28px rgba(37, 99, 235, 0.28);
        }
        .sidebar-app-name {
            font-weight: 800;
            line-height: 1.1;
        }
        .sidebar-user,
        .sidebar-label {
            color: #64748b !important;
            font-size: 12px;
        }
        .sidebar-label {
            text-transform: uppercase;
            font-weight: 800;
            letter-spacing: 0;
            margin: 18px 0 8px;
        }
        .sidebar-spacer {
            height: 18px;
            border-top: 1px solid rgba(148, 163, 184, 0.28);
            margin-top: 16px;
        }
        [data-testid="stSidebar"] .stButton>button {
            width: 100%;
            justify-content: flex-start;
            box-shadow: none !important;
            margin-bottom: 6px;
        }
        [data-testid="stSidebar"] .stButton>button[kind="secondary"] {
            background: transparent !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            font-size: 12px;
        }
        .form-section {
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            padding: 20px;
            background: #ffffff;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
            margin-bottom: 18px;
            animation: studioFadeSlide 360ms ease-out both;
        }
        .form-section h3,
        .section-title {
            margin: 0 0 6px;
            font-size: 18px;
            font-weight: 800;
            letter-spacing: 0;
        }
        .section-kicker {
            margin: 0 0 16px;
            color: #64748b !important;
            font-size: 13px;
        }
        .output-shell {
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            background: #ffffff;
            padding: 18px;
            box-shadow: 0 12px 34px rgba(15, 23, 42, 0.07);
            margin-top: 14px;
        }
        .history-card {
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            padding: 16px;
            background: #ffffff;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
            margin-bottom: 12px;
        }
        .history-title {
            font-weight: 800;
            font-size: 17px;
            margin-bottom: 4px;
        }
        .history-meta {
            color: #64748b !important;
            font-size: 13px;
            margin-bottom: 10px;
        }
        .metric-row {
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 16px;
            margin: 20px 0 26px;
        }
        .metric-row .studio-card {
            min-height: 112px;
        }
        .metric-row .studio-card b {
            color: #1d4ed8 !important;
            font-size: 30px;
        }
        .workflow-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin: 22px 0;
        }
        .workflow-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
        }
        .workflow-card b {
            color: #0f172a !important;
            display: block;
            margin-bottom: 6px;
        }
        .workflow-card span {
            color: #64748b !important;
            font-size: 13px;
            line-height: 1.45;
        }
        .preview {
            font-family: Arial, sans-serif;
            border-radius: 8px;
            padding: 34px;
            border: 1px solid #dbe3ef;
            box-shadow: 0 12px 34px rgba(15, 23, 42, 0.08);
        }
        .preview h1 {
            letter-spacing: 0;
        }
        .preview h2 {
            color: #1d4ed8 !important;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 6px;
        }
        .preview-photo,
        .grid-photo {
            border-radius: 8px;
            object-fit: cover;
            background: #f8fafc;
        }
        .detail-grid div {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
        }
        .flyer-preview {
            border: 0;
            box-shadow: 0 18px 44px rgba(15, 23, 42, 0.16);
            background: #ffffff;
        }
        .flyer-preview::before {
            content: "";
            display: block;
            height: 10px;
            background: #1d4ed8;
            margin: -28px -28px 18px;
        }
        .brochure-preview .preview-photo {
            max-height: 320px;
        }
        .report-preview {
            box-shadow: none;
            border-color: #cbd5e1;
        }
        .report-preview h2 {
            color: #333333 !important;
            border-bottom-color: #d1d5db;
        }
        @media (max-width: 900px) {
            .workflow-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .studio-hero {
                padding: 26px;
            }
            .studio-hero h1 {
                font-size: 34px;
            }
        }
        @media (max-width: 640px) {
            .workflow-grid {
                grid-template-columns: 1fr;
            }
            .studio-hero h1 {
                font-size: 30px;
            }
        }
        @keyframes studioFadeSlide {
            from {
                opacity: 0;
                transform: translateY(14px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        @keyframes studioSoftFade {
            from {
                opacity: 0;
            }
            to {
                opacity: 1;
            }
        }
        .studio-page {
            animation: studioFadeSlide 420ms ease-out both;
        }
        .studio-section {
            animation: studioSoftFade 520ms ease-out both;
        }
        .studio-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 14px;
            padding: 12px 16px;
            margin-bottom: 18px;
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.86);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        }
        .studio-nav-brand {
            color: #0f172a !important;
            font-weight: 800;
        }
        .studio-nav-meta {
            color: #64748b !important;
            font-size: 13px;
        }
        .studio-card,
        .workflow-card,
        .output-card {
            transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
        }
        .studio-card:hover,
        .workflow-card:hover,
        .output-card:hover {
            transform: translateY(-2px);
            border-color: #bfdbfe;
            box-shadow: 0 16px 34px rgba(15, 23, 42, 0.10);
        }
        .stButton>button:hover,
        .stDownloadButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 12px 26px rgba(37, 99, 235, 0.24);
            filter: brightness(1.03);
        }
        .stButton>button,
        .stDownloadButton>button {
            transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease;
        }
        .stTextInput input:focus,
        .stTextArea textarea:focus,
        .stDateInput input:focus,
        .stTimeInput input:focus {
            border-color: #2563eb !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14) !important;
        }
        .stat-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            border-radius: 8px;
            background: #eff6ff;
            color: #1d4ed8 !important;
            font-weight: 800;
            margin-bottom: 12px;
        }
        .recent-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin: 12px 0 24px;
        }
        .recent-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            min-height: 132px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
        }
        .recent-card b {
            color: #0f172a !important;
            display: block;
            margin-bottom: 8px;
        }
        .recent-card span,
        .recent-card p {
            color: #64748b !important;
            font-size: 13px;
            margin: 3px 0;
        }
        .output-card {
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            background: #ffffff;
            padding: 16px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
        }
        div[data-baseweb="tab-list"] {
            gap: 8px;
        }
        button[data-baseweb="tab"] {
            border-radius: 8px !important;
            padding: 10px 16px !important;
            background: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: #eff6ff !important;
            border-color: #93c5fd !important;
            color: #1d4ed8 !important;
        }
        @media (max-width: 900px) {
            .metric-row {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .recent-grid {
                grid-template-columns: 1fr;
            }
            .studio-nav {
                align-items: flex-start;
                flex-direction: column;
            }
        }
        @media (max-width: 640px) {
            .metric-row {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_theme():
    if st.session_state.get("reset_theme_widgets"):
        for key in ["theme-mode-select"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.reset_theme_widgets = False

    theme_options = ["Light", "Dark"]
    saved_mode = st.session_state.get("theme_mode", DEFAULT_THEME["theme_mode"])
    theme_index = theme_options.index(saved_mode) if saved_mode in theme_options else 0
    st.sidebar.markdown('<div class="sidebar-label">Theme</div>', unsafe_allow_html=True)
    theme_mode = st.sidebar.radio("Mode", theme_options, index=theme_index, key="theme-mode-select", horizontal=True)

    background_color = "#FFFFFF"
    text_color = "#111827"
    button_color = "#2563EB"

    if theme_mode == "Dark":
        background_color = "#0B1220"
        text_color = "#F8FAFC"
        button_color = "#38BDF8"

    st.session_state.theme_mode = theme_mode
    st.session_state.theme_background_color = background_color
    st.session_state.theme_button_color = button_color
    palette = theme_palette(background_color, text_color, button_color)
    text_color = palette["text"]
    st.session_state.theme_text_color = text_color
    theme_payload = {
        "mode": theme_mode,
        "background_color": background_color,
        "text_color": text_color,
        "button_color": button_color,
    }
    if st.session_state.get("last_saved_theme") != theme_payload:
        save_theme_preferences(theme_mode, background_color, text_color, button_color)
        st.session_state.last_saved_theme = theme_payload

    render_preview_css()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {palette["background"]};
            color: {palette["text"]};
        }}
        .stApp, .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span,
        .stTextInput label, .stTextArea label, .stSelectbox label, .stMultiSelect label,
        .stDateInput label, .stTimeInput label, .stFileUploader label, .stCheckbox label,
        .stRadio label, .stSlider label, .stNumberInput label, .stExpander, .stAlert {{
            color: {palette["text"]} !important;
        }}
        [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
            background-color: {palette["panel"]} !important;
            color: {palette["text"]} !important;
        }}
        [data-testid="stHeader"] {{
            background: transparent !important;
        }}
        .stButton>button, .stDownloadButton>button, .stFormSubmitButton>button {{
            background-color: {palette["button"]} !important;
            color: {palette["button_text"]} !important;
            border-radius: 8px !important;
            padding: 0.62em 1.05em !important;
            border: 1px solid {palette["button"]} !important;
            font-weight: 650 !important;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.16) !important;
            min-height: 2.65rem !important;
            opacity: 1 !important;
        }}
        .stButton>button:hover, .stDownloadButton>button:hover, .stFormSubmitButton>button:hover {{
            background-color: {palette["button_hover"]} !important;
            border-color: {palette["button_hover"]} !important;
            color: {palette["button_text"]} !important;
        }}
        .stButton>button:disabled, .stDownloadButton>button:disabled, .stFormSubmitButton>button:disabled {{
            background-color: {palette["panel"]} !important;
            color: {palette["muted"]} !important;
            border-color: {palette["border"]} !important;
            box-shadow: none !important;
        }}
        .stButton>button p, .stDownloadButton>button p, .stFormSubmitButton>button p,
        .stButton>button span, .stDownloadButton>button span, .stFormSubmitButton>button span {{
            color: inherit !important;
        }}
        .stTabs [data-baseweb="tab-list"], div[data-baseweb="tab-list"] {{
            gap: 8px;
            border-bottom: 1px solid {palette["border"]};
        }}
        .stTabs [data-baseweb="tab"], button[data-baseweb="tab"] {{
            background-color: {palette["panel"]} !important;
            color: {palette["text"]} !important;
            border: 1px solid {palette["border"]} !important;
            border-radius: 8px 8px 0 0 !important;
            padding: 8px 14px !important;
        }}
        .stTabs [aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] {{
            background-color: {palette["button"]} !important;
            color: {palette["button_text"]} !important;
            border-color: {palette["button"]} !important;
        }}
        .stTabs [data-baseweb="tab"] p, button[data-baseweb="tab"] p {{
            color: inherit !important;
        }}
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stFileUploader"],
        [data-testid="stExpander"],
        div[data-baseweb="select"] > div,
        .stTextInput input,
        .stTextArea textarea,
        .stDateInput input,
        .stTimeInput input {{
            background-color: {palette["card"]} !important;
            color: {palette["text"]} !important;
            border-color: {palette["border"]} !important;
        }}
        .studio-hero, .studio-nav, .studio-card, .workflow-card, .recent-card, .output-card,
        .form-section, .output-shell, .history-card {{
            background: {palette["card"]} !important;
            border-color: {palette["border"]} !important;
            color: {palette["text"]} !important;
        }}
        .studio-hero h1, .studio-hero p, .studio-eyebrow,
        .studio-nav-brand, .studio-nav-meta,
        .studio-card, .studio-card b,
        .workflow-card b, .workflow-card span,
        .recent-card b, .recent-card p, .recent-card span,
        .sidebar-app-name, .history-title, .section-title, .form-section h3 {{
            color: {palette["text"]} !important;
        }}
        .sidebar-user, .sidebar-label, .section-kicker, .history-meta {{
            color: {palette["muted"]} !important;
        }}
        .stat-icon {{
            background: {palette["button"]} !important;
            color: {palette["button_text"]} !important;
        }}
        .metric-row .studio-card b {{
            color: {palette["button"]} !important;
        }}
        .studio-nav {{
            border-left: 5px solid {palette["button"]} !important;
        }}
        .stInfo, .stSuccess, .stWarning, .stError {{
            color: {palette["text"]} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard():
    projects = list_user_projects()
    stats = project_output_stats(projects)
    recent_cards = recent_project_cards(projects)
    first_name = (current_user().get("name") or "there").split()[0]

    st.markdown(
        f"""
        <section class="studio-hero studio-page">
          <div class="studio-eyebrow">Event Content Studio</div>
          <h1>Welcome back, {first_name}.</h1>
          <p>Create professional flyers, brochures, official reports, and mobile-ready MP4 reels from one organized event workspace.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
          <div class="metric-row">
          <div class="studio-card"><span class="stat-icon">P</span><b>{stats["total"]}</b>Total Projects</div>
          <div class="studio-card"><span class="stat-icon">F</span><b>{stats["flyers"]}</b>Flyers Generated</div>
          <div class="studio-card"><span class="stat-icon">R</span><b>{stats["reports"]}</b>Reports Generated</div>
          <div class="studio-card"><span class="stat-icon">V</span><b>{stats["reels"]}</b>Reels Generated</div>
        </div>
        <div class="workflow-grid">
          <div class="workflow-card"><b>1. Enter Details</b><span>Add event, organization, date, venue, contact, feedback, and supporter information.</span></div>
          <div class="workflow-card"><b>2. Upload Media</b><span>Add logos, photos, videos, sponsor logos, and feedback documents.</span></div>
          <div class="workflow-card"><b>3. Generate</b><span>Create consistent PDF documents and a vertical MP4 reel.</span></div>
          <div class="workflow-card"><b>4. Manage History</b><span>Reopen, edit, download, or delete your own saved projects.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Recent Projects")
    if recent_cards:
        cards_html = "".join(
            f"""
            <div class="recent-card">
              <b>{card["name"]}</b>
              <p>{card["date"]}</p>
              <p>{card["venue"]}</p>
              <span>{card["outputs"]}</span>
            </div>
            """
            for card in recent_cards
        )
        st.markdown(f'<div class="recent-grid">{cards_html}</div>', unsafe_allow_html=True)
    else:
        st.info("No saved projects yet. Create your first event project to see it here.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Creating"):
            st.session_state.edit_project_path = ""
            st.session_state.edit_project_data = {}
            navigate_to("content_creation")
    with col2:
        if st.button("View History"):
            navigate_to("history")


def generate_outputs(data, project_folder, logo_path):
    generated_outputs = {}
    preview_logo = image_data_uri(logo_path)
    photo_paths = existing_media_paths(project_folder, "photos", data.get("photos", []))
    sponsor_paths = [
        os.path.join(project_folder, "assets", "sponsors", name)
        for name in data.get("sponsor_logos", [])
        if os.path.exists(os.path.join(project_folder, "assets", "sponsors", name))
    ]
    video_paths = existing_media_paths(project_folder, "videos", data.get("videos", []))
    banner_photo = image_data_uri(photo_paths[0]) if photo_paths else ""
    photo_uris = image_data_uris(photo_paths)
    sponsor_uris = image_data_uris(sponsor_paths)

    if "Brochure" in data["expected_output"]:
        path = os.path.join(project_folder, "brochure.pdf")
        generate_brochure_pdf(data, path, logo_path)
        generated_outputs["Brochure"] = {
            "type": "pdf",
            "path": path,
            "preview": build_brochure_preview_html(data, preview_logo, sponsor_uris, banner_photo, photo_uris),
        }

    if "Flyer" in data["expected_output"]:
        path = os.path.join(project_folder, "flyer.pdf")
        generate_flyer_pdf(data, path, logo_path)
        generated_outputs["Flyer"] = {
            "type": "pdf",
            "path": path,
            "preview": build_flyer_preview_html(data, preview_logo, sponsor_uris, banner_photo, photo_uris),
        }

    if "Report" in data["expected_output"]:
        path = os.path.join(project_folder, "report.pdf")
        generate_report_pdf(data, path, logo_path)
        generated_outputs["Report"] = {
            "type": "pdf",
            "path": path,
            "preview": build_report_preview_html(data, preview_logo, sponsor_uris, photo_uris),
        }

    if "Caption" in data["expected_output"]:
        path = os.path.join(project_folder, "caption.txt")
        caption = build_caption(data)
        with open(path, "w", encoding="utf-8") as file:
            file.write(caption)
        generated_outputs["Caption"] = {"type": "text", "path": path, "content": caption}

    if "Reel Content" in data["expected_output"]:
        path = os.path.join(project_folder, "reel_content.mp4")
        logger.debug("Number of uploaded photos detected: %s", len(photo_paths))
        logger.debug("Number of uploaded videos detected: %s", len(video_paths))
        logger.debug("Photo paths passed to generate_reel_mp4(): %s", photo_paths)
        logger.debug("Video paths passed to generate_reel_mp4(): %s", video_paths)
        if not photo_paths and not video_paths:
            generated_outputs["Reel Content"] = {
                "type": "warning",
                "message": "No uploaded photos or videos were found, so the reel was not generated. Add at least one photo or video and try again.",
            }
        else:
            try:
                verify_ffmpeg_installation()
                generate_reel_mp4(
                    data,
                    path,
                    logo_path,
                    photo_paths,
                    video_paths,
                    data.get("reel_format", REEL_FORMAT_OPTIONS[DEFAULT_REEL_FORMAT_LABEL]),
                )
                video_meta = validate_generated_mp4(path)
            except Exception as error:
                generated_outputs["Reel Content"] = {"type": "error", "message": str(error)}
            else:
                generated_outputs["Reel Content"] = {"type": "video", "path": path, "meta": video_meta}

    return generated_outputs


def render_content_creation():
    edit_data = st.session_state.get("edit_project_data") or {}
    is_edit = bool(st.session_state.get("edit_project_path") and edit_data)
    st.markdown(
        f"""
        <section class="studio-hero studio-page">
          <div class="studio-eyebrow">{"Edit Project" if is_edit else "Content Creation"}</div>
          <h1>{"Update your saved event project." if is_edit else "Build a complete event content package."}</h1>
          <p>Use Tab to move through fields quickly. Upload media once, choose the outputs, and generate polished PDFs plus a vertical MP4 reel.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if is_edit:
        st.info("Saved inputs are loaded. Existing media will be reused unless you upload additional files.")

    with st.container(border=True):
        st.markdown(
            '<div class="section-title">Event Details</div><div class="section-kicker">Core event identity, schedule, venue, and contact information.</div>',
            unsafe_allow_html=True,
        )
        organization_name = st.text_input(
            "Organization Name",
            value=edit_data.get("organization_name", ""),
            placeholder="Example: Sunrise Foundation",
        )
        organization_logo = st.file_uploader("Upload Organization Logo", type=["jpg", "jpeg", "png"])
        event_name = st.text_input(
            "Event Name",
            value=edit_data.get("event_name", ""),
            placeholder="Example: National Science Day Workshop",
        )

        duration_options = ["One Day", "Hours", "Multiple Days"]
        duration_default = edit_data.get("event_duration_type", "One Day")
        duration_index = duration_options.index(duration_default) if duration_default in duration_options else 0
        duration_type = st.selectbox("Event Duration", duration_options, index=duration_index)
        if duration_type == "Hours":
            date_col, start_time_col, end_time_col = st.columns(3)
            with date_col:
                start_date = st.date_input("Event Date", value=parse_date_value(edit_data.get("start_date")))
            end_date = start_date
            with start_time_col:
                start_time = st.time_input("Start Time", value=form_time_value(edit_data.get("start_time"), "09:00"))
            with end_time_col:
                end_time = st.time_input("End Time", value=form_time_value(edit_data.get("end_time"), "17:00"))
        elif duration_type == "Multiple Days":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=parse_date_value(edit_data.get("start_date")))
            with col2:
                end_date = st.date_input("End Date", value=parse_date_value(edit_data.get("end_date")))
            start_time = None
            end_time = None
        else:
            start_date = st.date_input("Event Date", value=parse_date_value(edit_data.get("start_date")))
            end_date = start_date
            start_time = None
            end_time = None

        location = st.text_input("Location Name", value=edit_data.get("location", ""), placeholder="Venue or campus name")
        location_map_link = st.text_input(
            "Location Map Link",
            value=edit_data.get("location_map_link", ""),
            placeholder="Optional Google Maps or venue link",
        )
        event_description = st.text_area(
            "Event Description",
            value=edit_data.get("event_description", ""),
            placeholder="Summarize the event purpose, audience, activities, and outcome.",
        )
        event_type = st.text_input("Event Type", value=edit_data.get("event_type", ""), placeholder="Workshop, seminar, camp, drive...")
        status_options = ["Upcoming", "Completed"]
        status_default = edit_data.get("event_status", "Upcoming")
        status_index = status_options.index(status_default) if status_default in status_options else 0
        event_status = st.selectbox("Event Status", status_options, index=status_index)

        st.markdown('<div class="section-title">Contact Information</div>', unsafe_allow_html=True)
        contact_col1, contact_col2, contact_col3 = st.columns(3)
        with contact_col1:
            contact_person = st.text_input("Contact Person", value=edit_data.get("contact_person", ""), placeholder="Coordinator name")
        with contact_col2:
            contact_number = st.text_input("Contact Number", value=edit_data.get("contact_number", ""), placeholder="Phone number")
        with contact_col3:
            contact_email = st.text_input("Contact Email", value=edit_data.get("contact_email", ""), placeholder="Email address")

    with st.container(border=True):
        st.markdown(
            '<div class="section-title">Media Uploads</div><div class="section-kicker">Add event photos, videos, sponsor assets, and collaborator information.</div>',
            unsafe_allow_html=True,
        )
        media_col1, media_col2 = st.columns(2)
        with media_col1:
            photos = st.file_uploader("Upload Photos", accept_multiple_files=True, type=["jpg", "jpeg", "png"])
            sponsor_logos = st.file_uploader(
                "Upload Sponsor Logos",
                accept_multiple_files=True,
                type=["jpg", "jpeg", "png"],
            )
        with media_col2:
            videos = st.file_uploader("Upload Videos", accept_multiple_files=True, type=["mp4", "mov"])
            sponsors = st.text_area(
                "Sponsors (optional)",
                value=edit_data.get("sponsors", ""),
                help="Enter one sponsor per line. Leave blank to hide this section.",
            )
        collaborators = st.text_area(
            "Collaborators (optional)",
            value=edit_data.get("collaborators", ""),
            help="Enter one collaborator per line. Leave blank to hide this section.",
        )
        render_uploaded_media_preview(photos, videos, edit_data)

    with st.container(border=True):
        st.markdown(
            '<div class="section-title">Feedback</div><div class="section-kicker">Attach feedback documents and summarize attendee responses for reports.</div>',
            unsafe_allow_html=True,
        )
        feedback_col1, feedback_col2 = st.columns(2)
        with feedback_col1:
            audio_comments = st.text_area("Audio Comments", value=edit_data.get("audio_comments", ""))
        with feedback_col2:
            feedback_document = st.file_uploader("Upload Feedback Document", type=["pdf"])
            feedback_summary = st.text_area("Feedback Summary", value=edit_data.get("feedback_summary", ""))

    with st.container(border=True):
        st.markdown(
            '<div class="section-title">Output Selection</div><div class="section-kicker">Choose the assets to generate. Feed video is the balanced default for modern mobile viewing.</div>',
            unsafe_allow_html=True,
        )
        output_options = DEFAULT_OUTPUTS
        default_outputs = edit_data.get("expected_output") or st.session_state.get("last_expected_output") or output_options
        default_outputs = [item for item in default_outputs if item in output_options]
        expected_output = st.multiselect(
            "Expected Output",
            output_options,
            default=default_outputs,
        )
        saved_format = edit_data.get("reel_format", REEL_FORMAT_OPTIONS[DEFAULT_REEL_FORMAT_LABEL])
        format_labels = list(REEL_FORMAT_OPTIONS.keys())
        saved_format_label = next(
            (label for label, value in REEL_FORMAT_OPTIONS.items() if value == saved_format),
            DEFAULT_REEL_FORMAT_LABEL,
        )
        reel_format_label = st.selectbox(
            "Video Format",
            format_labels,
            index=format_labels.index(saved_format_label),
        )
        reel_format = REEL_FORMAT_OPTIONS[reel_format_label]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Back"):
            navigate_to("welcome")

    with col2:
        if st.button("Regenerate and Save" if is_edit else "Generate Output"):
            if not organization_name or not event_name or not location or not event_type:
                st.error("Please fill in Organization Name, Event Name, Location Name and Event Type.")
                return
            if duration_type == "Multiple Days" and end_date < start_date:
                st.error("End Date must be the same as or later than Start Date.")
                return

            if is_edit:
                project_folder = st.session_state.edit_project_path
                timestamp = edit_data.get("project_timestamp") or datetime.now().strftime("%Y%m%d_%H%M%S")
            else:
                project_folder, timestamp = create_project_folder(event_name)

            photo_names = save_uploaded_files(
                photos,
                os.path.join(project_folder, "assets", "photos"),
                os.path.join(ASSETS_DIR, "photos"),
            )
            photo_names = list(dict.fromkeys((edit_data.get("photos", []) if is_edit else []) + photo_names))
            video_names = save_uploaded_files(
                videos,
                os.path.join(project_folder, "assets", "videos"),
                os.path.join(ASSETS_DIR, "videos"),
            )
            video_names = list(dict.fromkeys((edit_data.get("videos", []) if is_edit else []) + video_names))
            feedback_doc_name, _ = save_single_upload(
                feedback_document,
                os.path.join(project_folder, "assets", "documents"),
                os.path.join(ASSETS_DIR, "documents"),
            )
            if is_edit and not feedback_doc_name:
                feedback_doc_name = edit_data.get("feedback_document", "")
            logo_name, logo_path = save_single_upload(
                organization_logo,
                os.path.join(project_folder, "assets", "logos"),
                os.path.join(ASSETS_DIR, "logos"),
            )
            if is_edit and not logo_name:
                logo_name = edit_data.get("organization_logo", "")
                logo_path = os.path.join(project_folder, "assets", "logos", logo_name) if logo_name else ""
            sponsor_names = save_uploaded_files(
                sponsor_logos,
                os.path.join(project_folder, "assets", "sponsors"),
                os.path.join(ASSETS_DIR, "sponsors"),
            )
            sponsor_names = list(dict.fromkeys((edit_data.get("sponsor_logos", []) if is_edit else []) + sponsor_names))

            data = {
                "project_timestamp": timestamp,
                "project_folder": project_folder,
                "organization_name": organization_name,
                "organization_logo": logo_name,
                "event_name": event_name,
                "event_duration_type": duration_type,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "start_time": start_time.strftime("%I:%M %p") if start_time else "",
                "end_time": end_time.strftime("%I:%M %p") if end_time else "",
                "location": location,
                "location_map_link": location_map_link,
                "event_description": event_description,
                "event_type": event_type,
                "event_status": event_status,
                "contact_person": contact_person,
                "contact_number": contact_number,
                "contact_email": contact_email,
                "photos": photo_names,
                "videos": video_names,
                "sponsors": sponsors,
                "collaborators": collaborators,
                "sponsor_logos": sponsor_names,
                "audio_comments": audio_comments,
                "feedback_document": feedback_doc_name,
                "feedback_summary": feedback_summary,
                "expected_output": expected_output,
                "reel_format": reel_format,
                "owner_user_id": current_user_id(),
                "owner_email": current_user_email(),
                "owner_name": current_user().get("name", ""),
            }
            save_last_expected_output(expected_output)

            with open(os.path.join(project_folder, "event_data.json"), "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)
            with open(os.path.join(OUTPUTS_DIR, "event_data.json"), "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)

            generated_outputs = generate_outputs(data, project_folder, logo_path)
            st.session_state.generated_data = generated_outputs
            st.session_state.current_project_folder = project_folder
            st.session_state.edit_project_path = ""
            st.session_state.edit_project_data = {}
            st.session_state.output_success_message = True
            navigate_to("output")


def render_output():
    st.markdown(
        """
        <section class="studio-hero studio-page">
          <div class="studio-eyebrow">Generated Outputs</div>
          <h1>Your event content is ready.</h1>
          <p>Preview the generated documents and reel, then download the final files for sharing, submission, or publishing.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.get("output_success_message"):
        st.success("Outputs generated successfully. Preview and download files below.")
        st.session_state.output_success_message = False

    ordered_titles = DEFAULT_OUTPUTS
    available_titles = [
        title for title in ordered_titles if title in st.session_state.generated_data
    ]

    if not available_titles:
        st.info("No generated outputs found.")
    else:
        tabs = st.tabs(available_titles)
        for tab, title in zip(tabs, available_titles):
            item = st.session_state.generated_data[title]
            with tab:
                st.markdown(f'<div class="output-shell"><div class="section-title">{title} Preview</div>', unsafe_allow_html=True)

                if item["type"] == "pdf":
                    if item.get("preview"):
                        st.components.v1.html(item["preview"], height=700, scrolling=True)
                    else:
                        st.info("Professional PDF report generated. Use the download button below.")
                    st.download_button(
                        label=f"Download {title} PDF",
                        data=file_bytes(item["path"]),
                        file_name=os.path.basename(item["path"]),
                        mime="application/pdf",
                        key=f"download-{title}",
                    )
                elif item["type"] == "video":
                    format_label = "Instagram Feed Video (4:5)"
                    if st.session_state.current_project_folder:
                        data = read_project_data(st.session_state.current_project_folder)
                        if data.get("reel_format") == "reel_9_16":
                            format_label = "Instagram Reel / Shorts (9:16)"
                    try:
                        video_meta = item.get("meta") or validate_generated_mp4(item["path"])
                    except Exception as error:
                        st.error(f"The generated video is not ready for preview/download: {error}")
                    else:
                        st.caption(
                            f"{format_label} MP4, {video_meta['width']}x{video_meta['height']}, "
                            f"H.264/AAC, optimized for Streamlit, Windows Media Player, VLC, and mobile sharing."
                        )
                        st.video(item["path"])
                        st.download_button(
                            label=f"Download {title} MP4",
                            data=file_bytes(item["path"]),
                            file_name=os.path.basename(item["path"]),
                            mime="video/mp4",
                            key=f"download-{title}",
                        )
                elif item["type"] == "error":
                    st.error(item["message"])
                elif item["type"] == "warning":
                    st.warning(item["message"])
                else:
                    st.text_area(f"{title} Preview", item["content"], height=320)
                    st.download_button(
                        label=f"Download {title}",
                        data=item["content"],
                        file_name=os.path.basename(item["path"]),
                        mime="text/plain",
                        key=f"download-{title}",
                    )
                st.markdown("</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Back to Form"):
            navigate_to("content_creation")
    with col2:
        if st.button("Project History"):
            navigate_to("history")
    with col3:
        if st.button("Go to Welcome Page"):
            navigate_to("welcome")


def load_project_outputs(project_path):
    outputs = {}
    data_path = os.path.join(project_path, "event_data.json")
    logo_path = ""

    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        data["project_folder"] = data.get("project_folder") or project_path
        if data.get("organization_logo"):
            logo_path = os.path.join(project_path, "assets", "logos", data["organization_logo"])
        logo_uri = image_data_uri(logo_path)
        photo_preview_paths = [
            os.path.join(project_path, "assets", "photos", name)
            for name in data.get("photos", [])
            if os.path.exists(os.path.join(project_path, "assets", "photos", name))
        ]
        sponsor_preview_paths = [
            os.path.join(project_path, "assets", "sponsors", name)
            for name in data.get("sponsor_logos", [])
            if os.path.exists(os.path.join(project_path, "assets", "sponsors", name))
        ]
        banner_photo = image_data_uri(photo_preview_paths[0]) if photo_preview_paths else ""
        photo_uris = image_data_uris(photo_preview_paths)
        sponsor_uris = image_data_uris(sponsor_preview_paths)
    else:
        data = {}
        logo_uri = ""
        banner_photo = ""
        photo_uris = []
        sponsor_uris = []

    file_map = {
        "Brochure": (["brochure.pdf"], "pdf"),
        "Flyer": (["flyer.pdf"], "pdf"),
        "Report": (["report.pdf"], "pdf"),
        "Caption": (["caption.txt"], "text"),
        "Reel Content": (["reel_content.mp4", "reel_video.mp4"], "video"),
    }

    for title, (file_names, file_type) in file_map.items():
        path = ""
        for file_name in file_names:
            candidate = os.path.join(project_path, file_name)
            if os.path.exists(candidate):
                path = candidate
                break
        if not os.path.exists(path):
            continue

        if file_type == "text":
            with open(path, "r", encoding="utf-8") as file:
                outputs[title] = {"type": "text", "path": path, "content": file.read()}
        elif file_type == "video":
            try:
                outputs[title] = {"type": "video", "path": path, "meta": validate_generated_mp4(path)}
            except Exception as error:
                outputs[title] = {"type": "error", "message": f"Saved video is not playable: {error}"}
        elif title == "Brochure" and data:
            outputs[title] = {
                "type": "pdf",
                "path": path,
                "preview": build_brochure_preview_html(data, logo_uri, sponsor_uris, banner_photo, photo_uris),
            }
        elif title == "Flyer" and data:
            outputs[title] = {
                "type": "pdf",
                "path": path,
                "preview": build_flyer_preview_html(data, logo_uri, sponsor_uris, banner_photo, photo_uris),
            }
        elif title == "Report" and data:
            outputs[title] = {
                "type": "pdf",
                "path": path,
                "preview": build_report_preview_html(data, logo_uri, sponsor_uris, photo_uris),
            }
        else:
            outputs[title] = {"type": "pdf", "path": path, "preview": ""}

    return outputs


def render_history():
    st.markdown(
        """
        <section class="studio-hero studio-page">
          <div class="studio-eyebrow">Project History</div>
          <h1>Manage saved event projects.</h1>
          <p>Reopen generated outputs, edit saved inputs, download files, or remove projects you no longer need.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if not os.path.exists(PROJECTS_DIR):
        st.info("No projects found.")
    else:
        projects = list_user_projects()

        if not projects:
            st.info("No projects found.")

        for project in projects:
            project_path = os.path.join(PROJECTS_DIR, project)
            data_path = os.path.join(project_path, "event_data.json")

            if os.path.exists(data_path):
                data = read_project_data(project_path)
                title = data.get("event_name", project)
                timestamp = data.get("project_timestamp", project[:15])
            else:
                title = project
                timestamp = project[:15]

            data = read_project_data(project_path) if os.path.exists(data_path) else {}
            files = [name for name in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, name))]
            st.markdown(
                f"""
                <div class="history-card studio-page">
                  <div class="history-title">{title}</div>
                  <div class="history-meta">{timestamp} | {data.get("location", "No venue saved")} | {len(files)} files</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("Project actions and downloads"):
                files = [name for name in os.listdir(project_path) if os.path.isfile(os.path.join(project_path, name))]
                st.caption("Generated files: " + (", ".join(files) if files else "No output files found."))

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("Reopen Project", key=f"reopen-{project}"):
                        st.session_state.generated_data = load_project_outputs(project_path)
                        st.session_state.current_project_folder = project_path
                        navigate_to("output")

                with col2:
                    if st.button("Edit Project", key=f"edit-{project}"):
                        st.session_state.edit_project_path = project_path
                        st.session_state.edit_project_data = read_project_data(project_path)
                        navigate_to("content_creation")

                with col3:
                    for file_name in files:
                        path = os.path.join(project_path, file_name)
                        if file_name.endswith(".pdf"):
                            mime = "application/pdf"
                        elif file_name.endswith(".mp4"):
                            mime = "video/mp4"
                        else:
                            mime = "text/plain"
                        st.download_button(
                            f"Download {file_name}",
                            data=file_bytes(path),
                            file_name=file_name,
                            mime=mime,
                            key=f"history-download-{project}-{file_name}",
                        )

                with col4:
                    confirm_delete = st.checkbox(
                        "Confirm delete",
                        key=f"confirm-delete-{project}",
                    )
                    if st.button(
                        "Delete Project",
                        key=f"delete-{project}",
                        disabled=not confirm_delete,
                    ):
                        try:
                            delete_project_folder(project_path)
                        except PermissionError:
                            st.error(
                                "Windows blocked deletion for this project. Close any open PDFs/files from this project, wait for OneDrive sync to finish, then try again."
                            )
                        except OSError as error:
                            st.error(f"Could not delete this project: {error}")
                        else:
                            if st.session_state.current_project_folder == project_path:
                                st.session_state.current_project_folder = ""
                                st.session_state.generated_data = {}
                            st.success("Project deleted from history.")
                            st.rerun()

    if st.button("Back to Welcome"):
        navigate_to("welcome")


init_state()
ensure_base_folders()
restore_remembered_login()

if not is_logged_in():
    st.session_state.page = "auth"
    apply_theme()
    render_auth_page()
else:
    sync_page_from_query()
    render_account_controls()
    apply_theme()
    if st.session_state.page == "welcome":
        render_dashboard()
    elif st.session_state.page == "content_creation":
        render_content_creation()
    elif st.session_state.page == "history":
        render_history()
    elif st.session_state.page == "output":
        render_output()
