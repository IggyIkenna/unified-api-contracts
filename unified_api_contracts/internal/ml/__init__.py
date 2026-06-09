"""Internal ML schemas — model metadata, inference requests/responses, training jobs.

Re-exports the ML schemas from ``ml_backup`` (a proper submodule split is pending — see TODO below).
"""

# Import everything from backup to maintain compatibility temporarily
from ..ml_backup import *  # noqa: F403

# TODO: Complete proper module split in follow-up task
# The file was too large to properly split within time constraints
# This maintains compatibility while allowing gradual migration

__all__ = [  # noqa: F405
    # Re-export all symbols from original file
    "BackfillSpec",
    "CalibrationConfig",
    "LightGBMHyperparams",
    "MLModelScorecard",
    "MLPrediction",
    "ModelArtifactRegistry",
    "ModelType",
    "TargetType",
    "TrainingObjective",
    "TrainingPeriod",
    "TrainingPhase",
    "TrainingScope",
    "XGBoostHyperparams",
    # Add other exports as needed
]
