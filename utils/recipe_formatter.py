from datetime import datetime
from typing import Dict, List
from utils.date_formatter import format_datetime, format_date, format_duration_days, calculate_expires_at


def format_recipe_status(recipe: Dict) -> tuple[str, str]:
    status_emoji = "✅" if recipe['status'] == 'used' else "📝"
    status_text = "Списан" if recipe['status'] == 'used' else "Активен"
    return status_emoji, status_text


def format_recipe_items(items: List[Dict]) -> str:
    return "\n".join([
        f"• {item['drug_name']} - {item['quantity']} шт."
        for item in items
    ])


def format_doctor_name(recipe: Dict) -> str:
    return recipe.get('doctor_name') or recipe.get('doctor_username') or 'N/A'


def format_pharmacist_name(log: Dict) -> str:
    return log.get('pharmacist_username') or log.get('pharmacist_name') or 'Unknown'


def format_recipe_detail(recipe: Dict, recipe_id: int) -> str:
    status_emoji, status_text = format_recipe_status(recipe)
    created_at = recipe['created_at']
    expires_at = calculate_expires_at(created_at, recipe['duration_days'])
    is_expired = datetime.now() > expires_at
    
    items_text = format_recipe_items(recipe['items'])
    doctor_name = format_doctor_name(recipe)
    
    recipe_text = (
        f"{status_emoji} <b>Рецепт #{recipe_id}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👨‍⚕️ <b>Врач:</b> {doctor_name}\n"
        f"📅 <b>Дата создания:</b> {format_datetime(created_at)}\n"
        f"⏱ <b>Срок действия:</b> {recipe['duration_days']} дней (до {format_date(expires_at)})\n"
        f"📊 <b>Статус:</b> {status_text}\n"
    )
    
    if is_expired and recipe['status'] == 'active':
        recipe_text += "⚠️ <b>Рецепт просрочен!</b>\n"
    
    recipe_text += f"\n💊 <b>Препараты:</b>\n{items_text}\n"
    
    if recipe.get('comment'):
        recipe_text += f"\n💬 <b>Комментарий:</b> {recipe['comment']}\n"
    
    recipe_text += "━━━━━━━━━━━━━━━━━━━━"
    
    return recipe_text


def format_recipe_logs(logs: List[Dict]) -> str:
    if not logs:
        return ""
    
    logs_text = "\n\n📝 <b>История изменений:</b>\n"
    for log in logs:
        pharmacist_name = format_pharmacist_name(log)
        action_text = "Списан" if log['action_type'] == 'used' else "Изменено количество"
        logs_text += f"• {action_text} - {pharmacist_name} ({format_datetime(log['created_at'])})\n"
    
    return logs_text
