"""Helper module to handle missing dependencies and installation."""

invalid: bool = True
"""Flag for missing dependencies."""
promptRestart: bool = False
"""Flag for succesful installation requiring further restart."""
promptFailed: bool = False
"""Flag for failed installation, probably needing further admin access."""