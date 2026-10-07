"""Pipeline stages package.

Submodules
----------
base
    Abstract PipelineStage base class and StageResult dataclass.
registry
    Stage name -> class mapping via @register_stage decorator.
index
    Scan raw data and produce manifest + standardized positions.
stitch
    Build tile mosaics from bead-channel images.
focus_qc
    Per-FOV best-focus detection via Laplacian-of-Gaussian variance.
inspect_positions
    Analyse position drift across rounds and parse microscope logs.
reregistration
    Z-slice remapping for uniform depth across FOVs.
merlin_config
    Generate all MERlin parameter files (does not run MERlin).
segmentation
    Cellpose cell segmentation on aligned microscopy images.
cell_assignment
    Assign decoded barcodes to segmented cells using per-FOV masks.
barcode_qc
    Post-MERlin QC report with barcode metrics and diagnostic plots.
anndata_export
    Export cell-by-gene count matrix to AnnData h5ad format.
optimize_correlation
    Find gene subgroups maximizing bulk RNA-seq correlation via simulated annealing.
joint_optimization
    Find gene subgroups maximizing bulk correlation across multiple experiments.
spatial_visualization
    Interactive 3D spatial scatter plot of decoded barcodes.
"""

from merfish_pipeline.stages.base import PipelineStage, StageResult
from merfish_pipeline.stages.registry import (
    STAGE_REGISTRY,
    get_stage,
    list_stages,
    register_stage,
)

# Import concrete stages so their @register_stage decorators fire.
from merfish_pipeline.stages.index import IndexStage  # noqa: F401
from merfish_pipeline.stages.stitch import StitchStage  # noqa: F401
from merfish_pipeline.stages.focus_qc import FocusQCStage  # noqa: F401
from merfish_pipeline.stages.inspect_positions import InspectPositionsStage  # noqa: F401
from merfish_pipeline.stages.reregistration import ReregistrationStage  # noqa: F401
from merfish_pipeline.stages.convert import ConvertStage  # noqa: F401
from merfish_pipeline.stages.ims_convert import IMSConvertStage  # noqa: F401
from merfish_pipeline.stages.merlin_config import MerlinConfigStage  # noqa: F401
from merfish_pipeline.stages.filter_barcodes import FilterBarcodesStage  # noqa: F401
from merfish_pipeline.stages.correlation import CorrelationStage  # noqa: F401
from merfish_pipeline.stages.optimize_correlation import OptimizeCorrelationStage  # noqa: F401
from merfish_pipeline.stages.joint_optimization import JointOptimizationStage  # noqa: F401
from merfish_pipeline.stages.segmentation import SegmentationStage  # noqa: F401
from merfish_pipeline.stages.cell_assignment import CellAssignmentStage  # noqa: F401
from merfish_pipeline.stages.barcode_qc import BarcodeQCStage  # noqa: F401
from merfish_pipeline.stages.anndata_export import AnnDataExportStage  # noqa: F401
from merfish_pipeline.stages.spatial_visualization import SpatialVisualizationStage  # noqa: F401
from merfish_pipeline.stages.atlas_export import AtlasExportStage

__all__ = [
    "PipelineStage",
    "StageResult",
    "STAGE_REGISTRY",
    "register_stage",
    "get_stage",
    "list_stages",
]
