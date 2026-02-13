VALIDATION_MODES = {"current", "past"}


def ensure_validation_mode(validation_mode: str) -> None:
    if validation_mode not in VALIDATION_MODES:
        raise ValueError(f"validation_mode must be one of {sorted(VALIDATION_MODES)}")
