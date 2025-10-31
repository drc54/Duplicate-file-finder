#!/usr/bin/env python3
"""
Duplicate File Finder
Scans the current directory and all subdirectories to find duplicate files.
Provides interactive management to move duplicates to a deletion directory.
"""

import os
import hashlib
import shutil
import platform
from collections import defaultdict
from datetime import datetime


def get_file_hash(filepath):
    """
    Calculate MD5 hash of a file to determine duplicates.
    
    Args:
        filepath: Path to the file to hash
        
    Returns:
        MD5 hash string or None if file cannot be read
    """
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (IOError, OSError, PermissionError) as e:
        # Silently skip files that can't be read (common with cache files)
        return None


def format_size(size_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.23 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def clear_screen():
    """
    Clear the terminal screen in a cross-platform way.
    """
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')


def find_duplicates(root_dir="."):
    """
    Find all duplicate files starting from root_dir.
    Skips the to_be_deleted directory to avoid scanning files marked for deletion.
    
    Args:
        root_dir: Starting directory for the scan
        
    Returns:
        Dictionary mapping (file_size, file_hash) to lists of file paths
    """
    # Dictionary to store file hashes and their paths
    # Key: (file_size, file_hash), Value: list of file paths
    files_by_size = defaultdict(list)
    files_by_hash = defaultdict(list)
    skipped_files = []
    
    # Compute absolute path of the deletion directory
    deletion_dir_abs = os.path.abspath(os.path.join(os.getcwd(), 'to_be_deleted'))
    
    print("Scanning files...")
    
    # First pass: group files by size (faster than hashing everything)
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Remove 'to_be_deleted' from dirnames to prevent descending into it
        if 'to_be_deleted' in dirnames:
            dirnames.remove('to_be_deleted')
        
        # Get absolute path of current directory
        dirpath_abs = os.path.abspath(dirpath)
        
        # Skip if this directory is inside the deletion directory
        try:
            # Use commonpath to check if dirpath is under deletion_dir
            if os.path.commonpath([dirpath_abs, deletion_dir_abs]) == deletion_dir_abs:
                continue
        except ValueError:
            # On Windows, paths on different drives raise ValueError
            # Fall back to string comparison
            if dirpath_abs.startswith(deletion_dir_abs):
                continue
        
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            filepath_abs = os.path.abspath(filepath)
            
            # Skip if this file is inside the deletion directory
            try:
                if os.path.commonpath([filepath_abs, deletion_dir_abs]) == deletion_dir_abs:
                    continue
            except ValueError:
                # On Windows, paths on different drives raise ValueError
                if filepath_abs.startswith(deletion_dir_abs):
                    continue
            
            try:
                # Get file size
                file_size = os.path.getsize(filepath)
                
                # Group by size first (optimization)
                files_by_size[file_size].append(filepath)
                
            except (OSError, IOError, PermissionError) as e:
                # Track skipped files without cluttering output
                skipped_files.append((filepath, str(e)))
                continue
    
    # Report skipped files if any
    if skipped_files:
        print(f"\nSkipped {len(skipped_files)} file(s) due to access errors")
    
    print("\nCalculating file hashes for potential duplicates...")
    
    # Second pass: only hash files that have the same size
    for file_size, filepaths in files_by_size.items():
        if len(filepaths) > 1:  # Only hash if there are multiple files with same size
            for filepath in filepaths:
                file_hash = get_file_hash(filepath)
                if file_hash:
                    # Use both size and hash as key for extra safety
                    files_by_hash[(file_size, file_hash)].append(filepath)
    
    # Filter to only keep actual duplicates (more than one file with same hash)
    duplicates = {key: paths for key, paths in files_by_hash.items() if len(paths) > 1}
    
    return duplicates


def group_duplicates_by_directory(duplicates):
    """
    Group duplicate files by their parent directory.
    
    Args:
        duplicates: Dictionary mapping (size, hash) to file paths
        
    Returns:
        Dictionary mapping directories to lists of duplicate groups
    """
    dir_duplicates = defaultdict(list)
    
    for (file_size, file_hash), filepaths in duplicates.items():
        # Get all directories that contain these duplicates
        directories = set(os.path.dirname(os.path.abspath(fp)) for fp in filepaths)
        
        for directory in directories:
            # Find files in this directory
            files_in_dir = [fp for fp in filepaths if os.path.dirname(os.path.abspath(fp)) == directory]
            if files_in_dir:
                dir_duplicates[directory].append({
                    'size': file_size,
                    'hash': file_hash,
                    'files': filepaths,
                    'files_in_dir': files_in_dir
                })
    
    return dir_duplicates


def move_file_to_deletion(filepath, deletion_dir):
    """
    Move a file to the deletion directory with filename conflict handling.
    
    Args:
        filepath: Path to the file to move
        deletion_dir: Destination directory path
        
    Returns:
        Tuple of (success: bool, destination_path: str or None)
    """
    try:
        # Create deletion directory if it doesn't exist
        os.makedirs(deletion_dir, exist_ok=True)
        
        # Get filename
        filename = os.path.basename(filepath)
        destination = os.path.join(deletion_dir, filename)
        
        # Handle filename conflicts by appending _N counter
        counter = 1
        base_name, ext = os.path.splitext(filename)
        while os.path.exists(destination):
            new_filename = f"{base_name}_{counter}{ext}"
            destination = os.path.join(deletion_dir, new_filename)
            counter += 1
        
        # Use shutil.move for safe file moving
        shutil.move(filepath, destination)
        return (True, destination)
        
    except (OSError, IOError, PermissionError) as e:
        print(f"Error moving file {filepath}: {e}")
        return (False, None)


def manage_duplicates(duplicates):
    """
    Interactively manage duplicate files, allowing user to select which to move.
    Supports optional screen clearing and pausing between groups.
    
    Args:
        duplicates: Dictionary mapping (size, hash) to file paths
        
    Returns:
        List of tuples (original_path, destination_path) for moved files
    """
    if not duplicates:
        print("\nNo duplicate files found!")
        return []
    
    # Prompt user for preferences
    print("\n" + "=" * 80)
    print("INTERACTIVE DUPLICATE MANAGEMENT")
    print("=" * 80)
    
    pause_input = input("Pause between groups for review? (Y/n): ").strip().lower()
    pause_enabled = pause_input != 'n'
    
    clear_input = input("Clear screen between groups? (Y/n): ").strip().lower()
    clear_enabled = clear_input != 'n'
    
    moved_files = []
    deletion_dir = os.path.join(os.getcwd(), 'to_be_deleted')
    
    group_num = 0
    total_groups = len(duplicates)
    
    for (file_size, file_hash), filepaths in duplicates.items():
        group_num += 1
        
        # Clear screen if enabled
        if clear_enabled:
            clear_screen()
        
        print("\n" + "=" * 80)
        print(f"DUPLICATE GROUP {group_num} of {total_groups}")
        print("=" * 80)
        print(f"Size: {format_size(file_size)}")
        print(f"Hash: {file_hash}")
        print("-" * 80)
        
        # Display files with numbers
        for i, filepath in enumerate(filepaths, 1):
            print(f"{i}. {filepath}")
        
        print("-" * 80)
        print("\nOptions:")
        print("  Enter numbers to move (e.g., '1 3' or '1,3')")
        print("  'a' or 'all' to move all files")
        print("  's' or 'skip' to skip this group")
        print("  'q' or 'quit' to exit")
        
        choice = input("\nYour choice: ").strip().lower()
        
        if choice in ['q', 'quit']:
            print("\nExiting duplicate management...")
            break
        elif choice in ['s', 'skip', '']:
            print("Skipping this group.")
        elif choice in ['a', 'all']:
            # Move all files
            for filepath in filepaths:
                success, dest = move_file_to_deletion(filepath, deletion_dir)
                if success:
                    moved_files.append((filepath, dest))
                    print(f"Moved: {filepath} -> {dest}")
        else:
            # Parse number selections
            try:
                # Handle both space and comma separated input
                choice = choice.replace(',', ' ')
                indices = [int(x) for x in choice.split()]
                
                for idx in indices:
                    if 1 <= idx <= len(filepaths):
                        filepath = filepaths[idx - 1]
                        success, dest = move_file_to_deletion(filepath, deletion_dir)
                        if success:
                            moved_files.append((filepath, dest))
                            print(f"Moved: {filepath} -> {dest}")
                    else:
                        print(f"Invalid index: {idx}")
            except ValueError:
                print("Invalid input. Skipping this group.")
        
        # Pause if enabled
        if pause_enabled and group_num < total_groups:
            user_input = input("\nPress Enter to continue to next group (or 'q' to quit)... ").strip().lower()
            if user_input == 'q':
                print("\nExiting duplicate management...")
                break
    
    return moved_files


def write_results_to_file(original_duplicates, moved_files=None, output_file="duplicate_files_report.txt"):
    """
    Write duplicate results to a text file with before/after statistics.
    
    Args:
        original_duplicates: Dictionary of duplicates before cleanup
        moved_files: List of (original_path, destination_path) tuples or None
        output_file: Path to output file
    """
    with open(output_file, 'w') as f:
        f.write("DUPLICATE FILE FINDER REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        # ORIGINAL SEARCH RESULTS section (always written)
        f.write("ORIGINAL SEARCH RESULTS (BEFORE CLEANUP)\n")
        f.write("=" * 80 + "\n\n")
        
        if not original_duplicates:
            f.write("No duplicate files found!\n")
            return
        
        dir_duplicates = group_duplicates_by_directory(original_duplicates)
        
        # Write duplicates for each directory
        f.write("DUPLICATE FILES BY DIRECTORY\n")
        f.write("-" * 80 + "\n\n")
        
        for directory in sorted(dir_duplicates.keys()):
            duplicate_groups = dir_duplicates[directory]
            
            f.write(f"Directory: {directory}\n")
            f.write("-" * 40 + "\n")
            
            for group in duplicate_groups:
                f.write(f"Duplicate group (Size: {format_size(group['size'])}, Hash: {group['hash']}):\n")
                for filepath in group['files']:
                    marker = "[IN THIS DIR]" if filepath in group['files_in_dir'] else "[OTHER DIR]"
                    f.write(f"    {marker} {filepath}\n")
                f.write("\n")
            f.write("\n")
        
        # Write original summary
        total_groups = len(original_duplicates)
        total_duplicate_files = sum(len(paths) for paths in original_duplicates.values())
        
        f.write("ORIGINAL SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Number of unique file duplicate groups: {total_groups}\n")
        f.write(f"Total duplicate files: {total_duplicate_files}\n")
        f.write(f"Files that could be removed: {total_duplicate_files - total_groups}\n")
        f.write("\n")
        
        # CLEANUP ACTIONS section (if files were moved)
        if moved_files and len(moved_files) > 0:
            f.write("\n" + "=" * 80 + "\n")
            f.write("CLEANUP ACTIONS PERFORMED\n")
            f.write("=" * 80 + "\n\n")
            
            for original_path, destination_path in moved_files:
                f.write(f"From: {original_path}\n")
                f.write(f"To:   {destination_path}\n")
                f.write("\n")
            
            # Calculate remaining duplicates
            # Build set of moved files
            moved_set = {orig for orig, dest in moved_files}
            
            # Count remaining duplicate files
            remaining_duplicates = 0
            remaining_groups = 0
            for (file_size, file_hash), filepaths in original_duplicates.items():
                # Filter out moved files
                remaining_files = [fp for fp in filepaths if fp not in moved_set]
                if len(remaining_files) > 1:
                    remaining_groups += 1
                    remaining_duplicates += len(remaining_files)
            
            f.write("POST-CLEANUP SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total files moved to to_be_deleted: {len(moved_files)}\n")
            f.write(f"Remaining duplicate groups: {remaining_groups}\n")
            f.write(f"Remaining duplicate files: {remaining_duplicates}\n")
            f.write("\n")
        else:
            f.write("\n" + "=" * 80 + "\n")
            f.write("NO CLEANUP ACTIONS PERFORMED\n")
            f.write("=" * 80 + "\n\n")
        
        f.write("\nNOTE: Review carefully before permanently deleting any files!\n")
    
    print(f"\nResults written to: {output_file}")


def print_results(duplicates):
    """
    Print duplicate results grouped by directory.
    
    Args:
        duplicates: Dictionary mapping (size, hash) to file paths
        
    Returns:
        Tuple of (total_groups, total_duplicate_files)
    """
    if not duplicates:
        print("\nNo duplicate files found!")
        return 0, 0
    
    dir_duplicates = group_duplicates_by_directory(duplicates)
    
    print("\n" + "=" * 80)
    print("DUPLICATE FILES BY DIRECTORY")
    print("=" * 80)
    
    total_groups = len(duplicates)
    total_duplicate_files = sum(len(paths) for paths in duplicates.values())
    
    # Print duplicates for each directory
    for directory in sorted(dir_duplicates.keys()):
        duplicate_groups = dir_duplicates[directory]
        
        print(f"\nDirectory: {directory}")
        print("-" * 80)
        
        for group in duplicate_groups:
            print(f"  Duplicate group (Size: {format_size(group['size'])}, Hash: {group['hash'][:16]}...):")
            for filepath in group['files']:
                marker = "  *" if filepath in group['files_in_dir'] else "   "
                print(f"{marker} {filepath}")
            print()
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Number of unique file duplicate groups: {total_groups}")
    print(f"Total duplicate files: {total_duplicate_files}")
    print(f"Files that could be removed: {total_duplicate_files - total_groups}")
    print("=" * 80)
    
    return total_groups, total_duplicate_files


def main():
    """
    Main function to run the duplicate file finder.
    Maintains backward compatibility for command-line usage.
    """
    print("=" * 80)
    print("DUPLICATE FILE FINDER")
    print("=" * 80)
    print(f"Starting directory: {os.path.abspath('.')}")
    print("=" * 80)
    print()
    
    # Find duplicates starting from current directory
    duplicates = find_duplicates(".")
    
    # Print results to screen
    total_groups, total_duplicates = print_results(duplicates)
    
    if duplicates:
        # Ask if user wants to manage duplicates interactively
        print("\n" + "=" * 80)
        manage_input = input("Would you like to interactively manage duplicates? (Y/n): ").strip().lower()
        
        if manage_input != 'n':
            moved_files = manage_duplicates(duplicates)
            
            # Write results to file with cleanup information
            write_results_to_file(duplicates, moved_files)
            
            if moved_files:
                print(f"\n{len(moved_files)} file(s) moved to to_be_deleted/")
        else:
            # Write results to file without cleanup information
            write_results_to_file(duplicates)
    
    print("\nScan complete!")


if __name__ == "__main__":
    main()
