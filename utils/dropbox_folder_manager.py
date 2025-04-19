import os
import dropbox
import dropbox.common 
from .dropbox_token_manager import get_access_token

# Renamed from files_list_folder
def _files_list_folder_internal(dbx_client, path, **kwargs):
    """Internal function to list folder using a pre-configured client."""
    # API call parameters are passed via kwargs
    # Ensure only valid args for files_list_folder are passed
    valid_args = {
        'recursive', 'include_media_info', 'include_deleted', 
        'include_has_explicit_shared_members', 'include_mounted_folders', 
        'limit', 'shared_link', 'include_property_groups', 
        'include_non_downloadable_files'
    }
    api_kwargs = {k: v for k, v in kwargs.items() if k in valid_args}
    
    # Fix: Always ensure "/" is converted to "" for Dropbox API root path
    if path == "/":
        path = ""
        
    return dbx_client.files_list_folder(path=path, **api_kwargs)

# Renamed from files_list_folder_continue
def _files_list_folder_continue_internal(dbx_client, cursor):
    """Internal function to continue listing using a pre-configured client."""
    return dbx_client.files_list_folder_continue(cursor)

def list_folder_complete(path, select_user=None, **kwargs):
    """
    Lists all contents of a folder on Dropbox, handling pagination automatically.
    Determines the correct user context and path root based on Dropbox best practices.
    
    Args:
        path (str): The path of the folder to list (relative to the determined root). 
                    Use empty string "" for the root.
        select_user (str, optional): Team member ID (e.g., "dbmid:...") to operate as. 
                                     If None, operates as the admin linked to the token.
        **kwargs: Additional arguments for files_list_folder (e.g., recursive=True). 
                  Must match the API parameter names.
        
    Returns:
        list: Complete list of all dropbox.files.Metadata entries in the folder.
        
    Raises:
        dropbox.exceptions.ApiError: If the API request fails.
        ValueError: If token is invalid or required info cannot be determined.
        RuntimeError: For unexpected errors during the process.
    """
    access_token = get_access_token()
    if not access_token:
        raise ValueError("Failed to obtain a valid access token")

    dbx_team = dropbox.DropboxTeam(access_token)
    member_id_to_use = select_user

    try:
        # 1. Determine the Member ID context
        if not member_id_to_use:
            admin_info = dbx_team.team_token_get_authenticated_admin()
            # Ensure we get the team_member_id, not just the user_id if different
            if hasattr(admin_info.admin_profile, 'team_member_id'):
                 member_id_to_use = admin_info.admin_profile.team_member_id
            else:
                 # Fallback or error, depending on API version/structure
                 raise ValueError("Could not determine team_member_id for the authenticated admin.")
        
        # 2. Get user-specific context client
        dbx_user_context = dbx_team.as_user(member_id_to_use)

        # 3. Get account info to find the root namespace ID
        account_info = dbx_user_context.users_get_current_account()
        
        if not hasattr(account_info, 'root_info') or not hasattr(account_info.root_info, 'root_namespace_id'):
             raise ValueError("Could not determine root_namespace_id from user's account info.")
             
        root_namespace_id = account_info.root_info.root_namespace_id

        # 4. Create the final client scoped to the correct root and user
        team_path_root = dropbox.common.PathRoot.namespace_id(root_namespace_id)
        # Apply path_root first, then user context for the final client
        dbx_final_client = dbx_team.with_path_root(team_path_root).as_user(member_id_to_use)

        # 5. Perform the listing using the configured client
        # Pass only valid listing arguments from kwargs
        listing_kwargs = {
            k: v for k, v in kwargs.items() 
            if k in ['recursive', 'include_media_info', 'include_deleted', 
                     'include_has_explicit_shared_members', 'include_mounted_folders', 
                     'limit', 'shared_link', 'include_property_groups', 
                     'include_non_downloadable_files']
        }
        
        # Fix: Convert "/" to "" for root path (Dropbox API requires empty string for root)
        if path == "/":
            path = ""
            
        result = _files_list_folder_internal(dbx_final_client, path, **listing_kwargs)
        entries = result.entries
        
        # 6. Handle pagination
        while result.has_more:
            result = _files_list_folder_continue_internal(dbx_final_client, result.cursor)
            entries.extend(result.entries)
            
        return entries

    except dropbox.exceptions.AuthError as e:
        raise ValueError(f"Authentication error: {e}. Check token validity and scopes.") from e
    except dropbox.exceptions.ApiError as e:
        # Catch API errors during setup or listing
        error_summary = "Unknown Error"
        if hasattr(e, 'error') and hasattr(e.error, 'get_summary'):
            error_summary = e.error.get_summary()
        elif hasattr(e, 'error'):
             error_summary = str(e.error)
        else:
             error_summary = str(e)
             
        print(f"Dropbox API Error Summary: {error_summary}")
        
        # Attempt to print more details if available (e.g., for path errors)
        if hasattr(e, 'error') and hasattr(e.error, 'path') and e.error.path:
             print(f"  Error details related to path lookup: {e.error.path}")
             
        # Provide context about the operation
        print(f"  Error occurred during operation for path '{path}'.")
        raise # Re-raise the original ApiError

    except AttributeError as e:
        # Catch potential issues accessing nested attributes like root_info
        import traceback
        print(f"AttributeError: {e}\n{traceback.format_exc()}") # Log full traceback
        raise ValueError(f"Error accessing expected data structure: {e}. Check API response/structure or permissions.") from e
    except Exception as e:
        # Catch any other unexpected errors during setup/listing
        import traceback
        print(f"Unexpected Error: {e}\n{traceback.format_exc()}") # Log full traceback
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

# Keep original names as wrappers for backward compatibility if needed,
# but they are now essentially replaced by list_folder_complete.
# Consider removing them if they aren't used elsewhere.

def files_list_folder(path, select_user=None, **kwargs):
    """
    Legacy wrapper for list_folder_complete. Recommended: Use list_folder_complete directly.
    """
    print("Warning: Called legacy files_list_folder wrapper. Consider using list_folder_complete directly.")
    # Ensure only valid kwargs for list_folder_complete itself are passed (select_user handled)
    valid_kwargs = {k: v for k, v in kwargs.items() if k != 'select_user'}
    return list_folder_complete(path, select_user=select_user, **valid_kwargs)

def files_list_folder_continue(cursor, select_user=None):
    """
    This function cannot reliably continue pagination as it lacks the necessary client context
    (correctly scoped user and path_root). Pagination must be handled within list_folder_complete.
    """
    raise NotImplementedError("files_list_folder_continue cannot be used directly due to context requirements. Use list_folder_complete for full listing.")
