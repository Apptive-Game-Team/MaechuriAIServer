import os
import re
import json

# Set the directory path (current directory if placed in the target folder)
dir_path = os.path.dirname(os.path.abspath(__file__))

def rename_files():
    files = os.listdir(dir_path)

    # UUID pattern (36 characters with hyphens)
    uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

    # Identify prefixes from files ending with _case_state.json
    # This identifies the original UUIDs or system-generated IDs
    prefixes = [f.replace("_case_state.json", "") for f in files if (uuid_pattern.match(f) or f.startswith("test_generation_")) and f.endswith("_case_state.json")]

    for prefix in prefixes:
        group_files = [f for f in files if f.startswith(prefix + "_")]
        
        title = None
        
        # 1. Try to find the title from case_state.json
        case_state_file = f"{prefix}_case_state.json"
        if case_state_file in group_files:
            full_path = os.path.join(dir_path, case_state_file)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Match title with or without markdown bold symbols
                    match = re.search(r"(?:\*\*?)?제목:\s*(.+?)(?:\*\*?)?$", content, re.MULTILINE)
                    if match:
                        title = match.group(1).strip()
            except Exception as e:
                print(f"Error reading {case_state_file}: {e}")

        # 2. If title not found, check skeleton_result.json
        if not title:
            skeleton_file = f"{prefix}_skeleton_result.json"
            if skeleton_file in group_files:
                full_path = os.path.join(dir_path, skeleton_file)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        summary = data.get("incident", {}).get("summary", "")
                        match = re.search(r"제목:\s*(.+)", summary)
                        if match:
                            title = match.group(1).strip()
                except Exception as e:
                    print(f"Error reading {skeleton_file}: {e}")

        if title:
            # Sanitize title for filename
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
            print(f"Prefix {prefix} -> Title: {safe_title}")
            
            for file in group_files:
                # Replace the prefix with the title
                new_name = file.replace(prefix + "_", safe_title + "_", 1)
                old_path = os.path.join(dir_path, file)
                new_path = os.path.join(dir_path, new_name)
                
                if old_path != new_path:
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
        else:
            print(f"Could not find title for prefix {prefix}")

if __name__ == "__main__":
    rename_files()
    print("Done.")
