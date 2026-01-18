from datetime import datetime, timedelta


def format_datetime(dt: datetime) -> str:
    return dt.strftime('%d.%m.%Y %H:%M')


def format_date(dt: datetime) -> str:
    return dt.strftime('%d.%m.%Y')


def format_duration_days(days: int) -> str:
    if days == 30:
        return "1 месяц"
    elif days == 90:
        return "3 месяца"
    elif days == 180:
        return "6 месяцев"
    elif days == 365:
        return "1 год"
    else:
        return f"{days} дней"


def calculate_expires_at(created_at: datetime, duration_days: int) -> datetime:
    return created_at + timedelta(days=duration_days)
