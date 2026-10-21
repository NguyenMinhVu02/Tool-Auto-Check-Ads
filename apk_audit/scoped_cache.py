"""Reuse a rule's verdict across builds when the code it actually looked at is unchanged.

The normal verdict cache is keyed by the whole APK, so any rebuild reruns every rule.
Here a PASS/FAIL verdict is also indexed by the files the AI read or searched. A later
build may reuse it only if all of these still hold:
  * same rule, pack, engine identity, policy and the rule's scoped documents/inventory;
  * the set of decompiled file paths is identical (a new/removed file could change a
    "not found" conclusion);
  * every file or directory the AI touched has identical content;
  * the evidence still verifies against the new sources (done by the caller).
Anything the dependency list cannot describe (workspace-wide search, truncated command,
glob, unknown path) disables reuse for that verdict. Edits to files the AI never read
cannot be detected; see the README for this limit.
"""
import hashlib
from pathlib import Path
import re

from .utils import digest_json, write_json

MAX_DIR_FILES = 5000
TOKEN = re.compile(r"(?<![\w.-])((?:sources|resources)(?:/[^\s'\"|;:,)\]}>]*)?)")
BENIGN = re.compile(r"^\s*(?:(?:/bin/bash -lc\s+)?['\"]?\s*(?:pwd|echo)\b|StructuredOutput\b)")
TRUNCATED = 1000  # retain_source_read keeps at most this many characters of a command


def tree_digest(workspace, files):
    root = Path(workspace).resolve()
    return digest_json(sorted(Path(path).resolve().relative_to(root).as_posix() for path in files))


def _file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dir_hash(root, directory):
    files = sorted(p for p in directory.rglob('*') if p.is_file() and not p.is_symlink())
    if len(files) > MAX_DIR_FILES:
        return None
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(_file_hash(path).encode())
    return digest.hexdigest()


def _glob_hash(root, pattern):
    if '..' in Path(pattern).parts:
        return None
    matches = sorted(p for p in root.glob(pattern) if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root))
    if len(matches) > MAX_DIR_FILES:
        return None
    digest = hashlib.sha256()
    for path in matches:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(_file_hash(path).encode())
    return digest.hexdigest()


def dependency_paths(finding, trace):
    """Workspace-relative files/dirs the verdict depends on, or None if they cannot be listed."""
    paths = {item.get('file') for item in finding.evidence if isinstance(item, dict) and item.get('file')}
    attempts = trace.get('attempts') or []
    if not attempts:
        return None
    for attempt in attempts:
        if attempt.get('error') or attempt.get('exhausted_budget'):
            return None
        for event in attempt.get('events') or []:
            if event.get('type') != 'source_read':
                continue
            command = str(event.get('command') or '')
            if BENIGN.match(command):
                continue
            if len(command) >= TRUNCATED:
                return None
            tokens = TOKEN.findall(command)
            if not tokens:
                return None
            paths.update(token.rstrip('/') for token in tokens)
    return sorted(paths) or None


def hash_dependencies(workspace, paths):
    root = Path(workspace).resolve()
    hashes = {}
    for relative in paths:
        if any(char in relative for char in '*?['):
            value = _glob_hash(root, relative)
            if value is None:
                return None
            hashes[relative] = 'glob:' + value
            continue
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            return None
        if target.is_file():
            hashes[relative] = _file_hash(target)
        elif target.is_dir():
            value = _dir_hash(root, target)
            if value is None:
                return None
            hashes[relative] = 'dir:' + value
        else:
            return None  # glob, typo or removed path: not describable
    return hashes


def scoped_key(pack, rule, engine, identity, policy, scoped_docs, scoped_inventory):
    from dataclasses import asdict
    return digest_json({'tool': 'scoped-v1', 'pack': [pack.name, pack.context, pack.extract],
                        'rule': asdict(rule), 'engine': engine, 'identity': identity, 'policy': policy,
                        'documents': scoped_docs, 'inventory': scoped_inventory})


class ScopedIndex:
    def __init__(self, directory):
        self.root = Path(directory) / 'verdicts' / 'scoped'

    def put(self, skey, main_key, dependencies, tree):
        write_json(self.root / (skey + '.json'), {'main_key': main_key, 'tree': tree, 'dependencies': dependencies})

    def find(self, skey, workspace, tree):
        import json
        try:
            record = json.loads((self.root / (skey + '.json')).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
        if not isinstance(record, dict) or record.get('tree') != tree or not isinstance(record.get('dependencies'), dict):
            return None
        current = hash_dependencies(workspace, sorted(record['dependencies']))
        if current != record['dependencies']:
            return None
        return record.get('main_key')
