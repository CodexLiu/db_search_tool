#!/usr/bin/env python3
import sys
import os 
from utils.tools import list_folder_contents

# This script now uses list_folder_complete which dynamically determines
# the correct Dropbox API context (user and root namespace) based on the
# official Dropbox Team Files Guide.

def main():
    team_member_id = None
    folder_path = ""
    entries = list_folder_contents(folder_path, select_user=team_member_id)
    for entry in entries:
        entry_type = entry.__class__.__name__.replace('Metadata', '')
        name = getattr(entry, 'name', 'Unknown Name')
        print(f"[{entry_type}] {name}")

if __name__ == "__main__":
    main()