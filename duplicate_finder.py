#!/usr/bin/env python3
"""
Duplicate File Finder
Scans the current directory and all subdirectories to find duplicate files.
"""

import os
import hashlib
from collections import defaultdict
from datetime import datetime


def get_file_hash(filepath):
    """Calculate MD5 hash of a file to determine duplicates."""
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
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def find_duplicates(root_dir="."):
    """
    Find all duplicate files starting from root_dir.
    Returns a dictionary mapping file hashes to lists of file paths.
    """
    # Dictionary to store file hashes and their paths
    # Key: (file_size, file_hash), Value: list of file paths
    files_by_size = defaultdict(list)
    files_by_hash = defaultdict(list)
    skipped_files = []
    
    print("Scanning files...\n")
    print("-" * 80)
    
    # First pass: group files by size (faster than hashing everything)
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                # Get file size
                file_size = os.path.getsize(filepath)
                
                # Display progress
                print(f"Path: {filepath}")
                print(f"Size: {format_size(file_size)}")
                print()
                
                # Group by size first (optimization)
                files_by_size[file_size].append(filepath)
                
            except (OSError, IOError, PermissionError) as e:
                # Track skipped files without cluttering output
                skipped_files.append((filepath, str(e)))
                continue
    
    print("-" * 80)
    
    # Report skipped files if any
    if skipped_files:
        print(f"\nSkipped {len(skipped_files)} file(s) due to access errors (e.g., cache files, permission issues)")
        print("Run with elevated permissions if you need to scan all files.\n")
    
    print("\nCalculating file hashes for potential duplicates...\n")
    
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
    Returns a dictionary mapping directories to lists of duplicate groups.
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


def print_results(duplicates):
    """Print duplicate results grouped by directory."""
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


def write_results_to_file(duplicates, output_file="duplicate_files_report.txt"):
    """Write duplicate results to a text file for removal operations."""
    with open(output_file, 'w') as f:
        f.write("DUPLICATE FILE FINDER REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        if not duplicates:
            f.write("No duplicate files found!\n")
            return
        
        dir_duplicates = group_duplicates_by_directory(duplicates)
        
        # Write duplicates for each directory
        f.write("DUPLICATE FILES BY DIRECTORY\n")
        f.write("=" * 80 + "\n\n")
        
        for directory in sorted(dir_duplicates.keys()):
            duplicate_groups = dir_duplicates[directory]
            
            f.write(f"Directory: {directory}\n")
            f.write("-" * 80 + "\n")
            
            for group in duplicate_groups:
                f.write(f"Duplicate group (Size: {format_size(group['size'])}, Hash: {group['hash']}):\n")
                f.write(f"  Keep one of these files and remove the others:\n")
                for filepath in group['files']:
                    marker = "[IN THIS DIR]" if filepath in group['files_in_dir'] else "[OTHER DIR]"
                    f.write(f"    {marker} {filepath}\n")
                f.write("\n")
            f.write("\n")
        
        # Write summary
        total_groups = len(duplicates)
        total_duplicate_files = sum(len(paths) for paths in duplicates.values())
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Number of unique file duplicate groups: {total_groups}\n")
        f.write(f"Total duplicate files: {total_duplicate_files}\n")
        f.write(f"Files that could be removed: {total_duplicate_files - total_groups}\n")
        f.write("=" * 80 + "\n")
        
        f.write("\nNOTE: For each duplicate group, keep one file and remove the others.\n")
        f.write("Review carefully before deleting any files!\n")
    
    print(f"\nResults written to: {output_file}")


def main():
    """Main function to run the duplicate file finder."""
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
    
    # Write results to file
    if duplicates:
        write_results_to_file(duplicates)
    
    print("\nScan complete!")


if __name__ == "__main__":
    main()
