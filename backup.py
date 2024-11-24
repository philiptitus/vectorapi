import os
import django
from django.core.management import call_command

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jennie.settings')

# Initialize Django
django.setup()

# Ensure the backups directory exists
os.makedirs('backups', exist_ok=True)

# Dumpdata into a JSON file with utf-8 encoding
with open('backups/data_backup.json', 'w', encoding='utf-8') as f:
    call_command('dumpdata', indent=4, stdout=f)
