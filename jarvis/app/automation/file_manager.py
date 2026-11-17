"""
File Explorer and File System Controller for NIVA.
Handles file/folder creation, search, movement, reading (.txt, .docx, .pdf, .xlsx),
organization, and verification of outcomes.
"""

import glob
import logging
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

from app.safety.validation import PathValidator

logger = logging.getLogger("NIVA.FileManager")


class FileManager:
    """Provides safe, verifiable Windows filesystem management."""

    # Standard directory mappings
    WELL_KNOWN_DIRS = {
        "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
        "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
        "music": os.path.join(os.path.expanduser("~"), "Music"),
        "videos": os.path.join(os.path.expanduser("~"), "Videos"),
    }

    @classmethod
    def resolve_path(cls, path_str: str) -> str:
        """Expands environment variables, user home, and well-known folder aliases."""
        p = path_str.strip()
        # Check alias prefixes
        parts = p.split(os.sep) if os.sep in p else p.split("/")
        first_segment = parts[0].lower().replace(":", "")

        if first_segment in cls.WELL_KNOWN_DIRS:
            base = cls.WELL_KNOWN_DIRS[first_segment]
            if len(parts) > 1:
                return os.path.normpath(os.path.join(base, *parts[1:]))
            return base

        # Handle ~ or %USERPROFILE%
        expanded = os.path.expanduser(os.path.expandvars(p))
        return os.path.normpath(expanded)

    @classmethod
    def create_folder(cls, path: str) -> Dict[str, Any]:
        """Creates a directory and verifies its existence."""
        target = cls.resolve_path(path)
        is_safe, reason = PathValidator.is_safe_path(target, for_writing=True)
        if not is_safe:
            return {"success": False, "error": reason}

        try:
            os.makedirs(target, exist_ok=True)
            # Verification
            if os.path.exists(target) and os.path.isdir(target):
                return {
                    "success": True,
                    "message": f"Successfully created folder: {target}",
                    "path": target
                }
            return {"success": False, "error": f"Folder creation command issued but folder not found: {target}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to create folder: {str(e)}"}

    @classmethod
    def create_file(cls, path: str, content: str = "") -> Dict[str, Any]:
        """Creates a file with the given content and verifies."""
        target = cls.resolve_path(path)
        is_safe, reason = PathValidator.is_safe_path(target, for_writing=True)
        if not is_safe:
            return {"success": False, "error": reason}

        try:
            parent = os.path.dirname(target)
            if parent:
                os.makedirs(parent, exist_ok=True)

            with open(target, "w", encoding="utf-8") as f:
                f.write(content)

            # Verification
            if os.path.exists(target):
                return {
                    "success": True,
                    "message": f"Successfully created file: {target} ({len(content)} characters)",
                    "path": target,
                    "size_bytes": os.path.getsize(target)
                }
            return {"success": False, "error": f"File could not be verified after writing: {target}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to create file: {str(e)}"}

    @classmethod
    def read_file(cls, path: str, max_lines: int = 200) -> Dict[str, Any]:
        """Reads document contents across supported formats (.txt, .docx, .pdf, .xlsx)."""
        target = cls.resolve_path(path)
        if not os.path.exists(target):
            return {"success": False, "error": f"File does not exist: {target}"}

        ext = os.path.splitext(target)[1].lower()

        try:
            # 1. Plain text / code
            if ext in [".txt", ".md", ".json", ".py", ".csv", ".log", ".html", ".bat"]:
                with open(target, "r", encoding="utf-8", errors="replace") as f:
                    lines = [f.readline() for _ in range(max_lines)]
                    content = "".join(lines)
                return {"success": True, "content": content, "format": "text", "path": target}

            # 2. Microsoft Word .docx
            elif ext == ".docx":
                import docx
                doc = docx.Document(target)
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                text = "\n".join(paragraphs[:max_lines])
                return {"success": True, "content": text, "format": "docx", "path": target}

            # 3. PDF
            elif ext == ".pdf":
                import pypdf
                reader = pypdf.PdfReader(target)
                pages_text = []
                for i in range(min(15, len(reader.pages))):
                    text = reader.pages[i].extract_text() or ""
                    if text:
                        pages_text.append(text)
                return {"success": True, "content": "\n--- PAGE ---\n".join(pages_text), "format": "pdf", "path": target}

            # 4. Excel .xlsx
            elif ext in [".xlsx", ".xls"]:
                import openpyxl
                wb = openpyxl.load_workbook(target, data_only=True)
                sheet = wb.active
                rows_data = []
                for r in list(sheet.iter_rows(values_only=True))[:max_lines]:
                    rows_data.append([str(c) if c is not None else "" for c in r])
                wb.close()
                return {"success": True, "content": rows_data, "format": "xlsx", "path": target}

            else:
                return {"success": False, "error": f"Unsupported document format: {ext}"}

        except Exception as e:
            return {"success": False, "error": f"Failed reading file '{target}': {str(e)}"}

    @classmethod
    def move_file(cls, source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
        """Moves a file and verifies."""
        src = cls.resolve_path(source)
        dst = cls.resolve_path(destination)

        if not os.path.exists(src):
            return {"success": False, "error": f"Source does not exist: {src}"}

        try:
            if os.path.isdir(dst):
                dst = os.path.join(dst, os.path.basename(src))

            if os.path.exists(dst) and not overwrite:
                return {"success": False, "error": f"Destination already exists: {dst}"}

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)

            if os.path.exists(dst):
                return {"success": True, "message": f"Successfully moved '{src}' to '{dst}'", "source": src, "destination": dst}
            return {"success": False, "error": "Move completed but destination could not be verified."}
        except Exception as e:
            return {"success": False, "error": f"Move failed: {str(e)}"}

    @classmethod
    def copy_file(cls, source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
        """Copies a file and verifies."""
        src = cls.resolve_path(source)
        dst = cls.resolve_path(destination)

        if not os.path.exists(src):
            return {"success": False, "error": f"Source does not exist: {src}"}

        try:
            if os.path.isdir(dst):
                dst = os.path.join(dst, os.path.basename(src))

            if os.path.exists(dst) and not overwrite:
                return {"success": False, "error": f"Destination already exists: {dst}"}

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(src, dst)

            if os.path.exists(dst):
                return {"success": True, "message": f"Successfully copied '{src}' to '{dst}'", "source": src, "destination": dst}
            return {"success": False, "error": "Copy completed but destination could not be verified."}
        except Exception as e:
            return {"success": False, "error": f"Copy failed: {str(e)}"}

    @classmethod
    def delete_file(cls, path: str, permanent: bool = False) -> Dict[str, Any]:
        """Deletes a file or directory with safety verification."""
        target = cls.resolve_path(path)
        if not os.path.exists(target):
            return {"success": False, "error": f"File or folder does not exist: {target}"}

        is_safe, reason = PathValidator.is_safe_path(target, for_writing=True)
        if not is_safe:
            return {"success": False, "error": f"Security restriction: {reason}"}

        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)

            if not os.path.exists(target):
                return {"success": True, "message": f"Successfully deleted: {target}", "path": target}
            return {"success": False, "error": f"Delete command issued but target still exists: {target}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to delete '{target}': {str(e)}"}

    @classmethod
    def search_files(cls, directory: str = "Desktop", pattern: str = "*.*", recursive: bool = True) -> Dict[str, Any]:
        """Searches files by name/wildcard in target directory."""
        dir_path = cls.resolve_path(directory)
        if not os.path.exists(dir_path):
            return {"success": False, "error": f"Directory not found: {dir_path}"}

        try:
            search_str = os.path.join(dir_path, "**" if recursive else "", pattern)
            matches = glob.glob(search_str, recursive=recursive)
            file_results = [m for m in matches if os.path.isfile(m)][:50]

            return {
                "success": True,
                "count": len(file_results),
                "files": file_results,
                "directory": dir_path,
                "pattern": pattern
            }
        except Exception as e:
            return {"success": False, "error": f"Search failed: {str(e)}"}

    @classmethod
    def organize_folder(cls, directory: str = "Downloads", dry_run: bool = False) -> Dict[str, Any]:
        """
        Organizes files into categorized subfolders:
        Documents, Images, Audio, Video, Archives, Code, Other.
        """
        target_dir = cls.resolve_path(directory)
        if not os.path.exists(target_dir):
            return {"success": False, "error": f"Directory not found: {target_dir}"}

        category_map = {
            "Documents": [".pdf", ".docx", ".doc", ".xlsx", ".pptx", ".txt", ".csv", ".rtf"],
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"],
            "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg"],
            "Video": [".mp4", ".mkv", ".mov", ".avi", ".wmv"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".json"],
        }

        ext_to_cat = {}
        for cat, exts in category_map.items():
            for ext in exts:
                ext_to_cat[ext] = cat

        moved_summary: Dict[str, int] = {cat: 0 for cat in category_map}
        moved_summary["Other"] = 0

        for item in os.listdir(target_dir):
            item_path = os.path.join(target_dir, item)
            if os.path.isdir(item_path):
                continue

            ext = os.path.splitext(item)[1].lower()
            category = ext_to_cat.get(ext, "Other")
            dest_dir = os.path.join(target_dir, category)

            if not dry_run:
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, item)
                try:
                    shutil.move(item_path, dest_path)
                    moved_summary[category] += 1
                except Exception as e:
                    logger.warning(f"Could not move {item}: {e}")
            else:
                moved_summary[category] += 1

        total_moved = sum(moved_summary.values())
        return {
            "success": True,
            "message": f"Organized {total_moved} files in {target_dir}",
            "breakdown": moved_summary,
            "dry_run": dry_run
        }
