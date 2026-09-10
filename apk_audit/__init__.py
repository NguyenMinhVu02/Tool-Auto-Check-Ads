"""APK audit framework; business rules are supplied externally."""
__version__ = "0.1.0"

def run(target, **kwargs):
    from .pipeline import run as pipeline_run
    return pipeline_run(target, **kwargs)
