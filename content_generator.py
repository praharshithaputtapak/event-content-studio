import html
import os
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepInFrame,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BRAND_COLOR = colors.HexColor("#1D4ED8")
ACCENT_COLOR = colors.HexColor("#F97316")
INK_COLOR = colors.HexColor("#111827")
MUTED_COLOR = colors.HexColor("#6B7280")
LINE_COLOR = colors.HexColor("#D1D5DB")
SOFT_BLUE = colors.HexColor("#EFF6FF")
SOFT_ORANGE = colors.HexColor("#FFF7ED")
SOFT_BG = colors.HexColor("#F3F4F6")


def slugify(value):
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_")
    return cleaned or "event_project"


def create_project_folder(event_name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{timestamp}_{slugify(event_name)}"
    project_folder = os.path.join("generated_projects", folder_name)
    for folder in [
        project_folder,
        os.path.join(project_folder, "assets", "photos"),
        os.path.join(project_folder, "assets", "videos"),
        os.path.join(project_folder, "assets", "documents"),
        os.path.join(project_folder, "assets", "logos"),
        os.path.join(project_folder, "assets", "sponsors"),
    ]:
        os.makedirs(folder, exist_ok=True)
    return project_folder, timestamp


def photo_paths(data):
    project_folder = data.get("project_folder", "")
    paths = []
    for name in data.get("photos", []):
        candidates = [
            name,
            os.path.join(project_folder, "assets", "photos", name),
            os.path.join("assets", "photos", name),
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                paths.append(candidate)
                break
    return paths


def sponsor_paths(data):
    project_folder = data.get("project_folder", "")
    paths = []
    for name in data.get("sponsor_logos", []):
        candidates = [
            name,
            os.path.join(project_folder, "assets", "sponsors", name),
            os.path.join("assets", "sponsors", name),
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                paths.append(candidate)
                break
    return paths


def build_event_highlights(data):
    event_type = (data.get("event_type") or "event").lower()
    return [
        f"Focused {event_type} sessions with guided activities",
        "Interactive participation and knowledge-sharing moments",
        "Practical takeaways for attendees and community members",
        "Structured closing reflections and event highlights",
    ]


def build_participation_text(data):
    event_type = (data.get("event_type") or "event").lower()
    return (
        f"Open to students, faculty members, professionals, volunteers, and participants "
        f"interested in this {event_type}."
    )


def build_key_benefits(data):
    return [
        "Learn from structured sessions and real event activities",
        "Connect with peers, organizers, and invited guests",
        "Build awareness, skills, and confidence through participation",
    ]


def build_caption(data):
    contact_values = [
        data.get("contact_person"),
        data.get("contact_email"),
        data.get("contact_number"),
    ]
    contact_line = " | ".join(_clean_text(value) for value in contact_values if _has_content(value))
    contact_text = f"\nContact: {contact_line}" if contact_line else ""
    return f"""Celebrating {data['event_name']} at {data['location']}.

{data.get('event_description') or 'A meaningful event filled with learning, participation, and shared moments.'}

Date: {_event_date_display(data)}{contact_text}
Organized by: {data['organization_name']}
Location: {data.get('location_map_link') or data['location']}

#Event #Community #Learning #Highlights"""


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="StudioTitle",
            parent=styles["Title"],
            textColor=INK_COLOR,
            fontSize=27,
            leading=33,
            alignment=TA_CENTER,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="StudioFlyerTitle",
            parent=styles["Title"],
            textColor=BRAND_COLOR,
            fontSize=34,
            leading=39,
            alignment=TA_CENTER,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="StudioReportTitle",
            parent=styles["Title"],
            textColor=BRAND_COLOR,
            fontSize=25,
            leading=31,
            alignment=TA_CENTER,
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="StudioSection",
            parent=styles["Heading2"],
            textColor=BRAND_COLOR,
            fontSize=15,
            leading=19,
            spaceBefore=14,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="StudioSubsection",
            parent=styles["Heading3"],
            textColor=INK_COLOR,
            fontSize=12,
            leading=15,
            spaceBefore=8,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="StudioBody",
            parent=styles["BodyText"],
            textColor=INK_COLOR,
            fontSize=10.2,
            leading=14.5,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="StudioSmall",
            parent=styles["BodyText"],
            textColor=MUTED_COLOR,
            fontSize=8.5,
            leading=11,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="StudioMutedCenter",
            parent=styles["BodyText"],
            textColor=MUTED_COLOR,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
        )
    )
    return styles


def _report_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="OfficialCoverTitle",
            parent=styles["Title"],
            textColor=colors.black,
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="OfficialEventName",
            parent=styles["Title"],
            textColor=colors.HexColor("#222222"),
            fontSize=20,
            leading=26,
            alignment=TA_CENTER,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="OfficialHeading",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#333333"),
            fontSize=15,
            leading=20,
            spaceBefore=12,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="OfficialBody",
            parent=styles["BodyText"],
            textColor=colors.black,
            fontSize=10.5,
            leading=15,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="OfficialCenter",
            parent=styles["BodyText"],
            textColor=colors.black,
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )
    return styles


