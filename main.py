import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
)
from models import session, User, Course

# Load environment variables
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

# States for completing profile and adding a course
PROFILE_FIRST_NAME, PROFILE_LAST_NAME, PROFILE_ID = range(3)
COURSE_NAME, UNIVERSITY_NAME, SEMESTER = range(3)

# Constants
MAIN_MENU_TEACHER = [["Add a Course"], ["View Courses"], ["Back to Role Selection"]]
MAIN_MENU_STUDENT = [["View My Courses"], ["Back to Role Selection"]]
ROLE_SELECTION = [["I am Teacher"], ["I am Student"]]

# ---- Handlers ----

# START: Main handler when /start is triggered
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    existing_user = session.query(User).filter_by(telegram_id=user_id).first()

    if not existing_user:
        # If user is not registered, prompt for role selection
        reply_markup = ReplyKeyboardMarkup(ROLE_SELECTION, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Welcome! Please select your role to continue:",
            reply_markup=reply_markup
        )
    else:
        # Registered user -> show main menu based on role
        if existing_user.is_teacher:
            await show_teacher_menu(update)
        else:
            await show_student_menu(update)

# Role selection handler
async def role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = update.message.text

    # Register user based on role
    is_teacher = True if role == "I am Teacher" else False
    new_user = User(telegram_id=user_id, is_teacher=is_teacher)
    session.add(new_user)
    session.commit()

    await update.message.reply_text(
        "Registration successful! Please complete your profile.\nEnter your *First Name*:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return PROFILE_FIRST_NAME

# Profile completion steps
async def profile_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['first_name'] = update.message.text.strip()
    await update.message.reply_text("Enter your *Last Name*:", parse_mode="Markdown")
    return PROFILE_LAST_NAME

async def profile_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['last_name'] = update.message.text.strip()
    await update.message.reply_text("Enter your *University ID*:", parse_mode="Markdown")
    return PROFILE_ID

async def profile_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = session.query(User).filter_by(telegram_id=user_id).first()

    user.first_name = context.user_data['first_name']
    user.last_name = context.user_data['last_name']
    user.id_in_university = update.message.text.strip()
    session.commit()

    await update.message.reply_text(
        "Profile completed successfully!",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU_TEACHER if user.is_teacher else MAIN_MENU_STUDENT, resize_keyboard=True)
    )
    return ConversationHandler.END

# Show teacher menu
async def show_teacher_menu(update: Update):
    reply_markup = ReplyKeyboardMarkup(MAIN_MENU_TEACHER, resize_keyboard=True)
    await update.message.reply_text("Welcome to the Teacher Menu:", reply_markup=reply_markup)

# Show student menu
async def show_student_menu(update: Update):
    reply_markup = ReplyKeyboardMarkup(MAIN_MENU_STUDENT, resize_keyboard=True)
    await update.message.reply_text("Welcome to the Student Menu:", reply_markup=reply_markup)

# Handler for 'Add a Course'
async def add_course_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Let's add a new course!\nPlease enter the *Course Name*:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return COURSE_NAME

async def add_course_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['course_name'] = update.message.text.strip()
    await update.message.reply_text("Enter the *University Name*:", parse_mode="Markdown")
    return UNIVERSITY_NAME

async def add_university_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['university_name'] = update.message.text.strip()
    await update.message.reply_text("Enter the *Semester* in format Fall/Spring-Year (e.g. Fall-2024):", parse_mode="Markdown")
    return SEMESTER

async def add_semester(update: Update, context: ContextTypes.DEFAULT_TYPE):
    semester = update.message.text.strip()
    # if semester not in ["Fall", "Spring"]:
    #     await update.message.reply_text("Invalid semester. Please enter 'Fall' or 'Spring':")
    #     return SEMESTER

    # Save course to database
    user_id = update.effective_user.id
    teacher = session.query(User).filter_by(telegram_id=user_id).first()

    new_course = Course(
        name=context.user_data['course_name'],
        university=context.user_data['university_name'],
        semester=semester,
        teacher_id=teacher.id
    )
    session.add(new_course)
    session.commit()

    await update.message.reply_text(
        f"Course '{new_course.name}' added successfully!",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU_TEACHER, resize_keyboard=True)
    )
    return ConversationHandler.END

# Cancel operation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ---- Main Function ----
def main():
    # Create bot application
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Profile conversation handler
    profile_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^(I am Teacher|I am Student)$'), role_selection)],
        states={
            PROFILE_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_first_name)],
            PROFILE_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_last_name)],
            PROFILE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Course addition conversation handler
    add_course_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Add a Course$'), add_course_start)],
        states={
            COURSE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_course_name)],
            UNIVERSITY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_university_name)],
            SEMESTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_semester)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(profile_handler)
    application.add_handler(add_course_handler)

    # Run the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
