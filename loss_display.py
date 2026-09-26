"""Presentation only: never treat a positive rounded-zero loss as exact zero."""


def format_points_loss(value):
    value = float(value)
    text = f"{value:.2f}"
    return "<0.01" if value > 0.0 and text == "0.00" else text