def _safe_paragraph(value):
    text = html.escape(str(value or ""))
    return text.replace("\n", "<br/>")


def _document_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#CCCCCC"))
    canvas.setLineWidth(0.4)
    canvas.line(doc.leftMargin, 28, A4[0] - doc.rightMargin, 28)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(A4[0] - doc.rightMargin, 16, f"Page {doc.page}")
    canvas.restoreState()


def _build_doc(path, story):
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=44,
        leftMargin=44,
        topMargin=40,
        bottomMargin=40,
    )
    doc.build(story, onFirstPage=_document_footer, onLaterPages=_document_footer)


def _build_flyer_doc(path, story):
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=32,
        leftMargin=32,
        topMargin=28,
        bottomMargin=28,
    )
    doc.build(story)


def _image_element(path, width, height=None):
    if not path or not os.path.exists(path):
        return None
    if height is None:
        height = width
    return Image(path, width=width, height=height, kind="proportional")


def _bullet_list(items, styles):
    return [Paragraph(f"- {_safe_paragraph(item)}", styles["StudioBody"]) for item in items]
# ---------------------------------------------------------------------
# Shared layout source for previews and PDFs.
# Streamlit preview and downloaded PDF use this same section order, text,
# image selection, and document data.
# ---------------------------------------------------------------------


def _contact_lines(data):
    lines = []
    if data.get("contact_person"):
        lines.append(f"Contact Person: {data['contact_person']}")
    if data.get("contact_number"):
        lines.append(f"Contact Number: {data['contact_number']}")
    if data.get("contact_email"):
        lines.append(f"Contact Email: {data['contact_email']}")
    return lines


def _organization_lines(data):
    return [
        f"Organization: {data['organization_name']}",
        "Responsible for planning, coordination, communication, and participant support.",
    ]


def _participant_lines(data):
    lines = [build_participation_text(data)]
    if data.get("event_status"):
        lines.append(f"Event Status: {data['event_status']}")
    if data.get("event_type"):
        lines.append(f"Event Type: {data['event_type']}")
    return lines


def _event_summary_text(data):
    description = _clean_text(data.get("event_description"))
    if description:
        return (
            f"The event was organized by {data['organization_name']} at {data['location']}. "
            f"It focused on {data['event_type'].lower()} activities and participant engagement."
        )
    return (
        f"{data['event_name']} was organized by {data['organization_name']} at {data['location']} "
        "with structured planning, implementation, and documentation."
    )


def _observations_text(data):
    feedback = _clean_text(data.get("feedback_summary"))
    if feedback:
        return feedback
    return "The event showed active participation, organized execution, and useful engagement among attendees."


def _default_photo_images(data):
    return photo_paths(data)


def _default_sponsor_images(data):
    return sponsor_paths(data)


def _clean_text(value):
    return str(value or "").strip()


def _has_content(value):
    if isinstance(value, (list, tuple)):
        return any(_has_content(item) for item in value)
    return bool(_clean_text(value))


def _split_lines(value):
    lines = []
    for raw_line in _clean_text(value).replace(",", "\n").splitlines():
        line = raw_line.strip(" -\t")
        if line:
            lines.append(line)
    return lines


def _event_date_display(data):
    duration = data.get("event_duration_type") or "Multiple Days"
    start_date = _clean_text(data.get("start_date"))
    end_date = _clean_text(data.get("end_date"))
    start_time = _clean_text(data.get("start_time"))
    end_time = _clean_text(data.get("end_time"))

    if duration == "Hours":
        time_range = " to ".join(part for part in [start_time, end_time] if part)
        return f"{start_date} | {time_range}" if time_range else start_date
    if duration == "One Day":
        return start_date
    if end_date and end_date != start_date:
        return f"{start_date} to {end_date}"
    return start_date


def _event_duration_display(data):
    duration = data.get("event_duration_type") or "One Day"
    start_time = _clean_text(data.get("start_time"))
    end_time = _clean_text(data.get("end_time"))
    start_date = _clean_text(data.get("start_date"))
    end_date = _clean_text(data.get("end_date"))

    if duration == "Hours":
        time_range = " to ".join(part for part in [start_time, end_time] if part)
        return time_range or "Hours"
    if duration == "Multiple Days":
        if start_date and end_date and end_date != start_date:
            return "Multiple Days"
        return "One Day"
    return "One Day"


