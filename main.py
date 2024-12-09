import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
)
from models import session, User, Course, CourseUser

# Load environment variables
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

# States for completing profile, adding a course, and course enrollment
PROFILE_FIRST_NAME, PROFILE_LAST_NAME, PROFILE_ID = range(3)
COURSE_NAME, UNIVERSITY_NAME, SEMESTER = range(3)
SELECT_COURSE = range(1)

# Constants
MAIN_MENU_TEACHER = [["Add a Course"], ["My Courses"], ["Back to Main Menu"]]
MAIN_MENU_STUDENT = [["My Courses"], ["All Courses"], ["Back to Main Menu"]]
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

# Handler for 'All Courses'
async def all_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    courses = session.query(Course).all()
    if not courses:
        await update.message.reply_text("No courses are currently available.")
        return ConversationHandler.END

    course_buttons = [[course.name] for course in courses]
    reply_markup = ReplyKeyboardMarkup(course_buttons, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Here are all available courses. Select a course to request enrollment:",
        reply_markup=reply_markup
    )
    return SELECT_COURSE

async def select_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    course_name = update.message.text.strip()
    course = session.query(Course).filter_by(name=course_name).first()

    if not course:
        await update.message.reply_text("Invalid course selection. Please try again.")
        return SELECT_COURSE

    # Get the student
    student_id = update.effective_user.id
    student = session.query(User).filter_by(telegram_id=student_id).first()

    # Check if the student is already enrolled
    existing_enrollment = session.query(CourseUser).filter_by(user_id=student.id, course_id=course.id).first()
    if existing_enrollment:
        await update.message.reply_text("You are already enrolled in this course.")
    else:
        # Add enrollment to CourseUser table
        new_enrollment = CourseUser(user_id=student.id, course_id=course.id)
        session.add(new_enrollment)
        session.commit()

        await update.message.reply_text(f"You have been enrolled in '{course.name}' successfully!")

    await show_student_menu(update)
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

    # Course enrollment conversation handler
    all_courses_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^All Courses$'), all_courses)],
        states={
            SELECT_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_course)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(profile_handler)
    application.add_handler(all_courses_handler)

    # Run the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
