from __future__ import annotations
from tqdm import tqdm

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from tifffile import tifffile
from concurrent.futures import ThreadPoolExecutor, as_completed
from shutil import copy2

from merfish_pipeline.io.sheet_io import read_sheet, write_sheet
from merfish_pipeline.stages.base import PipelineStage, StageResult
from merfish_pipeline.stages.registry import register_stage
from typing import Any
# ---------------------------------------------------------------------------
# Package-level templates directory (two levels up from the ``src/`` tree)
# ---------------------------------------------------------------------------

_PACKAGE_DIR = Path(__file__).resolve().parent  # .../stages/
_TEMPLATES_DIR = _PACKAGE_DIR.parents[2] / "templates"  # repo-root/templates


def _resolve_template(path: Path | str, templates_dir: Path | None = None) -> Path:
    """Locate a template file.

    Resolution order:

    1. If *path* is absolute and exists, return it directly.
    2. If *templates_dir* is given, look for ``templates_dir / path`` and common
       sub-directories (``dataorganization/``, ``microscope/``, ``analysis/``,
       ``codebooks/``).
    3. Fall back to the package-level ``templates/`` directory using the same
       sub-directory search.

    Raises
    ------
    FileNotFoundError
        If the template cannot be found in any of the searched locations.
    """
    path = Path(path)

    # 1. Absolute and exists
    if path.is_absolute() and path.exists():
        return path

    search_dirs: list[Path] = []
    for base in [templates_dir, _TEMPLATES_DIR]:
        if base is None or not base.is_dir():
            continue
        search_dirs.append(base)
        for subdir in ("dataorganization", "microscope", "analysis", "codebooks"):
            candidate = base / subdir
            if candidate.is_dir():
                search_dirs.append(candidate)

    for directory in search_dirs:
        candidate = directory / path.name
        if candidate.exists():
            return candidate
        # Also try the path as-is (may include subdirectory components)
        candidate = directory / path
        if candidate.exists():
            return candidate

    searched = ", ".join(str(d) for d in search_dirs) if search_dirs else "(none)"
    raise FileNotFoundError(f"Template not found: {path}. Searched in: {searched}")


def merge_fov(fov, meta, manifest, shape, dtype, channel_lut):
    files = manifest.loc[manifest["fov"] == fov, ["round", "channel", "z_slice", "abs_path"]]
    merged = tifffile.memmap(meta[0], shape=shape, dtype=dtype, metadata = meta[1], ome = True)

    for file in files.itertuples(index=False):
        plane = tifffile.imread(file.abs_path)
        c = channel_lut[file.channel]
        merged[file.round - 1, c, file.z_slice - 1, ...] = plane

    return meta[0]


# ---------------------------------------------------------------------------
# Stage implementation
# ---------------------------------------------------------------------------


