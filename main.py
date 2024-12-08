from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
)
from models import session, User

# Replace with your bot's API Token
API_TOKEN = "8187999033:AAGMmC6m_WJ205WrxOIrgHRQiU77r7JzZKk"

# Define conversation states
FIRST_NAME, LAST_NAME, UNIVERSITY_ID = range(3)

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Check if the user already exists
    existing_user = session.query(User).filter_by(telegram_id=user_id).first()
    if not existing_user:
        # New user, ask for role
        keyboard = [['I am student', 'I am teacher']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            'Hi! Please select your role:', 
            reply_markup=reply_markup
        )
    elif existing_user.first_name and existing_user.last_name and existing_user.id_in_university:
        # Profile already completed
        await update.message.reply_text('Welcome back! Your profile is already complete.')
    else:
        # Profile incomplete, trigger profile completion
        await update.message.reply_text(
            'Please complete your profile by entering your details. What is your first name?'
        )
        return FIRST_NAME

# Role selection handler
async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = update.message.text.strip()

    # Validate role input
    if role not in ['I am student', 'I am teacher']:
        await update.message.reply_text("Invalid selection. Please choose 'I am student' or 'I am teacher'.")
        return

    # Save user role in the database
    is_teacher = True if role == 'I am teacher' else False
    existing_user = session.query(User).filter_by(telegram_id=user_id).first()

    if existing_user:
        await update.message.reply_text("You are already registered!")
        return

    user = User(telegram_id=user_id, is_teacher=is_teacher)
    session.add(user)
    session.commit()

    await update.message.reply_text(
        "Thank you! Now let's complete your profile. What is your first name?"
    )
    return FIRST_NAME  # Move to the profile completion state

# Conversation handler for first name
async def first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['first_name'] = update.message.text.strip()
    await update.message.reply_text("Great! What is your last name?")
    return LAST_NAME

# Conversation handler for last name
async def last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['last_name'] = update.message.text.strip()
    await update.message.reply_text("Finally, please enter your university ID:")
    return UNIVERSITY_ID

# Conversation handler for university ID
async def university_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    university_id = update.message.text.strip()

    # Validate university ID as an integer
    if not university_id.isdigit():
        await update.message.reply_text("University ID must be a number. Please try again.")
        return UNIVERSITY_ID

    # Update the user's profile in the database
    user = session.query(User).filter_by(telegram_id=user_id).first()
    if user:
        user.first_name = context.user_data['first_name']
        user.last_name = context.user_data['last_name']
        user.id_in_university = int(university_id)
        session.commit()

        await update.message.reply_text(
            f"Profile completed successfully!\n"
            f"First Name: {user.first_name}\n"
            f"Last Name: {user.last_name}\n"
            f"University ID: {user.id_in_university}",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text("An error occurred. Please try again later.")
    return ConversationHandler.END

# Handle conversation cancellation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Profile setup cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Main function
def main():
    # Create the bot application
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Define the conversation handler for profile completion
    profile_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.Regex('^(I am student|I am teacher)$'), set_role)],
        states={
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, last_name)],
            UNIVERSITY_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, university_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Add handlers
    application.add_handler(profile_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, set_role))

    # Run the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
