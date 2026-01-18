def get_access_denied_message(admin_text: str) -> str:
    return (
        "🚫 <b>Доступ запрещён</b>\n\n"
        "Бот доступен только для авторизованных пользователей.\n\n"
        "📋 <b>Для получения доступа:</b>\n"
        "1. Скопируйте сообщение с вашим ID ниже\n"
        f"2. Отправьте его {admin_text}\n\n"
        "После проверки администратор добавит вас в систему."
    )


def get_user_id_message(user_full_name: str, user_username: str | None, user_id: int) -> str:
    user_info = f"Имя: {user_full_name}\n"
    if user_username:
        user_info += f"Username: @{user_username}\n"
    user_info += f"User ID: <code>{user_id}</code>"
    
    return (
        f"📝 <b>Ваш ID для отправки администратору:</b>\n\n"
        f"{user_info}"
    )