def _sponsor_text_items(data):
    return _split_lines(data.get("sponsors") or data.get("sponsor_names"))


def _collaborator_items(data):
    return _split_lines(data.get("collaborators"))


def _layout_assets(data, logo_image=None, photo_images=None, sponsor_images=None):
    return {
        "logo": logo_image or "",
        "photos": photo_images if photo_images is not None else _default_photo_images(data),
        "sponsors": sponsor_images if sponsor_images is not None else _default_sponsor_images(data),
    }


def build_document_layout(kind, data, logo_image=None, photo_images=None, sponsor_images=None):
    assets = _layout_assets(data, logo_image, photo_images, sponsor_images)
    photos = assets["photos"]
    sponsor_images = assets["sponsors"]
    sponsors = _sponsor_text_items(data)
    collaborators = _collaborator_items(data)
    contact_lines = _contact_lines(data)
    event_date = _event_date_display(data)
    event_duration = _event_duration_display(data)
    description = data.get("event_description")
    feedback = data.get("feedback_summary")
    audio_comments = data.get("audio_comments")

    common_header = {
        "type": "header",
        "logo": assets["logo"],
        "logo_size": {"flyer": 1.58, "brochure": 1.45, "report": 1.9}.get(kind, 1.35),
        "organization": data["organization_name"],
        "title": data["event_name"] if kind != "report" else "Event Report",
        "subtitle": (
            f"{data['event_type']} | {data['event_status']}"
            if kind != "report"
            else data["event_name"]
        ),
    }

    info_cards = {
        "type": "cards",
        "title": "Event Information",
        "items": [
            ("Date", event_date),
            ("Location", data["location"]),
            ("Event Type", data["event_type"]),
            ("Status", data["event_status"]),
        ],
    }

    if kind == "flyer":
        flyer_cards = {
            "type": "cards",
            "title": "Event Information",
            "items": [
                ("Date", event_date),
                ("Venue", data["location"]),
                ("Event Type", data["event_type"]),
                ("Duration", event_duration),
            ],
        }
        return {
            "kind": "flyer",
            "sections": [
                common_header,
                {"type": "banner_image", "image": photos[0] if photos else ""},
                flyer_cards,
                {"type": "text", "title": "Event Description", "body": description},
                {"type": "bullets", "title": "Event Highlights", "items": build_event_highlights(data)[:3]},
                {"type": "text", "title": "Who Can Participate", "body": build_participation_text(data)},
                {"type": "bullets", "title": "Benefits", "items": build_key_benefits(data)},
                {"type": "lines", "title": "Contact Details", "items": contact_lines},
                {"type": "supporters", "title": "Sponsors", "items": sponsors, "images": sponsor_images},
                {"type": "lines", "title": "Collaborators", "items": collaborators},
                {
                    "type": "organization_footer",
                    "title": "Organization",
                    "logo": assets["logo"],
                    "name": data["organization_name"],
                },
            ],
        }

    if kind == "brochure":
        return {
            "kind": "brochure",
            "sections": [
                common_header,
                {"type": "banner_image", "image": photos[0] if photos else ""},
                info_cards,
                {"type": "text", "title": "Detailed Description", "body": description},
                {"type": "bullets", "title": "Event Highlights", "items": build_event_highlights(data)},
                {
                    "type": "text",
                    "title": "Location Information",
                    "body": data.get("location_map_link"),
                },
                {"type": "photo_grid", "title": "Event Photos", "items": photos[1:]},
                {"type": "lines", "title": "Contact Details", "items": contact_lines},
                {"type": "supporters", "title": "Sponsors", "items": sponsors, "images": sponsor_images},
                {"type": "lines", "title": "Collaborators", "items": collaborators},
                {"type": "lines", "title": "Organization Details", "items": _organization_lines(data)},
            ],
        }

    return {
        "kind": "report",
        "sections": [
            common_header,
            {"type": "cards", "title": "Cover Details", "items": [("Date", event_date), ("Venue", data["location"])]},
            {"type": "page_break"},
            {"type": "text", "title": "Event Overview", "body": description},
            {
                "type": "bullets",
                "title": "Event Objectives",
                "items": [
                    "Deliver a meaningful and well-coordinated event experience.",
                    "Encourage active participation and knowledge sharing.",
                    "Document outcomes, feedback, and memorable moments for future reference.",
                ],
            },
            {"type": "text", "title": "Event Summary", "body": _event_summary_text(data)},
            {"type": "page_break"},
            {"type": "text", "title": "Event Execution", "body": description},
            {"type": "bullets", "title": "Activities Conducted", "items": build_event_highlights(data)},
            {"type": "lines", "title": "Participant Information", "items": _participant_lines(data)},
            *(
                [
                    {"type": "page_break"},
                    {"type": "photo_grid", "title": "Event Gallery", "items": photos, "items_per_page": 4},
                ]
                if photos
                else []
            ),
            {"type": "page_break"},
            {"type": "text", "title": "Feedback Summary", "body": feedback},
            {"type": "text", "title": "Observations", "body": audio_comments or _observations_text(data)},
            {
                "type": "text",
                "title": "Conclusion",
                "body": (
                    f"{data['event_name']} was documented as a structured event with "
                    "clear participation, outcomes, and feedback for future improvement."
                ),
            },
            {"type": "lines", "title": "Contact Information", "items": contact_lines},
            {"type": "lines", "title": "Organization Information", "items": _organization_lines(data)},
        ],
    }


