"""Cache only when the configured engine identity is reproducible."""
import shutil
import subprocess


def cli_version(binary):
    path = shutil.which(binary)
    if not path:
        return None
    try:
        result = subprocess.run([path,'--version'],capture_output=True,text=True,timeout=10)
        return result.stdout.strip()[:200] if result.returncode == 0 else None
    except (OSError,subprocess.SubprocessError):
        return None


def engine_identity(engine):
    explicit = getattr(engine,'cache_identity',None)
    if isinstance(explicit,dict):
        return explicit,True
    native = bool(getattr(engine,'requires_claims',False)) and engine.name.split(':')[0] in {'codex','claude'}
    if not native:
        return {'engine':engine.name,'mode':'legacy'},True
    provider = engine.name.split(':')[0]
    model = getattr(engine,'model',None)
    version = cli_version(provider)
    return {'engine':engine.name,'model':model,'reasoning_effort':getattr(engine,'reasoning_effort',None),
            'cli_version':version},bool(model and version)
