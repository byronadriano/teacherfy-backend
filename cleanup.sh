#!/bin/bash
# cleanup.sh - Script to clean up unnecessary files in Teacherfy backend

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}Teacherfy Backend Cleanup${NC}"
echo -e "${BLUE}=======================================${NC}\n"

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Files that are candidates for removal
REDUNDANT_FILES=(
    # Redundant startup files
    "startup.txt"
    
    # Now consolidated into setup.sh
    "setup_history.sh"
    "setup_history_routes.sh" 
    "setup_migration.sh"
    "setup_recents_list.sh"
    "run_migration.sh"
    
    # Now consolidated into test.sh
    "test_api.sh"
    "test_rate_limits.sh"
    
    # Python cache files
    "**/__pycache__/"
    "**/*.pyc"
    "**/*.pyo"
    
    # Log files
    "**/*.log"
    
    # Temporary files
    "**/temp_*"
    "**/tmp_*"
    
    # Test download directory
    "test_downloads/"
)

# Files that should be backed up before removal
BACKUP_FIRST=(
    # Configuration files that might have custom changes
    ".env"
    "src/config.py"
)

# Create a backup directory
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"

# Function to backup files
backup_files() {
    echo -e "${YELLOW}Creating backup directory: $BACKUP_DIR${NC}"
    mkdir -p "$BACKUP_DIR"
    
    for file in "${BACKUP_FIRST[@]}"; do
        if [ -f "$file" ]; then
            echo "Backing up $file"
            cp "$file" "$BACKUP_DIR/"
        elif [ -d "$file" ]; then
            echo "Backing up directory $file"
            cp -r "$file" "$BACKUP_DIR/"
        fi
    done
    
    echo -e "${GREEN}Backup completed.${NC}"
}

# Function to remove files
remove_files() {
    local count=0
    
    echo -e "${YELLOW}The following files will be removed:${NC}"
    
    # First, list all files
    for pattern in "${REDUNDANT_FILES[@]}"; do
        for file in $(find . -path "./$pattern" -not -path "./venv/*" -not -path "./$BACKUP_DIR/*" 2>/dev/null); do
            echo "  $file"
            ((count++))
        done
    done
    
    if [ $count -eq 0 ]; then
        echo -e "${GREEN}No redundant files found.${NC}"
        return 0
    fi
    
    # Ask for confirmation
    read -p "Do you want to proceed with deletion? (y/n): " confirm
    if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
        echo -e "${YELLOW}Deletion cancelled.${NC}"
        return 0
    fi
    
    # Delete files
    for pattern in "${REDUNDANT_FILES[@]}"; do
        for file in $(find . -path "./$pattern" -not -path "./venv/*" -not -path "./$BACKUP_DIR/*" 2>/dev/null); do
            if [ -f "$file" ]; then
                echo "Removing file: $file"
                rm "$file"
            elif [ -d "$file" ]; then
                echo "Removing directory: $file"
                rm -r "$file"
            fi
        done
    done
    
    echo -e "${GREEN}Cleanup completed. $count items removed.${NC}"
}

# Function to clean temporary files
clean_temp_files() {
    echo -e "${YELLOW}Cleaning temporary files...${NC}"
    
    # Remove Python cache files
    find . -type d -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} +
    find . -name "*.pyc" -not -path "./venv/*" -delete
    find . -name "*.pyo" -not -path "./venv/*" -delete
    
    # Remove log files
    find . -name "*.log" -not -path "./venv/*" -delete
    
    echo -e "${GREEN}Temporary files cleaned.${NC}"
}

# Main function
main() {
    echo -e "${YELLOW}What would you like to do?${NC}"
    echo "1) Backup important files"
    echo "2) Clean up temporary files only (safe)"
    echo "3) Remove redundant files (backup recommended first)"
    echo "4) Full cleanup (backup + remove redundant files)"
    echo "5) Exit"
    
    read -p "Enter your choice [1-5]: " choice
    
    case $choice in
        1)
            backup_files
            ;;
        2)
            clean_temp_files
            ;;
        3)
            remove_files
            ;;
        4)
            backup_files
            clean_temp_files
            remove_files
            ;;
        5)
            echo "Exiting."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Exiting.${NC}"
            exit 1
            ;;
    esac
    
    echo -e "\n${GREEN}=======================================${NC}"
    echo -e "${GREEN}Operation completed!${NC}"
    echo -e "${GREEN}=======================================${NC}"
}

# Run main function
main