"""
Script to sort and merge ECE109 quizzes into a unified structure.

Current structure: Quizzes-{Season}-{Year}/Quiz{X}/Quiz{X}.{1,2,3}.pdf
Target structure:  Quizzes/Quiz {X}/quiz_{x}_{year}_{season}.pdf

This script creates copies - original files are not modified.
"""

import os
import re
from pathlib import Path
from PyPDF2 import PdfMerger

# Configuration
WORKSPACE_DIR = Path(__file__).parent
OUTPUT_DIR = WORKSPACE_DIR / "Quizzes"

# Patterns to match semester folders
SEMESTER_PATTERNS = [
    # Quizzes-Fall-2021, Quizzes-Winter-2022, Quizzes-Spring-2021
    r"Quizzes-(\w+)-(\d{4})",
    # Quizzes-Fall2024 (no hyphen before year)
    r"Quizzes-(\w+)(\d{4})",
]


def parse_semester_folder(folder_name: str) -> tuple[str, str] | None:
    """
    Extract season and year from a semester folder name.
    Returns (season, year) or None if not a semester folder.
    """
    for pattern in SEMESTER_PATTERNS:
        match = re.match(pattern, folder_name)
        if match:
            season, year = match.groups()
            return season.lower(), year
    return None


def find_quiz_folders(semester_path: Path) -> list[tuple[int, Path]]:
    """
    Find all quiz folders in a semester directory.
    Handles both 'Quiz1' and 'Q1' naming conventions.
    Returns list of (quiz_number, folder_path).
    """
    quiz_folders = []
    
    for item in semester_path.iterdir():
        if not item.is_dir():
            continue
        
        # Match 'Quiz1', 'Quiz2', etc.
        match = re.match(r"Quiz(\d+)", item.name, re.IGNORECASE)
        if match:
            quiz_folders.append((int(match.group(1)), item))
            continue
        
        # Match 'Q1', 'Q2', etc. (Spring 2021 format)
        match = re.match(r"Q(\d+)$", item.name, re.IGNORECASE)
        if match:
            quiz_folders.append((int(match.group(1)), item))
    
    return sorted(quiz_folders, key=lambda x: x[0])


def find_quiz_parts(quiz_folder: Path, quiz_num: int) -> list[Path]:
    """
    Find the 3 PDF parts for a quiz in order (.1, .2, .3).
    Handles both dot (Quiz1.1.pdf) and comma (Quiz6,1.pdf) separators.
    """
    parts = []
    
    for part_num in [1, 2, 3]:
        # Try different naming patterns
        patterns = [
            f"Quiz{quiz_num}.{part_num}.pdf",   # Quiz1.1.pdf
            f"Quiz{quiz_num},{part_num}.pdf",   # Quiz6,1.pdf (Fall 2021 Quiz 6)
        ]
        
        found = False
        for pattern in patterns:
            pdf_path = quiz_folder / pattern
            if pdf_path.exists():
                parts.append(pdf_path)
                found = True
                break
        
        if not found:
            # Try case-insensitive search as fallback
            for file in quiz_folder.iterdir():
                if file.suffix.lower() == ".pdf":
                    # Check if file matches pattern loosely
                    if re.match(rf"Quiz{quiz_num}[.,]{part_num}\.pdf", file.name, re.IGNORECASE):
                        parts.append(file)
                        found = True
                        break
        
        if not found:
            print(f"  Warning: Could not find part {part_num} in {quiz_folder}")
    
    return parts


def merge_pdfs(pdf_paths: list[Path], output_path: Path) -> bool:
    """
    Merge multiple PDFs into a single file.
    Returns True on success, False on failure.
    """
    if not pdf_paths:
        return False
    
    try:
        merger = PdfMerger()
        
        for pdf_path in pdf_paths:
            merger.append(str(pdf_path))
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        merger.write(str(output_path))
        merger.close()
        return True
    
    except Exception as e:
        print(f"  Error merging PDFs: {e}")
        return False


def main():
    print("=" * 60)
    print("ECE109 Quiz Sorter and Merger")
    print("=" * 60)
    print(f"\nWorkspace: {WORKSPACE_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    # Find all semester folders
    semester_folders = []
    for item in WORKSPACE_DIR.iterdir():
        if item.is_dir():
            parsed = parse_semester_folder(item.name)
            if parsed:
                season, year = parsed
                semester_folders.append((season, year, item))
    
    if not semester_folders:
        print("No semester folders found!")
        return
    
    # Sort by year, then season
    season_order = {"winter": 0, "spring": 1, "fall": 2}
    semester_folders.sort(key=lambda x: (x[1], season_order.get(x[0], 3)))
    
    print(f"Found {len(semester_folders)} semester folders:")
    for season, year, path in semester_folders:
        print(f"  - {path.name} ({season.capitalize()} {year})")
    print()
    
    # Process each semester
    total_merged = 0
    total_errors = 0
    
    for season, year, semester_path in semester_folders:
        print(f"\nProcessing {semester_path.name}...")
        
        quiz_folders = find_quiz_folders(semester_path)
        
        for quiz_num, quiz_folder in quiz_folders:
            # Find the 3 PDF parts
            parts = find_quiz_parts(quiz_folder, quiz_num)
            
            if len(parts) != 3:
                print(f"  Quiz {quiz_num}: Found {len(parts)}/3 parts - skipping")
                total_errors += 1
                continue
            
            # Create output path: Quizzes/Quiz X/quiz_x_year_season.pdf
            output_folder = OUTPUT_DIR / f"Quiz {quiz_num}"
            output_filename = f"quiz_{quiz_num}_{year}_{season}.pdf"
            output_path = output_folder / output_filename
            
            # Merge PDFs
            if merge_pdfs(parts, output_path):
                print(f"  Quiz {quiz_num}: Merged -> {output_filename}")
                total_merged += 1
            else:
                print(f"  Quiz {quiz_num}: Failed to merge")
                total_errors += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Successfully merged: {total_merged} quizzes")
    print(f"Errors: {total_errors}")
    print(f"\nOutput location: {OUTPUT_DIR}")
    
    if total_merged > 0:
        print("\nCreated folders:")
        for folder in sorted(OUTPUT_DIR.iterdir()):
            if folder.is_dir():
                file_count = len(list(folder.glob("*.pdf")))
                print(f"  {folder.name}: {file_count} files")


if __name__ == "__main__":
    main()
