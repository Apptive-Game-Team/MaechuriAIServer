import os
import re
import json

# Set the directory path (current directory if placed in the target folder)
dir_path = os.path.dirname(os.path.abspath(__file__))

# UUID pattern (36 characters with hyphens)
_UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _get_prefixes(files: list[str]) -> list[str]:
    """Return prefixes derived from *_case_state.json files whose names match a
    UUID or a test-generation pattern."""
    return [
        f.replace("_case_state.json", "")
        for f in files
        if (_UUID_PATTERN.match(f) or f.startswith("test_generation_"))
        and f.endswith("_case_state.json")
    ]


def _extract_title_from_case_state(prefix: str, group_files: list[str]) -> str | None:
    """Try to extract the scenario title from *_case_state.json."""
    case_state_file = f"{prefix}_case_state.json"
    if case_state_file not in group_files:
        return None
    full_path = os.path.join(dir_path, case_state_file)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Match title with or without markdown bold symbols
        match = re.search(r"(?:\*\*?)?제목:\s*(.+?)(?:\*\*?)?$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"Error reading {case_state_file}: {e}")
    return None


def _extract_title_from_skeleton(prefix: str, group_files: list[str]) -> str | None:
    """Try to extract the scenario title from *_skeleton_result.json."""
    skeleton_file = f"{prefix}_skeleton_result.json"
    if skeleton_file not in group_files:
        return None
    full_path = os.path.join(dir_path, skeleton_file)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        summary = data.get("incident", {}).get("summary", "")
        match = re.search(r"제목:\s*(.+)", summary)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"Error reading {skeleton_file}: {e}")
    return None


def _resolve_title(prefix: str, group_files: list[str]) -> str | None:
    """Return the scenario title by checking case_state first, then skeleton."""
    return (
        _extract_title_from_case_state(prefix, group_files)
        or _extract_title_from_skeleton(prefix, group_files)
    )


def _rename_group_files(prefix: str, group_files: list[str], safe_title: str) -> None:
    """Rename all files in *group_files* by replacing *prefix* with *safe_title*."""
    print(f"Prefix {prefix} -> Title: {safe_title}")
    for file in group_files:
        new_name = file.replace(prefix + "_", safe_title + "_", 1)
        old_path = os.path.join(dir_path, file)
        new_path = os.path.join(dir_path, new_name)

        if old_path == new_path:
            continue

        # Handle potential naming conflicts
        if os.path.exists(new_path):
            short_prefix = prefix[:4]
            new_name = file.replace(prefix + "_", f"{safe_title}_{short_prefix}_", 1)
            new_path = os.path.join(dir_path, new_name)

        print(f"Renaming {file} to {new_name}")
        try:
            os.rename(old_path, new_path)
        except Exception as e:
            print(f"Failed to rename {file}: {e}")


def rename_files() -> None:
    files = os.listdir(dir_path)
    prefixes = _get_prefixes(files)

    for prefix in prefixes:
        group_files = [f for f in files if f.startswith(prefix + "_")]
        title = _resolve_title(prefix, group_files)

        if title:
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
            _rename_group_files(prefix, group_files, safe_title)
        else:
            print(f"Could not find title for prefix {prefix}")


if __name__ == "__main__":
    rename_files()
    print("Done.")
