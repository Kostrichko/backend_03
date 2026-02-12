# Bot configuration
import os

# API settings
API_URL = os.getenv('API_URL', 'http://web:8000/api')
API_KEY = os.getenv('API_KEY', '12345')

# User limits (should match backend settings)
MAX_TAGS_PER_USER = 4
MAX_PENDING_TASKS_PER_USER = 6
MAX_ARCHIVE_TASKS_PER_USER = 5

# Bot settings
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Notification times (in minutes)
NOTIFICATION_TIMES = [1, 2, 5, 10, 15, 30]