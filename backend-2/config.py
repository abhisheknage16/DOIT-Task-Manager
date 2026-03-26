# import os
# from dotenv import load_dotenv

# load_dotenv()

# # MongoDB Atlas Cloud Connection
# MONGO_URI = os.getenv(
#     "MONGO_URI",
#     "mongodb+srv://Admin:Lkbd2sXR80uUBd5T@jira-task-management.croznmu.mongodb.net/taskdb?retryWrites=true&w=majority&appName=jira-task-management",
# )
# JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this")
# JWT_EXPIRY_HOURS = 24
import os
from dotenv import load_dotenv

load_dotenv()

# Azure DocumentDB (MongoDB compatibility)
MONGO_URI = os.getenv(
    "COSMOS_CONNECTION_STRING",
    "mongodb+srv://doitadmin:pENxg5pnsxmL9I6z@doitdb.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000",
)

# Document Intelligence
DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv(
    "DOCUMENT_INTELLIGENCE_ENDPOINT", "https://docint07.cognitiveservices.azure.com/"
)
DOCUMENT_INTELLIGENCE_KEY = os.getenv(
    "DOCUMENT_INTELLIGENCE_KEY",
    "",  # Never hardcode — use .env only
)
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this")
JWT_EXPIRY_HOURS = 24
