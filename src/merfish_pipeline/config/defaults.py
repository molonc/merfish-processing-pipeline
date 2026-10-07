"""Default constants and fallback values for the merFISH pipeline configuration."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Valid microscope identifiers
# ---------------------------------------------------------------------------
VALID_MICROSCOPES: list[str] = ["oni", "nikon", "andor"]

# ---------------------------------------------------------------------------
# All recognised pipeline stage names (in canonical execution order)
# ---------------------------------------------------------------------------
VALID_STAGES: list[str] = [
    "index",
    "atlas_export",
    "stitch",
    "focus_qc",
    "inspect_positions",
    "reregistration",
    "convert",
    "ims_convert",
    "merlin_config",
    "filter_barcodes",
    "correlation",
    "optimize_correlation",
    "joint_optimization",
    "segmentation",
    "cell_assignment",
    "barcode_qc",
    "anndata_export",
    "spatial_visualization",
]

# ---------------------------------------------------------------------------
# Derived paths that are created under output_dir when not explicitly set
# ---------------------------------------------------------------------------
DEFAULT_DERIVED_PATHS: dict[str, str] = {
    "remapped_data_dir": "remapped_data",
    "merlin_data_dir": "merlin_data",
    "parameters_dir": "parameters",
    "logs_dir": "logs",
}

# ---------------------------------------------------------------------------
# Per-microscope fallback defaults (used when no YAML file is found for the
# requested microscope).  These mirror the expected YAML content so the
# pipeline can still run with sensible values.
# ---------------------------------------------------------------------------
MICROSCOPE_DEFAULTS: dict[str, dict] = {
    "oni": {
        "file_pattern": "merFISH_{ir}_{fov}_{z}.TIFF",
        "position_file_pattern": "stagePos_Round#{round}.csv",
        "position_format": "csv",
        "stage_x_heading": "stage_pos_x",
        "stage_y_heading": "stage_pos_y",
        "log_file_name": "merfish_log.txt",
        "microns_per_pixel": 0.1168224,
        "image_dimensions": [684, 428],
        "flip_horizontal": False,
        "flip_vertical": False,
        "transpose": False,
        "default_bead_channel": "488nm, Raw",
        "default_data_org_template": "XP8054_dataorganization.csv",
        "default_analysis_template": "ONI_Adaptive_analysis.json",
        "default_microscope_template": "ONI_microscope.json",
    },
    "nikon": {
        "file_pattern": "merFISH_{ir}_{fov}_{z}.TIFF",
        "position_file_pattern": "stagePos_Round_{round}.xlsx",
        "position_format": "xlsx",
        "stage_x_heading": "stage_pos_x",
        "stage_y_heading": "stage_pos_y",
        "log_file_name": "merlog.txt",
        "microns_per_pixel": 0.174129,
        "image_dimensions": [1608, 1608],
        "flip_horizontal": True,
        "flip_vertical": True,
        "transpose": False,
        "default_bead_channel": "473nm, Raw",
        "default_data_org_template": "XP8054_dataorganization.csv",
        "default_analysis_template": "NIKON_Adaptive_analysis.json",
        "default_microscope_template": "NIKON_microscope.json",
    },
    "andor": {
        "file_pattern": "*_F{fov:03d}.ims",
        "position_file_pattern": None,
        "position_format": "ims",
        "stage_x_heading": None,
        "stage_y_heading": None,
        "log_file_name": "merfish_log.txt",
        "microns_per_pixel": 0.15078125,
        "image_dimensions": [2048, 2048],
        "flip_horizontal": False,
        "flip_vertical": False,
        "transpose": False,
        "default_bead_channel": "488nm, Raw",
        "default_data_org_template": "XP8054_dataorganization.csv",
        "default_analysis_template": "ANDOR_Adaptive_analysis.json",
        "default_microscope_template": "ANDOR_microscope.json",
    },
}