def _html_image(src, class_name):
    return f'<img src="{src}" class="{class_name}" />' if src else ""


def _render_preview_section(section):
    section_type = section["type"]

    if section_type == "header":
        return f"""
        <section class="preview-header-block">
          {_html_image(section.get("logo"), "logo")}
          <h1>{html.escape(section["title"])}</h1>
          <div class="banner">{html.escape(section["subtitle"])}</div>
        </section>
        """

    if section_type == "banner_image":
        return _html_image(section.get("image"), "preview-photo")

    if section_type == "cards":
        if not section.get("items"):
            return ""
        cards = "".join(
            f"<div><b>{html.escape(label)}</b><span>{html.escape(str(value))}</span></div>"
            for label, value in section["items"]
            if _has_content(value)
        )
        if not cards:
            return ""
        return f"<h2>{html.escape(section['title'])}</h2><div class=\"detail-grid\">{cards}</div>"

    if section_type == "text":
        if not _has_content(section.get("body")):
            return ""
        return f"<h2>{html.escape(section['title'])}</h2><p>{_safe_paragraph(section.get('body'))}</p>"

    if section_type == "bullets":
        items = "".join(f"<li>{html.escape(item)}</li>" for item in section["items"] if _has_content(item))
        if not items:
            return ""
        return f"<h2>{html.escape(section['title'])}</h2><ul>{items}</ul>"

    if section_type == "lines":
        lines = "".join(f"<p>{html.escape(item)}</p>" for item in section["items"] if _has_content(item))
        if not lines:
            return ""
        return f"<h2>{html.escape(section['title'])}</h2>{lines}"

    if section_type == "photo_grid":
        if not section.get("items"):
            return ""
        images = "".join(
            f"""
            <figure>
              {_html_image(item, "grid-photo")}
            </figure>
            """
            for item in section["items"]
            if _has_content(item)
        )
        if not images:
            return ""
        return f"<h2>{html.escape(section['title'])}</h2><div class=\"photo-grid\">{images}</div>"

    if section_type == "supporters":
        names = "".join(f"<p>{html.escape(item)}</p>" for item in section.get("items", []) if _has_content(item))
        images = "".join(_html_image(src, "sponsor-logo") for src in section.get("images", []))
        if not names and not images:
            return ""
        return f"<h2>{html.escape(section['title'])}</h2><div class=\"sponsor-strip\"><span>{images}</span>{names}</div>"

    if section_type == "organization_footer":
        if not _has_content(section.get("name")) and not section.get("logo"):
            return ""
        return f"""
        <h2>{html.escape(section['title'])}</h2>
        <div class="footer-organization">
          {_html_image(section.get("logo"), "footer-logo")}
          <p>{html.escape(section.get("name", ""))}</p>
        </div>
        """

    if section_type == "page_break":
        return '<div class="page-divider"></div>'

    return ""


