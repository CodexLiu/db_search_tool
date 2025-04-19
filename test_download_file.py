#!/usr/bin/env python3
from utils.tools import check_file_contents

def main():
    # Set the Dropbox path to the file you want to check
    file_path = "/Amplifye (NEW)/Research & Development/SOP/SOP-template.docx"
    # Optionally set team_member_id if needed, else None
    team_member_id = None
    
    print("--- Checking file contents with OpenAI API ---")
    try:
        api_response = check_file_contents(file_path, select_user=team_member_id)
        print(api_response)
    except Exception as e:
        print(f"Error querying OpenAI API: {e}")

if __name__ == "__main__":
    main() 