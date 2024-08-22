from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


def today_dates(today):
    start_date = today
    end_date = start_date + timedelta(days=1)
    return start_date, end_date


def current_week_dates(today):
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)
    return start_date, end_date


def current_month_dates(today):
    start_date = today.replace(day=1)
    end_date = start_date + relativedelta(months=1)
    return start_date, end_date


def current_year_dates(today):
    start_date = date(today.year, 1, 1)
    end_date = date(today.year, 12, 31)
    return start_date, end_date


def past_days_dates(today, count=1):
    end_date = today
    start_date = end_date - timedelta(days=count)
    return start_date, end_date


def past_week_dates(today, count=1):
    end_date = today - timedelta(days=today.weekday())
    start_date = end_date - timedelta(days=7)
    if count > 1:
        start_date -= timedelta(days=(7 * (count - 1)))

    return start_date, end_date


def past_month_dates(today, count=1):
    end_date = today.replace(day=1)
    start_date = end_date - relativedelta(months=1)

    if count > 1:
        start_date -= relativedelta(months=count - 1)

    return start_date, end_date


def past_year_dates(today, count=1):
    end_date = date(today.year, 12, 31)
    start_date = date(today.year - count, 1, 1)
    return start_date, end_date


def past_24_hr_dates(today):
    end_date = today
    start_date = end_date - timedelta(hours=24)
    return start_date, end_date


def next_day_dates(today):
    end_date = today + timedelta(days=2)
    start_date = end_date - timedelta(days=1)
    return start_date, end_date


def next_week_dates(today):
    this_week_start = today - timedelta(days=today.weekday())
    start_date = this_week_start + timedelta(days=7)
    end_date = start_date + timedelta(days=7)
    return start_date, end_date


def next_month_dates(today):
    start_date = today.replace(day=1) + relativedelta(months=1)
    end_date = start_date + relativedelta(months=1)
    return start_date, end_date


def next_year_dates(today):
    start_date = date(today.year + 1, 1, 1)
    end_date = date(today.year + 2, 1, 1)
    return start_date, end_date