def _render_flyer_layout_preview(layout):
    header = _layout_section(layout, "header")
    banner = _layout_section(layout, "banner_image")
    cards = _layout_section(layout, "cards")
    description = _layout_section(layout, "text", "Event Description")
    highlights = _layout_section(layout, "bullets", "Event Highlights")
    participant = _layout_section(layout, "text", "Who Can Participate")
    benefits = _layout_section(layout, "bullets", "Benefits")
    contact = _layout_section(layout, "lines", "Contact Details")
    sponsors = _layout_section(layout, "supporters", "Sponsors")
    collaborators = _layout_section(layout, "lines", "Collaborators")
    organization = _layout_section(layout, "organization_footer")

    def render_if_present(section):
        return _render_preview_section(section) if section else ""

    lower_sections = "".join(
        f'<div class="flyer-block">{_render_preview_section(section)}</div>'
        for section in [highlights, participant, benefits]
        if section and _render_preview_section(section)
    )
    supporter_html = ""
    sponsor_content = render_if_present(sponsors)
    collaborator_content = render_if_present(collaborators)
    if sponsor_content or collaborator_content:
        supporter_html = f'<div class="flyer-info-block">{sponsor_content}{collaborator_content}</div>'

    bottom_sections = "".join(
        f'<div class="flyer-info-block">{rendered}</div>'
        for rendered in [render_if_present(contact), render_if_present(organization)]
        if rendered
    ) + supporter_html
    footer_class = "has-supporters" if supporter_html else "no-supporters"

    return f"""
    <div class="preview flyer-preview">
      {_render_preview_section(header)}
      {_render_preview_section(banner)}
      {_render_preview_section(cards)}
      {_render_preview_section(description)}
      {f'<div class="flyer-lower-grid">{lower_sections}</div>' if lower_sections else ''}
      {f'<div class="flyer-bottom-grid {footer_class}">{bottom_sections}</div>' if bottom_sections else ''}
    </div>
    """


def render_layout_preview_html(layout):
    if layout["kind"] == "flyer":
        return _render_flyer_layout_preview(layout)
    sections = "".join(_render_preview_section(section) for section in layout["sections"])
    return f'<div class="preview {layout["kind"]}-preview">{sections}</div>'


def _pdf_header(section, styles):
    story = []
    logo_size = section.get("logo_size", 1.0) * inch
    logo = _image_element(section.get("logo"), logo_size, logo_size)
    if logo:
        table = Table([[logo]], colWidths=[6.2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (0, 0), (0, 0), 0),
                    ("TOPPADDING", (0, 0), (0, 0), 0),
                    ("BOTTOMPADDING", (0, 0), (0, 0), 0),
                ]
            )
        )
        story.append(table)
    story.extend(
        [
            Spacer(1, 8),
            Paragraph(_safe_paragraph(section["title"]), styles["StudioTitle"]),
            Paragraph(_safe_paragraph(section["subtitle"]), styles["StudioMutedCenter"]),
            Spacer(1, 10),
        ]
    )
    return story


def _pdf_cards(section, styles):
    rows = [
        [
            Paragraph(f"<b>{html.escape(str(label))}</b>", styles["StudioBody"]),
            Paragraph(_safe_paragraph(value), styles["StudioBody"]),
        ]
        for label, value in section["items"]
        if _has_content(value)
    ]
    if not rows:
        return []
    table = Table(rows, colWidths=[1.35 * inch, 4.85 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return [Paragraph(section["title"], styles["StudioSection"]), table]


def _pdf_image_grid(items, styles, items_per_page=None):
    cells = []
    for image_path in items:
        image = _image_element(image_path, 2.85 * inch, 2.05 * inch)
        if image:
            cells.append(image)

    story = []
    if items_per_page:
        chunks = [cells[index : index + items_per_page] for index in range(0, len(cells), items_per_page)]
    else:
        chunks = [cells]

    for chunk_index, chunk in enumerate(chunks):
        if chunk_index > 0:
            story.append(PageBreak())
        for index in range(0, len(chunk), 2):
            row = chunk[index : index + 2]
            if len(row) == 1:
                row.append("")
            table = Table([row], colWidths=[3.05 * inch, 3.05 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.35, LINE_COLOR),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ]
                )
            )
            story.append(table)
    return story


def _pdf_sponsor_grid(images):
    cells = []
    for image_path in images[:8]:
        image = _image_element(image_path, 0.45 * inch, 0.32 * inch)
        if image:
            cells.append(image)
    if not cells:
        return []
    return [Table([cells], hAlign="LEFT")]


def _pdf_supporter_block(section, styles):
    story = []
    images = _pdf_sponsor_grid(section.get("images", []))
    names = [item for item in section.get("items", []) if _has_content(item)]
    if not images and not names:
        return story

    story.append(Paragraph(section["title"], styles["StudioSection"]))
    story.extend(images)
    for name in names:
        story.append(Paragraph(_safe_paragraph(name), styles["StudioBody"]))
    story.append(Spacer(1, 6))
    return story


def _layout_section(layout, section_type=None, title=None):
    for section in layout["sections"]:
        if section_type and section.get("type") != section_type:
            continue
        if title and section.get("title") != title:
            continue
        return section
    return {}


def _compact_text_block(title, body, styles):
    if not _has_content(body):
        return ""
    return [
        Paragraph(f"<b>{html.escape(title)}</b>", styles["StudioSubsection"]),
        Paragraph(_safe_paragraph(body), styles["StudioSmall"]),
    ]


