"""Expert definition loading with platform-specific override support.

Agent definitions are NOT auto-discovered from the PAF repo.
The host application provides search directories at runtime via the
agents_dirs parameter. The repo's agents/ folder contains only
skeletons (_skeleton/) and samples (sample/) for reference.
"""

import json
import os
from typing import Optional


def _read_text(path: str) -> str:
    """Read a text file, return empty string if missing."""
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def _walk_expert_dirs(agents_dirs: list[str]) -> list[tuple[str, str]]:
    """Recursively find all agent directories containing expert.json.

    Skips directories whose name starts with '_' (skeletons/templates).
    Returns list of (expert_id, absolute_path) tuples.
    """
    results = []
    for base_dir in agents_dirs:
        if not os.path.isdir(base_dir):
            continue
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if not d.startswith("_")]
            if "expert.json" in files:
                expert_id = os.path.basename(root)
                results.append((expert_id, root))
    return sorted(results, key=lambda x: x[0])


def list_experts(agents_dirs: list[str]) -> list[dict]:
    """Return list of expert metadata dicts from given agent directories.

    Args:
        agents_dirs: List of directory paths to search for agent definitions.
    """
    experts = []
    for _, path in _walk_expert_dirs(agents_dirs):
        meta_path = os.path.join(path, "expert.json")
        with open(meta_path, encoding="utf-8") as f:
            experts.append(json.load(f))
    return experts


def get_expert_dir(expert_id: str, agents_dirs: list[str]) -> Optional[str]:
    """Return absolute path to an expert directory, or None if not found.

    Args:
        expert_id: Expert identifier (directory name).
        agents_dirs: List of directory paths to search.
    """
    for eid, path in _walk_expert_dirs(agents_dirs):
        if eid == expert_id:
            return path
    return None


def load_expert(expert_id: str, agents_dirs: list[str],
                platform_dir: Optional[str] = None) -> dict:
    """Load expert files with platform-specific override support.

    Resolution order for each file (IDENTITY.md, SOUL.md, MEMORY.md):
      1. platform_dir/agents/{expert_id}/{file}  (platform-specific override)
      2. agents/{expert_id}/{file}                (shared default)

    Args:
        expert_id: Expert identifier (directory name).
        agents_dirs: List of directory paths to search for agent definitions.
        platform_dir: Optional absolute path to a platform directory.
                      If provided, platform-specific overrides are checked first.

    Returns:
        Dict with keys: id, identity, soul, memory, metadata.
    """
    shared_dir = get_expert_dir(expert_id, agents_dirs)
    if not shared_dir:
        raise FileNotFoundError(
            f"Expert '{expert_id}' not found in: {agents_dirs}"
        )

    # Load metadata from shared expert dir (always authoritative)
    meta_path = os.path.join(shared_dir, "expert.json")
    metadata = {}
    if os.path.isfile(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            metadata = json.load(f)

    # Resolve each file with platform override fallback
    def _resolve(filename: str) -> str:
        if platform_dir:
            override = os.path.join(platform_dir, "agents", expert_id, filename)
            if os.path.isfile(override):
                return _read_text(override)
        return _read_text(os.path.join(shared_dir, filename))

    return {
        "id": expert_id,
        "identity": _resolve("IDENTITY.md"),
        "soul": _resolve("SOUL.md"),
        "memory": _resolve("MEMORY.md"),
        "metadata": metadata,
    }
