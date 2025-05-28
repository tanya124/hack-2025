import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Print environment variables
print(f"PGHOST: {os.getenv('PGHOST')}")
print(f"PGDATABASE: {os.getenv('PGDATABASE')}")
print(f"PGUSER: {os.getenv('PGUSER')}")
print(f"PGPASSWORD: {os.getenv('PGPASSWORD')}")
print(f"PGPORT: {os.getenv('PGPORT')}")
