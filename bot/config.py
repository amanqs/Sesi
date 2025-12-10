# config.py

API_ID = 9128356   # ganti dengan API ID my.telegram.org
API_HASH = "cf219228092173e15047d3fb5a023cfc"  # ganti
BOT_TOKEN = "8547139242:AAHSyKp8iSRkswAl37TymgP4crlihTsqlZY"  # ganti

# lokasi file SQLite
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sessions.db")


# admin yang boleh pakai /admin_users (optional)
ADMINS = [1839010591]  # isi dengan user_id kamu, bisa lebih dari satu
