import json
from pathlib import Path

import cv2
import torch
import wandb
from lightning.pytorch.callbacks import ModelCheckpoint
from lightning.pytorch.cli import LightningArgumentParser, LightningCLI
from lightning.pytorch.loggers import WandbLogger

from src.run_context import RunContextError, load_and_validate_run_context

cv2.setNumThreads(0)
torch.set_float32_matmul_precision("medium")


def apply_run_context_to_config(config, context: dict) -> None:
    """Inject validated data, W&B, and checkpoint policy into parsed CLI config."""
    if config.seed_everything != context["seed"]:
        raise RunContextError(
            "Lightning seed does not match run context: "
            f"{config.seed_everything} != {context['seed']}"
        )
    logger_configs = config.trainer.logger
    if not isinstance(logger_configs, list) or len(logger_configs) != 1:
        raise RunContextError("Run context requires exactly one configured W&B logger")
    logger_config = logger_configs[0]
    if logger_config.class_path != "lightning.pytorch.loggers.WandbLogger":
        raise RunContextError(
            "Run context requires lightning.pytorch.loggers.WandbLogger"
        )
    logger_args = logger_config.init_args
    logger_args.entity = context["wandb_entity"]
    logger_args.project = context["wandb_project"]
    logger_args.group = context["wandb_group"]
    logger_args.name = context["wandb_name"]
    logger_args.job_type = context["wandb_job_type"]
    logger_args.tags = context["wandb_tags"]
    logger_args.offline = context["wandb_offline"]
    # Checkpoint upload is handled explicitly in after_fit so offline and
    # online runs preserve the same best-only artifact contract.
    logger_args.log_model = False
    logger_args.save_dir = config.trainer.default_root_dir
    config.data.init_args.train_chip_dir = context["data_paths"]["train"]
    config.data.init_args.val_chip_dir = context["data_paths"]["val"]
    config.data.init_args.test_chip_dir = context["data_paths"]["test"]

    checkpoint_callbacks = [
        callback
        for callback in config.trainer.callbacks
        if callback.class_path == "lightning.pytorch.callbacks.ModelCheckpoint"
    ]
    if len(checkpoint_callbacks) != 1:
        raise RunContextError(
            "Run context requires exactly one ModelCheckpoint callback"
        )
    checkpoint_args = checkpoint_callbacks[0].init_args
    checkpoint_args.save_top_k = 1
    checkpoint_args.save_last = True


class KelpLightningCLI(LightningCLI):
    """LightningCLI with validated PlanetScope run-context injection."""

    def add_arguments_to_parser(self, parser: LightningArgumentParser) -> None:
        parser.add_argument("--run_context", type=str, default=None)

    def before_instantiate_classes(self) -> None:
        config = self.config[self.subcommand] if self.subcommand else self.config
        context_path = config.get("run_context")
        self.run_context = None
        if not context_path:
            return
        context = load_and_validate_run_context(Path(context_path))
        apply_run_context_to_config(config, context)
        self.run_context = context

    def before_fit(self) -> None:
        if self.run_context is None:
            return
        wandb_loggers = [
            logger for logger in self.trainer.loggers if isinstance(logger, WandbLogger)
        ]
        if len(wandb_loggers) != 1:
            raise RunContextError("Expected exactly one instantiated W&B logger")
        logger = wandb_loggers[0]
        logger.log_hyperparams(self.run_context)

        context_hash = self.run_context["fold_manifest_sha256"][:12]
        metadata_root = (
            Path(self.trainer.default_root_dir) / "run_metadata" / context_hash
        )
        metadata_root.mkdir(parents=True, exist_ok=True)
        resolved_config_path = metadata_root / "resolved_config.yaml"
        resolved_config_path.write_text(self.parser.dump(self.config, skip_none=False))
        context_path = metadata_root / "run_context.json"
        context_path.write_text(
            json.dumps(self.run_context, indent=2, sort_keys=True) + "\n"
        )

        artifact = wandb.Artifact(
            name=f"{self.run_context['wandb_name']}-run-metadata",
            type="run-metadata",
            metadata=self.run_context,
        )
        artifact.add_file(str(resolved_config_path), name="resolved_config.yaml")
        artifact.add_file(str(context_path), name="run_context.json")
        for name in (
            "dataset_metadata",
            "archive_receipt",
            "chip_manifest",
            "fold_manifest",
            "fold_summary",
            "model_config",
        ):
            artifact.add_file(
                self.run_context["source_artifacts"][name], name=f"sources/{name}"
            )
        logger.experiment.log_artifact(artifact)

    def after_fit(self) -> None:
        if self.run_context is None:
            return
        wandb_loggers = [
            logger for logger in self.trainer.loggers if isinstance(logger, WandbLogger)
        ]
        checkpoint_callbacks = [
            callback
            for callback in self.trainer.callbacks
            if isinstance(callback, ModelCheckpoint)
        ]
        if len(wandb_loggers) != 1 or len(checkpoint_callbacks) != 1:
            raise RunContextError(
                "Expected exactly one W&B logger and ModelCheckpoint callback"
            )
        logger = wandb_loggers[0]
        checkpoint = checkpoint_callbacks[0]
        metrics = {
            key: value.item() if hasattr(value, "item") else value
            for key, value in self.trainer.callback_metrics.items()
            if isinstance(value, (bool, int, float)) or hasattr(value, "item")
        }
        logger.experiment.summary.update(metrics)
        best_path = Path(checkpoint.best_model_path)
        if best_path.is_file():
            artifact = wandb.Artifact(
                name=f"{self.run_context['wandb_name']}-best-checkpoint",
                type="model",
                metadata={
                    "fold_id": self.run_context["fold_id"],
                    "fold_manifest_sha256": self.run_context["fold_manifest_sha256"],
                    "monitor": checkpoint.monitor,
                    "best_model_score": (
                        checkpoint.best_model_score.item()
                        if checkpoint.best_model_score is not None
                        else None
                    ),
                    "checkpoint_policy": "best_only",
                },
            )
            artifact.add_file(str(best_path), name=best_path.name)
            logger.experiment.log_artifact(artifact, aliases=["best"])


def cli_main():
    """
    Command-line interface to run SMPSegmentationModel with DataModule.
    """
    cli = KelpLightningCLI(save_config_kwargs={"overwrite": True})
    return cli


if __name__ == "__main__":
    cli_main()

    print("Done!")