def _compact_bullet_block(title, items, styles):
    items = [item for item in items if _has_content(item)]
    if not items:
        return ""
    return [
        Paragraph(f"<b>{html.escape(title)}</b>", styles["StudioSubsection"]),
        *[Paragraph(f"- {_safe_paragraph(item)}", styles["StudioSmall"]) for item in items[:3]],
    ]


def _compact_lines_block(title, items, styles):
    items = [item for item in items if _has_content(item)]
    if not items:
        return ""
    return [
        Paragraph(f"<b>{html.escape(title)}</b>", styles["StudioSubsection"]),
        *[Paragraph(_safe_paragraph(item), styles["StudioSmall"]) for item in items],
    ]


def _compact_organization_footer_block(section, styles):
    logo = _image_element(section.get("logo"), 0.55 * inch, 0.55 * inch)
    block = [Paragraph(f"<b>{html.escape(section.get('title', 'Organization'))}</b>", styles["StudioSubsection"])]
    if logo:
        block.append(Table([[logo]], hAlign="CENTER"))
    if _has_content(section.get("name")):
        block.append(Paragraph(_safe_paragraph(section.get("name")), styles["StudioSmall"]))
    return block if len(block) > 1 else ""


def _compact_supporters_footer_block(sponsors, collaborators, styles):
    sponsor_names = [item for item in sponsors.get("items", []) if _has_content(item)] if sponsors else []
    sponsor_images = sponsors.get("images", []) if sponsors else []
    collaborator_names = [item for item in collaborators.get("items", []) if _has_content(item)] if collaborators else []
    if not sponsor_names and not sponsor_images and not collaborator_names:
        return ""

    block = [Paragraph("<b>Supporters</b>", styles["StudioSubsection"])]
    sponsor_grid = _pdf_sponsor_grid(sponsor_images)
    block.extend(sponsor_grid)
    for name in sponsor_names[:4]:
        block.append(Paragraph(_safe_paragraph(name), styles["StudioSmall"]))
    for name in collaborator_names[:4]:
        block.append(Paragraph(f"Collaborator: {_safe_paragraph(name)}", styles["StudioSmall"]))
    return block