@register_stage("atlas_export")
class AtlasExportStage(PipelineStage):
    """
        Export Vancouver Merfish Experiment into Atlas Optimized Format --> Files Merged into (Time,Channel, Z, Y, X) stacks
        Doing So lowers total number of files significantly --> saving costs on upload and download
    """

    description = " Export Vancouver Merfish Experiment into Atlas Optimized Format"    

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    def validate_inputs(self) -> list[str]:
        errors: list[str] = []

        # Manifest from index stage
        manifest_path = self._manifest_path()
        if not manifest_path.exists():
            errors.append(f"Manifest not found (run 'index' stage first): {manifest_path}")

        # Positions from index stage
        positions_path = self._positions_path()
        if not positions_path.exists():
            errors.append(f"Positions file not found (run 'index' stage first): {positions_path}")

        return errors

    def check_outputs_exist(self) -> bool:
        """Return True if all key output files already exist."""
        output_dir = self.get_output_dir()

        if (output_dir / "atlas_export").exists():
            return True
        return False

    def run(self, dry_run: bool = False) -> StageResult:
        start_time = datetime.now()
        output_dir = self.get_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        xp_name = self.config.experiment.name
        export_dir = output_dir / "atlas_export"

        export_dir.mkdir(parents=True, exist_ok=True)
        output_files: list[str] = []
        workers = self.config.execution.max_workers
        # ---------------------------------------------------------------
        # 0. Read manifest to get n_z_slices and n_channels
        # ---------------------------------------------------------------
        manifest_path = self._manifest_path()
        position_path = self._positions_path()
        self.logger.info("Reading manifest from %s", manifest_path)
        manifest = read_sheet(manifest_path)
        positions = read_sheet(position_path)

        if manifest.empty:
            return StageResult(status="failed", error=f"Manifest is empty {manifest_path}")
        if positions.empty:
            return StageResult(status="failed", error=f"Positions is empty {position_path}")

        n_z = manifest["z_slice"].nunique()
        n_ir = manifest["round"].nunique()

        # -------------------------------------------------------------
        # 1. Extract image shape, pixel size, z step and a channel lookup table
        # -------------------------------------------------------------
        pixel_size = self.config.microscope.microns_per_pixel
        z_step = abs(
            positions.loc[:, positions.columns.str.match("z_position")]
            .diff(axis=1)
            .dropna(axis=1)
            .mean(axis=None)
        )
        img_shape = self.config.microscope.image_dimensions
        channels = sorted(manifest["channel"].unique())
        channel_lut = pd.Series(list(range(len(channels))), index=channels)
        fovs = manifest["fov"].unique()
        self.logger.info(
            "Manifest: %d imaging-rounds %d z-slices, %d channels %d fovs",
            n_ir,
            n_z,
            len(channels),
            len(fovs),
        )
        shape = (n_ir, len(channels), n_z, img_shape[0], img_shape[1])
        self.logger.info("FOV Size: t: %d c: %d z: %d y: %d x: %d", *shape)
        ome = {
            "axes": "TCZYX",
            "PhysicalSizeX": pixel_size,
            "PhysicalSizeY": pixel_size,
            "PhysicalSizeZ": z_step,
            "PhysicalSizeXUnit": "um",
            "PhysicalSizeYUnit": "um",
            "PhysicalSizeZUnit": "um",
        }
        if dry_run:
            self.logger.info(f"Would Merge {len(fovs)} FOVS into {shape} volumes")
            return StageResult(status="skipped", metadata={"dry_run": True, "n_groups": len(fovs)})

        self.logger.info("Merging %d FOVS with %d workers", len(fovs), workers)
        tasks = []
        with ThreadPoolExecutor(workers) as pool:
            for fov in fovs:
                tasks.append(
                    pool.submit(
                        merge_fov,
                        fov,
                        (export_dir / f"{xp_name}_FOV_{fov}.tiff", ome),
                        manifest,
                        shape,
                        "uint16",
                        channel_lut,
                    )
                )
            for future in as_completed(tasks):
                fov = future.result()
                self.logger.info(f"Wrote FOV {fov}")
                output_files.append(fov)
        positions_export = export_dir / position_path.name 
        copy2(position_path, positions_export)
        output_files.append(position_export)
        return StageResult(status="passed", output_files=output_files, error="")

    # ------------------------------------------------------------------
    # Internal: reregistration detection
    # ------------------------------------------------------------------

    def _detect_reregistration(self) -> dict | None:
        """Check if the reregistration stage ran and return its metadata.

        Returns
        -------
        dict or None
            If reregistration ran successfully, returns a dict with key
            ``target_z`` (int).
            Returns ``None`` if reregistration was not enabled or has no output.
        """
        if not self.config.reregistration.enabled:
            return None

        rereg_metadata_path = (
            Path(self.config.paths.output_dir) / "reregistration" / "run_metadata.json"
        )
        if not rereg_metadata_path.exists():
            return None

        try:
            with open(rereg_metadata_path, "r", encoding="utf-8") as fh:
                metadata = json.load(fh)
            target_z = metadata.get("parameters", {}).get("target_z")
            if target_z is None:
                self.logger.warning(
                    "Reregistration metadata exists but missing target_z: %s",
                    rereg_metadata_path,
                )
                return None
            return {"target_z": int(target_z)}
        except (json.JSONDecodeError, KeyError) as exc:
            self.logger.warning(
                "Could not parse reregistration metadata (%s): %s",
                rereg_metadata_path,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Internal: path resolution helpers
    # ------------------------------------------------------------------

    def _manifest_path(self) -> Path:
        """Path to the manifest CSV produced by the index stage."""
        return Path(self.config.paths.output_dir) / "index" / "manifest.csv"

    def _positions_path(self) -> Path:
        """Path to the standardized positions CSV produced by the index stage."""
        return Path(self.config.paths.output_dir) / "index" / "positions.standardized.csv"
