from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from models import session, User

# Replace with your actual bot token
API_TOKEN = '8187999033:AAGMmC6m_WJ205WrxOIrgHRQiU77r7JzZKk'

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if user already exists
    existing_user = session.query(User).filter_by(telegram_id=user_id).first()
    if not existing_user:
        # If user is new, prompt them to select their role
        keyboard = [['I am student', 'I am teacher']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            'Hi! Please select your role:', 
            reply_markup=reply_markup
        )
    else:
        # Greet the user based on their saved role
        role = existing_user.role
        if role == "student":
            await update.message.reply_text('Welcome student! You can access your courses.')
        else:
            await update.message.reply_text('Welcome teacher! You can manage your courses.')

# Message handler to set user role
async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = update.message.text.strip()

    # Check for valid role input
    if role not in ['I am student', 'I am teacher']:
        await update.message.reply_text("Invalid selection. Please choose 'I am student' or 'I am teacher'.")
        return

    # Save user role to database
    existing_user = session.query(User).filter_by(telegram_id=user_id).first()
    if existing_user:
        await update.message.reply_text("You are already registered!")
        return

    new_role = role.lower().replace('i am ', '')
    user = User(telegram_id=user_id, role=new_role)
    session.add(user)
    session.commit()

    await update.message.reply_text(f'You are now registered as a {new_role}!')

# Main function to run the bot
def main():
    # Create the bot application
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Add command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, set_role))

    # Run the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
