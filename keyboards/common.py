from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_role_menu(role: str) -> ReplyKeyboardMarkup:
    if role == 'admin':
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Добавить пользователя")],
                [KeyboardButton(text="👥 Список пользователей")],
                [KeyboardButton(text="➕ Добавить рецепт")],
                [KeyboardButton(text="🔍 Найти рецепт")]
            ],
            resize_keyboard=True
        )
    elif role == 'doctor':
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Добавить рецепт")],
                [KeyboardButton(text="📋 Мои рецепты")]
            ],
            resize_keyboard=True
        )
    elif role == 'pharmacist':
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔍 Проверить рецепт")]
            ],
            resize_keyboard=True
        )
    else:
        keyboard = ReplyKeyboardMarkup(
            keyboard=[],
            resize_keyboard=True
        )
    return keyboard


def get_duration_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 месяц", callback_data="duration_30")],
            [InlineKeyboardButton(text="3 месяца", callback_data="duration_90")],
            [InlineKeyboardButton(text="6 месяцев", callback_data="duration_180")],
            [InlineKeyboardButton(text="1 год", callback_data="duration_365")],
            [InlineKeyboardButton(text="Своя длительность", callback_data="duration_custom")]
        ]
    )
    return keyboard


def get_recipe_items_actions_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ещё", callback_data="add_more_item")],
            [InlineKeyboardButton(text="❌ Удалить", callback_data="delete_item")],
            [InlineKeyboardButton(text="✅ Продолжить", callback_data="continue_recipe")]
        ]
    )
    return keyboard


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_recipe"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_recipe")
            ]
        ]
    )
    return keyboard


def get_recipe_actions_keyboard(recipe_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отметить как списанный", callback_data=f"mark_used_{recipe_id}")],
            [InlineKeyboardButton(text="✏️ Изменить количество", callback_data=f"edit_quantity_{recipe_id}")]
        ]
    )
    return keyboard


def get_doctor_recipe_actions_keyboard(recipe_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить количество", callback_data=f"edit_quantity_{recipe_id}")]
        ]
    )
    return keyboard


def get_item_delete_keyboard(items: list) -> InlineKeyboardMarkup:
    buttons = []
    for idx, item in enumerate(items):
        buttons.append([InlineKeyboardButton(
            text=f"❌ {item['drug_name']} - {item['quantity']}",
            callback_data=f"delete_item_{idx}"
        )])
    buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="done_delete")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_item_edit_keyboard(recipe_id: int, items: list) -> InlineKeyboardMarkup:
    buttons = []
    for item in items:
        buttons.append([InlineKeyboardButton(
            text=f"✏️ {item['drug_name']} ({item['quantity']})",
            callback_data=f"edit_item_{recipe_id}_{item['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_recipe_{recipe_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
