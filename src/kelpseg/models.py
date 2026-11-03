"""The single baseline segmentation model."""

import segmentation_models_pytorch as smp


def build_model(
    in_channels: int, *, encoder_weights: str | None = "imagenet"
) -> smp.Segformer:
    """Build SegFormer B3 with one full-resolution foreground logit.

    Pass ``encoder_weights=None`` for offline tests. ImageNet initialization
    uses SMP's first-convolution adaptation: RGB weights repeat cyclically and
    are scaled by 3 / in_channels for four/eight inputs. Three inputs retain
    the original RGB weights. This adaptation is positional, not a learned
    physical-band mapping; the loader owns the recorded physical band order.
    """
    if type(in_channels) is not int or in_channels not in (3, 4, 8):
        raise ValueError("SegFormer B3 requires 3, 4, or 8 input bands.")
    if encoder_weights not in (None, "imagenet"):
        raise ValueError("encoder_weights must be 'imagenet' or None (offline).")
    return smp.Segformer(
        encoder_name="mit_b3",
        encoder_weights=encoder_weights,
        in_channels=in_channels,
        classes=1,
        activation=None,
    )
