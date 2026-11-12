"""Shared application workflow for already-decoded workbook measurements.

This is an operational, offline entry point used by both CLI and Streamlit.
It is not a raw-CAN decoder, an AI tool registry, or a cloud acquisition service.
"""
from .recording import Recording


def prepare_workbook(source, *, profile=None, quality_config=None, sheet=None,
                     max_rows=250_000, filename=None) -> Recording:
    """Import, screen and calculate signed power without a presentation dependency.

    Accept the same path/seekable binary source as ``excel.load_xlsx``. Explicit
    profile/quality settings are forwarded unchanged. Raw measurements, source
    provenance, uncertain units and original recording order remain intact.
    Excel dependencies are loaded only when this workbook workflow is called.
    Engineering analysis and report generation remain separate reusable steps.
    """
    from .excel import load_xlsx
    from .quality import validate_recording
    from .diagnostics import calculate_power

    recording = load_xlsx(source, profile=profile, sheet=sheet, max_rows=max_rows,
                          filename=filename)
    validate_recording(recording, quality_config)
    return calculate_power(recording)
