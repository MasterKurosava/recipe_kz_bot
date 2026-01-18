from typing import List, Dict


def format_admin_contacts(admins: List[Dict]) -> str:
    if not admins:
        return "администратором"
    
    admin_usernames = []
    for admin in admins:
        if admin.get('username'):
            admin_usernames.append(f"@{admin['username']}")
    
    if not admin_usernames:
        return "администратором"
    
    if len(admin_usernames) == 1:
        return f"администратором {admin_usernames[0]}"
    else:
        return f"администраторами: {', '.join(admin_usernames)}"
