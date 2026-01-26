from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_role_menu(role: str) -> ReplyKeyboardMarkup:
    menus = {
        'admin': [
            [KeyboardButton(text="➕ Добавить пользователя")],
            [KeyboardButton(text="👥 Список пользователей")],
            [KeyboardButton(text="➕ Добавить рецепт")],
            [KeyboardButton(text="🔍 Найти рецепт")]
        ],
        'doctor': [
            [KeyboardButton(text="➕ Добавить рецепт")],
            [KeyboardButton(text="📋 Мои рецепты")]
        ],
        'pharmacist': [
            [KeyboardButton(text="🔍 Проверить рецепт")]
        ]
    }
    
    return ReplyKeyboardMarkup(keyboard=menus.get(role, []), resize_keyboard=True)


def get_duration_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц", callback_data="duration_30")],
        [InlineKeyboardButton(text="3 месяца", callback_data="duration_90")],
        [InlineKeyboardButton(text="6 месяцев", callback_data="duration_180")],
        [InlineKeyboardButton(text="1 год", callback_data="duration_365")],
        [InlineKeyboardButton(text="Своя длительность", callback_data="duration_custom")]
    ])


def get_recipe_items_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ещё", callback_data="add_more_item")],
        [InlineKeyboardButton(text="❌ Удалить препарат", callback_data="delete_item")],
        [InlineKeyboardButton(text="✅ Продолжить", callback_data="continue_recipe")],
        [InlineKeyboardButton(text="🚫 Отменить рецепт", callback_data="cancel_recipe_creation")]
    ])


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_recipe"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_recipe")
    ]])


def get_recipe_actions_keyboard(recipe_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отметить как списанный", callback_data=f"mark_used_{recipe_id}")],
        [InlineKeyboardButton(text="✏️ Изменить количество", callback_data=f"edit_quantity_{recipe_id}")]
    ])


def get_doctor_recipe_actions_keyboard(recipe_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить количество", callback_data=f"edit_quantity_{recipe_id}")]
    ])


def get_item_delete_keyboard(items: list) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=f"❌ {item['drug_name']} - {item['quantity']}", callback_data=f"delete_item_{idx}")] 
               for idx, item in enumerate(items)]
    buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="done_delete")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_item_edit_keyboard(recipe_id: int, items: list) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=f"✏️ {item['drug_name']} ({item['quantity']})", callback_data=f"edit_item_{recipe_id}_{item['id']}")] 
               for item in items]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_recipe_{recipe_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_recipes_pagination_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    if total_pages <= 1:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    row = []
    if current_page > 0:
        row.append(InlineKeyboardButton(text="◀️ Назад", callback_data="recipes_page_prev"))
    if current_page < total_pages - 1:
        row.append(InlineKeyboardButton(text="Вперед ▶️", callback_data="recipes_page_next"))
    
    return InlineKeyboardMarkup(inline_keyboard=[row] if row else [])