def render_flyer_pdf(layout, output_path):
    styles = _styles()
    header = _layout_section(layout, "header")
    banner = _layout_section(layout, "banner_image")
    cards = _layout_section(layout, "cards")
    description = _layout_section(layout, "text", "Event Description")
    highlights = _layout_section(layout, "bullets", "Event Highlights")
    participant = _layout_section(layout, "text", "Who Can Participate")
    benefits = _layout_section(layout, "bullets", "Benefits")
    contact = _layout_section(layout, "lines", "Contact Details")
    sponsors = _layout_section(layout, "supporters", "Sponsors")
    collaborators = _layout_section(layout, "lines", "Collaborators")
    organization = _layout_section(layout, "organization_footer")

    logo_size = header.get("logo_size", 1.45) * inch
    logo = _image_element(header.get("logo"), logo_size, logo_size)
    header_rows = []
    if logo:
        header_rows.append([logo])
    header_rows.extend(
        [
            [Paragraph(_safe_paragraph(header.get("title")), styles["StudioFlyerTitle"])],
            [Paragraph(_safe_paragraph(header.get("subtitle")), styles["StudioMutedCenter"])],
        ]
    )
    header_table = Table(header_rows, colWidths=[7.25 * inch])
    header_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.8, BRAND_COLOR),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    info_items = [
        (label, value)
        for label, value in cards.get("items", [])
        if label in ["Date", "Venue", "Location", "Event Type", "Duration"] and _has_content(value)
    ]
    info_cells = [
        Paragraph(f"<b>{html.escape(label)}</b><br/>{_safe_paragraph(value)}", styles["StudioBody"])
        for label, value in info_items
    ]
    if not info_cells:
        info_cells = [Paragraph("", styles["StudioBody"])]
    while len(info_cells) < 4:
        info_cells.append("")
    info_table = Table([info_cells[:4]], colWidths=[1.78 * inch, 1.78 * inch, 1.78 * inch, 1.78 * inch])
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT_ORANGE),
                ("BOX", (0, 0), (-1, -1), 0.6, ACCENT_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story = [header_table, Spacer(1, 6)]
    banner_image = _image_element(banner.get("image"), 7.1 * inch, 2.25 * inch)
    if banner_image:
        story.extend([Table([[banner_image]], hAlign="CENTER"), Spacer(1, 7)])
    story.extend(
        [
            info_table,
            Spacer(1, 6),
            *(_compact_text_block("Description", description.get("body"), styles) or []),
            Spacer(1, 4),
        ]
    )

    lower_cells = [
        _compact_bullet_block("Highlights", highlights.get("items", []), styles),
        _compact_text_block("Who Can Participate", participant.get("body"), styles),
        _compact_bullet_block("Benefits", benefits.get("items", []), styles),
    ]
    lower_cells = [cell or "" for cell in lower_cells]
    lower_table = Table([lower_cells], colWidths=[2.35 * inch, 2.35 * inch, 2.35 * inch])
    lower_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([lower_table, Spacer(1, 7)])

    bottom_blocks = [
        _compact_lines_block("Contact", contact.get("items", []), styles),
        _compact_organization_footer_block(organization, styles),
        _compact_supporters_footer_block(sponsors, collaborators, styles),
    ]
    bottom_blocks = [block for block in bottom_blocks if block]

    if bottom_blocks:
        bottom_table = Table([bottom_blocks], colWidths=[7.1 * inch / len(bottom_blocks)] * len(bottom_blocks))
        bottom_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
                    ("BOX", (0, 0), (-1, -1), 0.5, LINE_COLOR),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E5E7EB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(bottom_table)

    _build_flyer_doc(output_path, [KeepInFrame(7.25 * inch, 10.85 * inch, story, mode="shrink")])


def render_layout_pdf(layout, output_path):
    styles = _styles()
    story = []
    is_brochure = layout.get("kind") == "brochure"

    for section in layout["sections"]:
        section_type = section["type"]
        if section_type == "header":
            story.extend(_pdf_header(section, styles))
        elif section_type == "banner_image":
            image_width = 6.2 * inch if is_brochure else 4.85 * inch
            image_height = 2.75 * inch if is_brochure else 2.25 * inch
            image = _image_element(section.get("image"), image_width, image_height)
            if image:
                story.extend([Table([[image]], hAlign="CENTER"), Spacer(1, 10)])
        elif section_type == "cards":
            story.extend(_pdf_cards(section, styles))
            story.append(Spacer(1, 8))
        elif section_type == "text":
            if _has_content(section.get("body")):
                story.extend([Paragraph(section["title"], styles["StudioSection"]), Paragraph(_safe_paragraph(section.get("body")), styles["StudioBody"])])
        elif section_type == "bullets":
            items = [item for item in section["items"] if _has_content(item)]
            if items:
                story.append(Paragraph(section["title"], styles["StudioSection"]))
                story.extend(_bullet_list(items, styles))
        elif section_type == "lines":
            items = [item for item in section["items"] if _has_content(item)]
            if items:
                story.append(Paragraph(section["title"], styles["StudioSection"]))
                for item in items:
                    story.append(Paragraph(_safe_paragraph(item), styles["StudioBody"]))
        elif section_type == "photo_grid" and section.get("items"):
            story.append(Paragraph(section["title"], styles["StudioSection"]))
            story.extend(_pdf_image_grid(section["items"], styles, section.get("items_per_page")))
        elif section_type == "supporters":
            story.extend(_pdf_supporter_block(section, styles))
        elif section_type == "page_break":
            story.append(PageBreak())

    _build_doc(output_path, story)


def _build_report_doc(path, story):
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=54,
        leftMargin=54,
        topMargin=50,
        bottomMargin=50,
    )
    doc.build(story, onFirstPage=_document_footer, onLaterPages=_document_footer)


def _report_cover(header, details, styles):
    story = [Spacer(1, 38)]
    logo = _image_element(header.get("logo"), 2.45 * inch, 2.45 * inch)
    if logo:
        story.extend([Table([[logo]], colWidths=[6.0 * inch], hAlign="CENTER"), Spacer(1, 18)])
    story.extend(
        [
            Paragraph(_safe_paragraph(header.get("organization")), styles["OfficialCenter"]),
            Spacer(1, 22),
            Paragraph("Event Report", styles["OfficialCoverTitle"]),
            Paragraph(_safe_paragraph(header.get("subtitle")), styles["OfficialEventName"]),
            Spacer(1, 18),
        ]
    )
    rows = [
        [
            Paragraph(f"<b>{html.escape(str(label))}</b>", styles["OfficialBody"]),
            Paragraph(_safe_paragraph(value), styles["OfficialBody"]),
        ]
        for label, value in details.get("items", [])
        if _has_content(value)
    ]
    if rows:
        table = Table(rows, colWidths=[1.4 * inch, 4.2 * inch], hAlign="CENTER")
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#777777")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BBBBBB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(table)
    story.append(PageBreak())
    return story


