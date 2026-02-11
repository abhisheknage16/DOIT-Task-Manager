from database import db
from bson import ObjectId
import datetime
from datetime import timezone

# Collections
ai_conversations_collection = db.ai_conversations
ai_messages_collection = db.ai_messages

class AIConversation:
    """Model for AI Assistant conversations (separate from team chat and chatbot)"""
    
    @staticmethod
    def create(user_id, title="New Conversation"):
        """Create a new AI conversation"""
        conversation_data = {
            "user_id": user_id,
            "title": title,
            "created_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None),
            "updated_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None),
            "message_count": 0
        }
        result = ai_conversations_collection.insert_one(conversation_data)
        return result.inserted_id
    
    @staticmethod
    def get_by_id(conversation_id):
        """Get conversation by ID"""
        return ai_conversations_collection.find_one({"_id": ObjectId(conversation_id)})
    
    @staticmethod
    def get_user_conversations(user_id, limit=50):
        """Get all conversations for a user"""
        return list(
            ai_conversations_collection.find({"user_id": user_id})
            .sort("updated_at", -1)
            .limit(limit)
        )
    
    @staticmethod
    def update_title(conversation_id, title):
        """Update conversation title"""
        return ai_conversations_collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$set": {
                    "title": title,
                    "updated_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None)
                }
            }
        )
    
    @staticmethod
    def update_timestamp(conversation_id):
        """Update the last updated timestamp"""
        return ai_conversations_collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$set": {
                    "updated_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None)
                },
                "$inc": {"message_count": 1}
            }
        )
    
    @staticmethod
    def delete(conversation_id):
        """Delete a conversation and all its messages"""
        # Delete all messages first
        ai_messages_collection.delete_many({"conversation_id": str(conversation_id)})
        # Delete conversation
        return ai_conversations_collection.delete_one({"_id": ObjectId(conversation_id)})


class AIMessage:
    """Model for messages in AI Assistant conversations"""
    
    @staticmethod
    def create(conversation_id, role, content, attachments=None, image_url=None):
        """
        Create a new message
        role: 'user' or 'assistant'
        content: text content
        attachments: list of file attachments (optional)
        image_url: URL of generated image (optional)
        """
        message_data = {
            "conversation_id": str(conversation_id),
            "role": role,
            "content": content,
            "attachments": attachments or [],
            "image_url": image_url,
            "created_at": datetime.datetime.now(timezone.utc).replace(tzinfo=None),
            "tokens_used": 0  # Will be updated after API call
        }
        result = ai_messages_collection.insert_one(message_data)
        
        # Update conversation timestamp
        AIConversation.update_timestamp(conversation_id)
        
        return result.inserted_id
    
    @staticmethod
    def get_conversation_messages(conversation_id, limit=100):
        """Get all messages for a conversation"""
        return list(
            ai_messages_collection.find({"conversation_id": str(conversation_id)})
            .sort("created_at", 1)
            .limit(limit)
        )
    
    @staticmethod
    def update_tokens(message_id, tokens_used):
        """Update token count for a message"""
        return ai_messages_collection.update_one(
            {"_id": ObjectId(message_id)},
            {"$set": {"tokens_used": tokens_used}}
        )
    
    @staticmethod
    def delete(message_id):
        """Delete a message"""
        return ai_messages_collection.delete_one({"_id": ObjectId(message_id)})
    
    @staticmethod
    def get_recent_context(conversation_id, limit=10):
        """Get recent messages for context (for continuing conversation)"""
        messages = list(
            ai_messages_collection.find({"conversation_id": str(conversation_id)})
            .sort("created_at", -1)
            .limit(limit)
        )
        # Reverse to get chronological order
        return list(reversed(messages))
