from pathlib import Path


FRONTEND_HTML = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


def test_modals_are_scrollable_and_form_fields_do_not_force_horizontal_overflow():
    html = FRONTEND_HTML.read_text()

    assert ".modal-box" in html
    assert "max-height: calc(100vh - 40px);" in html
    assert "overflow-y: auto;" in html
    assert "box-sizing: border-box;" in html
    assert "overflow-wrap: anywhere;" in html


def test_apply_button_opens_real_job_url_before_tracking_application():
    html = FRONTEND_HTML.read_text()

    assert "beginApplication(" in html
    assert "/api/jobs/${jobId}/apply-assist" in html
    assert "window.open(jobUrl, '_blank', 'noopener,noreferrer')" in html
    assert "confirm('Se abrió la oferta real" in html


def test_outreach_modal_can_generate_ai_email():
    html = FRONTEND_HTML.read_text()

    assert "generateOutreachEmail(" in html
    assert "/api/email/generate" in html
    assert "GENERAR CON IA" in html
