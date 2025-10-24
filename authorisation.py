import os
import requests
import subprocess
from vars import OWNER, CREDIT, AUTH_USERS, TOTAL_USERS
from pyrogram import Client, filters
from pyrogram.types import Message

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

async def add_auth_user(client: Client, message: Message):
    if message.chat.id != OWNER:
        return 
    try:
        new_user_id = int(message.command[1])
        if new_user_id in AUTH_USERS:
            await message.reply_text("**User ID is already authorized.**")
        else:
            AUTH_USERS.append(new_user_id)
            await message.reply_text(f"**User ID `{new_user_id}` added to authorized users.**")
            await client.send_message(chat_id=new_user_id, text=f"<b>Great! You are added in Premium Membership!</b>")
    except (IndexError, ValueError):
        await message.reply_text("**Please provide a valid user ID.**")
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

async def list_auth_users(client: Client, message: Message):
    if message.chat.id != OWNER:
        return
    
    user_list = '\n'.join(map(str, AUTH_USERS))  # AUTH_USERS ki list dikhayenge
    await message.reply_text(f"**Authorized Users:**\n{user_list}")
  
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

async def remove_auth_user(client: Client, message: Message):
    if message.chat.id != OWNER:
        return
    
    try:
        user_id_to_remove = int(message.command[1])
        if user_id_to_remove not in AUTH_USERS:
            await message.reply_text("**User ID is not in the authorized users list.**")
        else:
            AUTH_USERS.remove(user_id_to_remove)
            await message.reply_text(f"**User ID `{user_id_to_remove}` removed from authorized users.**")
            await client.send_message(chat_id=user_id_to_remove, text=f"<b>Oops! You are removed from Premium Membership!</b>")
    except (IndexError, ValueError):
        await message.reply_text("**Please provide a valid user ID.**")
          
