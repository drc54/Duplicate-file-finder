# Duplicate-file-finder
Directory tree search for duplicate files

## Description

A Python script that scans the current directory and all subdirectories to find duplicate files. The tool identifies duplicates using MD5 hashing and provides detailed reports both on screen and in a text file.

## Features

- **Real-time scanning progress**: Displays each file's path and size while scanning
- **Efficient duplicate detection**: Uses file size pre-filtering before computing MD5 hashes
- **Directory-based reporting**: Shows duplicates organized by directory
- **Detailed summary**: Reports total unique duplicate groups and total duplicate files
- **Export to file**: Generates a text report (`duplicate_files_report.txt`) for use in removing duplicates
- **Smart skipping**: Only shows directories that contain duplicates

## Requirements

- Python 3.x
- No external dependencies (uses only Python standard library)

## Usage

1. Navigate to the directory you want to scan:
```bash
cd /path/to/scan
```

2. Run the duplicate finder:
```bash
python3 /path/to/duplicate_finder.py
```

Or make it executable and run directly:
```bash
chmod +x duplicate_finder.py
./duplicate_finder.py
```

## Output

### Screen Output

The script provides three stages of output:

1. **Scanning Phase**: Shows each file being scanned with its path and size
2. **Duplicate Report**: Displays duplicates grouped by directory
   - Files marked with `*` are in the current directory being listed
   - Other files are in different directories
3. **Summary**: Shows statistics including:
   - Number of unique file duplicate groups
   - Total duplicate files found
   - Files that could be removed

### File Output

A detailed report is saved to `duplicate_files_report.txt` containing:
- Timestamp of the scan
- Duplicates organized by directory
- Full file paths with directory markers
- Hash values for verification
- Summary statistics
- Notes on safe removal practices

## Example

```
================================================================================
DUPLICATE FILE FINDER
================================================================================
Starting directory: /home/user/documents
================================================================================

Scanning files...

--------------------------------------------------------------------------------
Path: ./folder1/image.jpg
Size: 1.23 MB

Path: ./folder2/photo.jpg
Size: 1.23 MB
...

================================================================================
DUPLICATE FILES BY DIRECTORY
================================================================================

Directory: /home/user/documents/folder1
--------------------------------------------------------------------------------
  Duplicate group (Size: 1.23 MB, Hash: a1b2c3d4e5f6...):
  * ./folder1/image.jpg
    ./folder2/photo.jpg

================================================================================
SUMMARY
================================================================================
Number of unique file duplicate groups: 1
Total duplicate files: 2
Files that could be removed: 1
================================================================================
```

## How It Works

1. **Size Grouping**: First groups files by size (optimization step)
2. **Hash Calculation**: Only files with matching sizes are hashed using MD5
3. **Duplicate Detection**: Files with identical hashes are marked as duplicates
4. **Directory Grouping**: Results are organized by parent directory
5. **Reporting**: Displays results to screen and exports to text file

## Safety Notes

- The script only identifies duplicates; it does not delete any files
- Always review the generated report carefully before removing any files
- Keep at least one copy of each duplicate group
- Consider backing up important files before performing any deletions

## License

Open source - feel free to use and modify as needed.
