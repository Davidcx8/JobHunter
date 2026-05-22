# JobHunter Pro - Cron Jobs Configuration
# This file defines scheduled tasks for automatic job hunting

# Format: minute hour day month weekday command

# =============================================================================
# AUTO SCRAPING SCHEDULE (Linux/Mac crontab)
# =============================================================================

# Run daily scraping at 9:00 AM
# 0 9 * * * cd /path/to/jobhunter-pro && python backend/scheduler.py

# Run twice daily (9 AM and 6 PM)
# 0 9,18 * * * cd /path/to/jobhunter-pro && python backend/scheduler.py

# Run every 6 hours
# 0 */6 * * * cd /path/to/jobhunter-pro && python backend/scheduler.py


# =============================================================================
# WINDOWS TASK SCHEDULER
# =============================================================================

# For Windows, use the following PowerShell commands:

# Create a daily task at 9:00 AM
# $action = New-ScheduledTaskAction -Execute 'python' -Argument 'C:\path\to\jobhunter-pro\backend\scheduler.py'
# $trigger = New-ScheduledTaskTrigger -Daily -At 9AM
# $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingBatteries
# Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -TaskName "JobHunterDailyScrape"


# =============================================================================
# AUTO SCRAPING CONFIGURATION
# =============================================================================

AUTO_SCRAPE_CONFIG = {
    'enabled': True,
    'schedule': {
        'frequency': 'daily',  # Options: hourly, daily, twice_daily
        'times': ['09:00', '18:00'],  # For twice_daily
        'sources': ['linkedin', 'indeed', 'remotive', 'glassdoor', 'weworkremotely', 'github'],
    },
    'search_terms': [
        'python developer',
        'full stack developer',
        'remote software engineer',
        'javascript developer',
    ],
    'location': 'worldwide',
    'limit_per_source': 20,
    'save_to_db': True,
    'notify_on_new': True,
}


# =============================================================================
# AUTO FOLLOW-UP CONFIGURATION
# =============================================================================

AUTO_FOLLOWUP_CONFIG = {
    'enabled': True,
    'check_times': ['08:00'],
    'days_to_followup': [3, 7, 14],  # Days after application
    'template': 'follow_up',
    'auto_send': False,  # Set to True to send automatically
}


# =============================================================================
# AUTO EMAIL SEQUENCE
# =============================================================================

AUTO_EMAIL_CONFIG = {
    'enabled': False,  # Requires email configuration
    'schedule': {
        'frequency': 'daily',
        'times': ['10:00'],
    },
    'max_emails_per_day': 10,
    'delay_between_emails': 60,  # seconds
    'templates': ['cold_reachout', 'follow_up'],
}


# =============================================================================
# DATABASE BACKUP
# =============================================================================

BACKUP_CONFIG = {
    'enabled': True,
    'schedule': 'weekly',  # daily, weekly, monthly
    'time': '03:00',  # 3 AM - off-peak hours
    'retention_days': 30,
    'backup_location': './backups',
}


# =============================================================================
# LOG ROTATION
# =============================================================================

LOG_CONFIG = {
    'max_size_mb': 50,
    'retention_days': 7,
    'log_folder': './logs',
}


# =============================================================================
# EXAMPLE: Run multiple times per day
# =============================================================================

MULTIPLE_SCRAPE_SCHEDULE = """
# Every day at 6 AM, 12 PM, 6 PM
0 6,12,18 * * * cd /path/to/jobhunter-pro && python -c "from backend.scheduler import auto_scrape_all; auto_scrape_all()"

# Every Monday at 8 AM
0 8 * * 1 cd /path/to/jobhunter-pro && python -c "from backend.scheduler import auto_scrape_all; auto_scrape_all()"
"""