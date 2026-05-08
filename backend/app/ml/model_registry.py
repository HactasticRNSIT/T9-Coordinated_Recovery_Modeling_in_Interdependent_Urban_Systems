"""
Model Registry — loads and caches all ML models at startup.
Provides a single access point for inference.
"""
import os
import json
import torch
import joblib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Singleton registry for all ML models."""

    _gnn_model = None
    _lstm_model = None
    _xgb_model = None
    _gnn_config = None
    _lstm_config = None
    _xgb_config = None
    _loaded = False

    @classmethod
    async def load_all_models(cls):
        """Load all models from disk at application startup."""
        models_path = os.getenv("ML_MODELS_PATH", "./ml_pipeline/artifacts")

        if not os.path.exists(models_path):
            logger.warning(f"ML models path not found: {models_path}. Running without ML models.")
            cls._loaded = True
            return

        # Load GNN
        gnn_path = os.path.join(models_path, "gnn_cascade_best.pt")
        gnn_config_path = os.path.join(models_path, "gnn_config.json")
        if os.path.exists(gnn_path) and os.path.exists(gnn_config_path):
            try:
                with open(gnn_config_path) as f:
                    cls._gnn_config = json.load(f)
                # Import here to avoid circular imports
                from ml_pipeline.training.train_gnn import CascadeGNN, NODE_FEATURE_DIM
                cls._gnn_model = CascadeGNN(in_channels=NODE_FEATURE_DIM)
                cls._gnn_model.load_state_dict(torch.load(gnn_path, map_location="cpu"))
                cls._gnn_model.eval()
                logger.info(f"GNN model loaded: {cls._gnn_config.get('version')}")
            except Exception as e:
                logger.error(f"Failed to load GNN model: {e}")

        # Load LSTM
        lstm_path = os.path.join(models_path, "lstm_recovery_best.pt")
        lstm_config_path = os.path.join(models_path, "lstm_config.json")
        if os.path.exists(lstm_path) and os.path.exists(lstm_config_path):
            try:
                with open(lstm_config_path) as f:
                    cls._lstm_config = json.load(f)
                from ml_pipeline.training.train_lstm import RecoveryLSTM
                cls._lstm_model = RecoveryLSTM(
                    input_size=cls._lstm_config["input_size"],
                    hidden_size=cls._lstm_config["hidden_size"],
                    num_layers=cls._lstm_config["num_layers"],
                )
                cls._lstm_model.load_state_dict(torch.load(lstm_path, map_location="cpu"))
                cls._lstm_model.eval()
                logger.info(f"LSTM model loaded: {cls._lstm_config.get('version')}")
            except Exception as e:
                logger.error(f"Failed to load LSTM model: {e}")

        # Load XGBoost
        xgb_path = os.path.join(models_path, "xgb_resilience.pkl")
        xgb_config_path = os.path.join(models_path, "xgb_config.json")
        if os.path.exists(xgb_path) and os.path.exists(xgb_config_path):
            try:
                with open(xgb_config_path) as f:
                    cls._xgb_config = json.load(f)
                cls._xgb_model = joblib.load(xgb_path)
                logger.info(f"XGBoost model loaded: {cls._xgb_config.get('version')}")
            except Exception as e:
                logger.error(f"Failed to load XGBoost model: {e}")

        cls._loaded = True
        logger.info("Model registry initialization complete")

    @classmethod
    def get_gnn(cls):
        return cls._gnn_model

    @classmethod
    def get_lstm(cls):
        return cls._lstm_model

    @classmethod
    def get_xgb(cls):
        return cls._xgb_model

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._loaded

    @classmethod
    def get_status(cls) -> dict:
        return {
            "gnn": cls._gnn_model is not None,
            "lstm": cls._lstm_model is not None,
            "xgb": cls._xgb_model is not None,
            "gnn_version": cls._gnn_config.get("version") if cls._gnn_config else None,
            "lstm_version": cls._lstm_config.get("version") if cls._lstm_config else None,
            "xgb_version": cls._xgb_config.get("version") if cls._xgb_config else None,
        }