def _report_cards(section, styles):
    rows = [
        [
            Paragraph(f"<b>{html.escape(str(label))}</b>", styles["OfficialBody"]),
            Paragraph(_safe_paragraph(value), styles["OfficialBody"]),
        ]
        for label, value in section.get("items", [])
        if _has_content(value)
    ]
    if not rows:
        return []
    table = Table(rows, colWidths=[1.45 * inch, 4.65 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return [Paragraph(section["title"], styles["OfficialHeading"]), table, Spacer(1, 8)]


def _report_photo_grid(items, styles, items_per_page=4):
    cells = []
    for image_path in items:
        image = _image_element(image_path, 2.85 * inch, 2.05 * inch)
        if image:
            cells.append(image)

    story = []
    chunks = [cells[index : index + items_per_page] for index in range(0, len(cells), items_per_page)]
    for chunk_index, chunk in enumerate(chunks):
        if chunk_index > 0:
            story.append(PageBreak())
        story.append(Paragraph("Event Gallery", styles["OfficialHeading"]))
        for index in range(0, len(chunk), 2):
            row = chunk[index : index + 2]
            if len(row) == 1:
                row.append("")
            table = Table([row], colWidths=[3.05 * inch, 3.05 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
                    ]
                )
            )
            story.append(table)
    return story


def render_report_pdf(layout, output_path):
    styles = _report_styles()
    story = []
    sections = layout["sections"]
    header = _layout_section(layout, "header")
    cover_details = _layout_section(layout, "cards", "Cover Details")
    story.extend(_report_cover(header, cover_details, styles))

    for section in sections[3:]:
        section_type = section["type"]
        if section_type == "header" or section.get("title") == "Cover Details":
            continue
        if section_type == "page_break":
            if story and not isinstance(story[-1], PageBreak):
                story.append(PageBreak())
        elif section_type == "text":
            if _has_content(section.get("body")):
                story.extend(
                    [
                        Paragraph(section["title"], styles["OfficialHeading"]),
                        Paragraph(_safe_paragraph(section.get("body")), styles["OfficialBody"]),
                    ]
                )
        elif section_type == "bullets":
            items = [item for item in section.get("items", []) if _has_content(item)]
            if items:
                story.append(Paragraph(section["title"], styles["OfficialHeading"]))
                for item in items:
                    story.append(Paragraph(f"- {_safe_paragraph(item)}", styles["OfficialBody"]))
        elif section_type == "lines":
            items = [item for item in section.get("items", []) if _has_content(item)]
            if items:
                story.append(Paragraph(section["title"], styles["OfficialHeading"]))
                for item in items:
                    story.append(Paragraph(_safe_paragraph(item), styles["OfficialBody"]))
        elif section_type == "cards":
            story.extend(_report_cards(section, styles))
        elif section_type == "supporters":
            names = [item for item in section.get("items", []) if _has_content(item)]
            images = section.get("images", [])
            if names or images:
                story.append(Paragraph(section["title"], styles["OfficialHeading"]))
                story.extend(_pdf_sponsor_grid(images))
                for name in names:
                    story.append(Paragraph(_safe_paragraph(name), styles["OfficialBody"]))
        elif section_type == "photo_grid" and section.get("items"):
            story.extend(_report_photo_grid(section["items"], styles, section.get("items_per_page", 4)))

    _build_report_doc(output_path, story)


def generate_brochure_pdf(data, output_path, logo_path=None):
    render_layout_pdf(build_document_layout("brochure", data, logo_path), output_path)


def generate_flyer_pdf(data, output_path, logo_path=None):
    render_flyer_pdf(build_document_layout("flyer", data, logo_path), output_path)


def generate_report_pdf(data, output_path, logo_path=None):
    render_report_pdf(build_document_layout("report", data, logo_path), output_path)


def build_brochure_preview_html(data, logo_path=None, sponsor_uris=None, banner_photo=None, photo_uris=None):
    photos = photo_uris if photo_uris is not None else ([banner_photo] if banner_photo else [])
    return render_layout_preview_html(build_document_layout("brochure", data, logo_path, photos, sponsor_uris or []))


def build_flyer_preview_html(data, logo_path=None, sponsor_uris=None, banner_photo=None, photo_uris=None):
    photos = photo_uris if photo_uris is not None else ([banner_photo] if banner_photo else [])
    return render_layout_preview_html(build_document_layout("flyer", data, logo_path, photos, sponsor_uris or []))


def build_report_preview_html(data, logo_path=None, sponsor_uris=None, photo_uris=None):
    return render_layout_preview_html(build_document_layout("report", data, logo_path, photo_uris or [], sponsor_uris or []))
