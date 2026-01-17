from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню с основными функциями"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Проверить рецепт")],
            [KeyboardButton(text="➕ Добавить рецепт")],
            [KeyboardButton(text="🕓 История по рецепту")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
    return keyboard


def get_back_to_menu_button() -> ReplyKeyboardMarkup:
    """Кнопка для возврата в главное меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 В меню")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_cancel_button() -> ReplyKeyboardMarkup:
    """Кнопка для отмены действия (завершает FSM)"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_skip_button() -> ReplyKeyboardMarkup:
    """Кнопка для пропуска комментария"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭️ Пропустить комментарий")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_confirm_buttons() -> ReplyKeyboardMarkup:
    """Кнопки подтверждения сохранения рецепта"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✅ Сохранить"),
                KeyboardButton(text="❌ Отменить")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
