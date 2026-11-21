#!/usr/bin/env python3
"""Validate Agent Skills metadata, Codex UI metadata and linked skill resources.

Requires requirements-dev.txt. Checks packaging, not agent behavior or every
host-specific interpretation of the Agent Skills specification.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("Install validation dependencies: python3 -m pip install -r requirements-dev.txt")


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys instead of silently discarding earlier values."""


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str):
            raise ValueError("YAML mapping keys must be strings")
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def text_field(obj, key, limit, required=False):
    value = obj.get(key)
    if value is None and not required and key not in obj:
        return
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{key}: expected non-empty string, maximum {limit} characters")


def validate_skill(root):
    root = Path(root).resolve()
    content = (root / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", content, re.S)
    if not match:
        raise ValueError("SKILL.md: missing YAML frontmatter")
    metadata = yaml.load(match.group(1), Loader=UniqueLoader)
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must be a mapping")
    allowed = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    if set(metadata) - allowed:
        raise ValueError("unsupported frontmatter fields")
    text_field(metadata, "name", 64, required=True)
    name = metadata["name"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or name != root.name:
        raise ValueError("name must be valid kebab-case and match the installed directory")
    text_field(metadata, "description", 1024, required=True)
    for field, limit in (("compatibility", 500), ("license", 1024), ("allowed-tools", 4096)):
        text_field(metadata, field, limit)
    if "metadata" in metadata:
        extra = metadata["metadata"]
        if not isinstance(extra, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                             for k, v in extra.items()):
            raise ValueError("metadata must map string keys to string values")
    if not content[match.end():].strip():
        raise ValueError("SKILL.md body is empty")
    for relative in set(re.findall(r"(?:references|scripts)/[A-Za-z0-9_./-]+\.(?:md|py)", content)):
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"missing or escaping skill reference: {relative}")
    config = yaml.load((root / "agents/openai.yaml").read_text(encoding="utf-8"), Loader=UniqueLoader)
    if not isinstance(config, dict) or not isinstance(config.get("interface"), dict):
        raise ValueError("agents/openai.yaml: interface must be a mapping")
    interface = config["interface"]
    text_field(interface, "display_name", 128, required=True)
    text_field(interface, "short_description", 64, required=True)
    if len(interface["short_description"]) < 25:
        raise ValueError("short_description must be 25–64 characters")
    text_field(interface, "default_prompt", 2048, required=True)
    if f"${name}" not in interface["default_prompt"]:
        raise ValueError("default_prompt must mention the skill as $skill-name")
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        validate_skill(args.directory)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print("VALID: Agent Skills metadata, Codex UI metadata, and skill references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
