import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.helpers import escape_markdown
from ..services.user_service import UserService
from ..services.quiz_service import QuizService
from ..services.course_service import CourseService

logger = logging.getLogger(__name__)

from telegram.ext import ConversationHandler, MessageHandler, filters

# Conversation States
START_MODE, ASK_NICKNAME, ASK_PASSWORD, LOGIN_NICKNAME, LOGIN_PASSWORD = range(5)
# Quiz Conversation States
SELECT_WEEK, SELECT_QUIZ, QUIZ_INFO, QUIZ_QUESTION = range(5, 9)
# Feedback State
COLLECT_FEEDBACK = 10
# Course Selection States
COURSE_SELECT, WEEK_SELECT, CONTENT_OPTIONS, COURSE_QUIZ_SELECT = range(11, 15)
# Settings & Delete States
SETTINGS_MODE, CONFIRM_DELETE = range(15, 17)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command."""
    await update.message.reply_text(
        "Available Commands:\n"
        "/quiz - Browse timed quizzes by week\n"
        "/stats - Check your score and rank\n"
        "/leaderboard - View the ranking\n"
        "/forgot - Recover your password if registered\n"
        "/logout - Sign out from your current account\n"
        "/start - Register or login to another account"
    )

async def check_user_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is registered and provide helpful guidance if not."""
    user = UserService.get_or_create_user(update.effective_user.id, update.effective_user.username, update.effective_user.full_name)
    
    if not UserService.is_registered(update.effective_user.id):
        # Check if user exists but missing registration details
        if user.nickname is None:
            await update.message.reply_text(
                "🛑 *Registration Required*\n\n"
                "You need to complete your registration before taking quizzes.\n\n"
                "Please use /start to finish setting up your account with a nickname and password.\n\n"
                "If you already have an account, use /start and choose 'Login' to access your existing profile.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "🔧 *Account Setup Incomplete*\n\n"
                "Your account is missing some required information.\n\n"
                "Please use /start to complete your registration.",
                parse_mode="Markdown"
            )
        return False
    return True

async def quizzes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for browsing structured quizzes."""
    if not await check_user_registration(update, context):
        return ConversationHandler.END

    # Standard 12 weeks in a grid
    keyboard = []
    for i in range(1, 13, 3):
        keyboard.append([
            InlineKeyboardButton(f"Week {i}", callback_data=f"std_week_{i}"),
            InlineKeyboardButton(f"Week {i+1}", callback_data=f"std_week_{i+1}"),
            InlineKeyboardButton(f"Week {i+2}", callback_data=f"std_week_{i+2}")
        ])
    
    # Special categories
    keyboard.append([
        InlineKeyboardButton("🎓 Mid Exam", callback_data="std_week_13"),
        InlineKeyboardButton("🏆 Final Exam", callback_data="std_week_14")
    ])
    keyboard.append([InlineKeyboardButton("🤡 Funny Question", callback_data="std_week_15")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📚 *Browse Quizzes*\nSelect a week or category to see available challenges:", 
                                   reply_markup=reply_markup, parse_mode="Markdown")
    return SELECT_WEEK

async def std_select_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    week = int(query.data.split('_')[2])
    
    quizzes = QuizService.get_quizzes_by_week(week)
    if not quizzes:
        await query.edit_message_text(f"ℹ️ No quizzes available for Week {week} yet. Check back later!")
        return ConversationHandler.END
        
    week_name = f"Week {week}" if week <= 12 else "Mid Exam" if week == 13 else "Final Exam" if week == 14 else "Funny Question"
    
    keyboard = [[InlineKeyboardButton(q.title, callback_data=f"std_quiz_{q.id}")] for q in quizzes]
    keyboard.append([InlineKeyboardButton("⬅️ Back to Categories", callback_data="back_to_weeks")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"📅 *{week_name} Quizzes*\nChoose a quiz to view details:", 
                                 reply_markup=reply_markup, parse_mode="Markdown")
    return SELECT_QUIZ

async def show_week_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show week selection for callback queries (used in navigation)"""
    query = update.callback_query
    
    # Standard 12 weeks in a grid
    keyboard = []
    for i in range(1, 13, 3):
        keyboard.append([
            InlineKeyboardButton(f"Week {i}", callback_data=f"std_week_{i}"),
            InlineKeyboardButton(f"Week {i+1}", callback_data=f"std_week_{i+1}"),
            InlineKeyboardButton(f"Week {i+2}", callback_data=f"std_week_{i+2}")
        ])
    
    # Special categories
    keyboard.append([
        InlineKeyboardButton("🎓 Mid Exam", callback_data="std_week_13"),
        InlineKeyboardButton("🏆 Final Exam", callback_data="std_week_14")
    ])
    keyboard.append([InlineKeyboardButton("🤡 Funny Question", callback_data="std_week_15")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📚 *Browse Quizzes*\nSelect a week or category to see available challenges:", 
                                   reply_markup=reply_markup, parse_mode="Markdown")
    return SELECT_WEEK

async def std_quiz_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_weeks":
        return await show_week_selection(update, context)

    quiz_id = int(query.data.split('_')[2])
    quiz = QuizService.get_quiz(quiz_id)
    questions = QuizService.get_quiz_questions(quiz_id)
    
    context.user_data['active_quiz'] = quiz
    context.user_data['quiz_questions'] = questions
    
    info_text = (
        f"📝 *{quiz.title}*\n\n"
        f"ℹ️ {quiz.description}\n"
        f"📅 Week: {quiz.week_number}\n"
        f"⏱ Duration: {quiz.duration_minutes} minutes\n"
        f"❓ Questions: {len(questions)}\n\n"
        "Ready to start? The timer begins as soon as you click the button below!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 Start Quiz Now", callback_data="start_confirmed")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"std_week_{quiz.week_number}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode="Markdown")
    return QUIZ_INFO

async def start_timed_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    quiz = context.user_data['active_quiz']
    user = UserService.get_or_create_user(update.effective_user.id)
    attempt = QuizService.start_quiz_attempt(user.id, quiz.id)
    
    context.user_data['quiz_start_time'] = datetime.utcnow()
    context.user_data['quiz_index'] = 0
    context.user_data['quiz_score'] = 0
    context.user_data['quiz_attempt_id'] = attempt.id
    
    return await send_next_quiz_question(update, context)

async def send_next_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    index = context.user_data['quiz_index']
    questions = context.user_data['quiz_questions']
    quiz = context.user_data['active_quiz']
    
    if index >= len(questions):
        return await finish_timed_quiz(update, context)
        
    # Check time
    total_seconds = (datetime.utcnow() - context.user_data['quiz_start_time']).total_seconds()
    remaining_seconds = max(0, (quiz.duration_minutes * 60) - total_seconds)
    
    if remaining_seconds <= 0:
        await query.message.reply_text("⏰ *Time's up!* The quiz has ended.", parse_mode="Markdown")
        return await finish_timed_quiz(update, context)

    mins = int(remaining_seconds // 60)
    secs = int(remaining_seconds % 60)

    question = questions[index]
    
    # Build question UI
    keyboard = [
        [
            InlineKeyboardButton("A", callback_data=f"t_ans_{index}_A"),
            InlineKeyboardButton("B", callback_data=f"t_ans_{index}_B")
        ],
        [
            InlineKeyboardButton("C", callback_data=f"t_ans_{index}_C"),
            InlineKeyboardButton("D", callback_data=f"t_ans_{index}_D")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    q_text = (
        f"⏱ *Time Remaining: {mins}m {secs}s*\n"
        f"📊 *Question {index+1}/{len(questions)}*\n\n"
        f"{question.question_text}\n\n"
        f"A) {question.option_a}\n"
        f"B) {question.option_b}\n"
        f"C) {question.option_c}\n"
        f"D) {question.option_d}"
    )
    
    if query.message.text == q_text: # Avoid "Message is not modified"
        pass 
    
    await query.edit_message_text(q_text, reply_markup=reply_markup, parse_mode="Markdown")
    return QUIZ_QUESTION

async def handle_timed_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    index = int(data[2])
    selected = data[3]
    
    questions = context.user_data['quiz_questions']
    question = questions[index]
    quiz = context.user_data['active_quiz']
    
    # Strict time check
    elapsed = (datetime.utcnow() - context.user_data['quiz_start_time']).total_seconds() / 60
    if elapsed > quiz.duration_minutes:
        await query.edit_message_text("⏰ *Time's up!* This answer was not counted.", parse_mode="Markdown")
        return await finish_timed_quiz(update, context)
    
    if selected.upper() == question.correct_answer.upper():
        context.user_data['quiz_score'] += 1
        
    # Record submission anyway
    user = UserService.get_or_create_user(update.effective_user.id)
    QuizService.submit_answer(
        user_id=user.id,
        telegram_id=user.telegram_id,
        question_id=question.id,
        selected_answer=selected
    )
    
    context.user_data['quiz_index'] += 1
    return await send_next_quiz_question(update, context)

async def finish_timed_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    score = context.user_data['quiz_score']
    total = len(context.user_data['quiz_questions'])
    quiz = context.user_data['active_quiz']
    attempt_id = context.user_data.get('quiz_attempt_id')
    
    duration_mins = (datetime.utcnow() - context.user_data['quiz_start_time']).total_seconds() / 60
    accuracy = (score / total * 100) if total > 0 else 0
    
    # Update Stats
    UserService.update_streak(update.effective_user.id)
    
    # Award Badges
    new_badges = []
    if accuracy == 100:
        UserService.add_badge(update.effective_user.id, "🎯 Sharpshooter")
        new_badges.append("🎯 Sharpshooter")
    
    # Speed Demon: If finished in less than 25% of the allotted time
    if duration_mins < (quiz.duration_minutes * 0.25) and total >= 5:
        UserService.add_badge(update.effective_user.id, "⚡ Speed Demon")
        new_badges.append("⚡ Speed Demon")

    if attempt_id:
        QuizService.finish_quiz_attempt(attempt_id, score)
    
    # Fetch updated user for streak/badges
    user = UserService.get_or_create_user(update.effective_user.id)
    badge_text = f"\n🎖 New Badge: {', '.join(new_badges)}!" if new_badges else ""

    await query.edit_message_text(
        f"🏁 *Quiz Finished!* 🏁\n\n"
        f"🏆 Quiz: {quiz.title}\n"
        f"✅ Correct: {score}/{total}\n"
        f"📈 Accuracy: {int(accuracy)}%\n"
        f"⏱ Time: {round(duration_mins, 1)} minutes\n"
        f"🔥 Streak: {user.streak_count} days\n"
        f"{badge_text}\n"
        "Well done! Your performance has been recorded on the leaderboard.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def forgot_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles password recovery via Telegram Handle check."""
    user = update.effective_user
    password = UserService.recover_password(user.id, user.username)
    
    if password:
        await update.message.reply_text(
            f"🔑 *Password Recovery Successful!*\n\n"
            f"Your access password is: `{password}`\n\n"
            "_Keep this safe!_",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ *Recovery Failed*\n\n"
            "I couldn't find an account associated with this Telegram handle.\n"
            "If your Telegram username has changed since registration, please contact your instructor.",
            parse_mode="Markdown"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command - Entry point for Register/Login."""
    from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
    user = update.effective_user
    db_user = UserService.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        full_name=user.full_name
    )
    
    if UserService.is_registered(user.id):
        # Show main menu for registered users
        return await show_main_menu(update, context, db_user.nickname)

    reply_keyboard = [['🆕 New Student', '📲 Login (Existing Account)']]
    welcome_msg = (
        "🤖 *Welcome to the C++ Mastery Bot!* 🚀\n\n"
        "I will help you master C++ through interactive challenges.\n"
        "Please choose how you want to continue:"
    )
    await update.message.reply_text(
        welcome_msg, 
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return START_MODE

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, nickname=None):
    """Show the main menu with Reply Keyboard for registered users."""
    from telegram import ReplyKeyboardMarkup
    
    if nickname is None:
        user = UserService.get_user(update.effective_user.id)
        nickname = user.nickname if user else "User"
    
    # Create main menu keyboard with exactly 5 categories as requested
    main_keyboard = [
        ['📚 Courses', '📝 Quizzes'],
        ['📊 My Status', '🏆 Leaderboard'],
        ['⚙️ Settings']
    ]
    
    esc_nickname = escape_markdown(nickname, version=1)
    welcome_msg = (
        f"👋 Welcome back, *{esc_nickname}*! 👋\n\n"
        f"🚀 Ready to master C++? Choose an option below:"
    )
    
    await update.message.reply_text(
        welcome_msg,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END

async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the settings submenu."""
    from telegram import ReplyKeyboardMarkup
    settings_keyboard = [
        ['👤 Edit Profile', '🔐 Forgot Password'],
        ['🚪 Logout', '🗑️ Delete Account'],
        ['🔙 Back to Main Menu', '💬 Give Feedback'],
        ['❓ Help']
    ]
    
    await update.message.reply_text(
        "⚙️ *Settings*\nManage your profile and account settings:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(settings_keyboard, resize_keyboard=True)
    )
    return SETTINGS_MODE

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu keyboard choices."""
    choice = update.message.text
    
    if choice == '📝 Quizzes':
        return await quizzes_command(update, context)
    elif choice == '📊 My Status':
        return await stats_command(update, context)
    elif choice == '🏆 Leaderboard':
        return await leaderboard_command(update, context)
    elif choice == '⚙️ Settings':
        return await show_settings_menu(update, context)
    elif choice == '📚 Courses':
        return await show_courses(update, context)
    else:
        # Unknown choice or fallback
        await update.message.reply_text("❓ Please choose one of the options from the menu below:")
        return await show_main_menu(update, context)

async def handle_settings_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle choices within the settings submenu."""
    choice = update.message.text
    
    if choice == '👤 Edit Profile':
        await update.message.reply_text("👤 *Profile Edit*\n\nThis feature is coming soon! 🚧", parse_mode="Markdown")
        return SETTINGS_MODE
    elif choice == '🔐 Forgot Password':
        await forgot_password(update, context)
        return SETTINGS_MODE
    elif choice == '🚪 Logout':
        await logout_command(update, context)
        return ConversationHandler.END
    elif choice == '🗑️ Delete Account':
        await update.message.reply_text(
            "⚠️ *CAUTION*: You are about to delete your account.\n\n"
            "This will permanently erase your score, streak, and history. "
            "This action *cannot* be undone.\n\n"
            "Are you sure? Type 'CONFIRM DELETE' to proceed or anything else to go back.",
            parse_mode="Markdown"
        )
        return CONFIRM_DELETE
    elif choice == '💬 Give Feedback':
        return await start_feedback(update, context)
    elif choice == '❓ Help':
        await help_command(update, context)
        return SETTINGS_MODE
    elif choice == '🔙 Back to Main Menu':
        return await show_main_menu(update, context)
    else:
        await update.message.reply_text("❓ Please choose an option from the settings menu:")
        return await show_settings_menu(update, context)

async def confirm_account_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the final account deletion confirmation."""
    text = update.message.text.strip()
    
    if text == "CONFIRM DELETE":
        success = UserService.delete_user_account(update.effective_user.id)
        if success:
            from telegram import ReplyKeyboardRemove
            await update.message.reply_text(
                "🗑️ *Account Deleted*\nYour data has been erased. Goodbye!", 
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text("❌ *Error*: Could not delete account. Please try again later.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Deletion aborted. Returning to Settings.")
        return await show_settings_menu(update, context)

async def choose_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the mode selection (New vs Existing)."""
    choice = update.message.text
    from telegram import ReplyKeyboardRemove
    
    if choice == '🆕 New Student':
        await update.message.reply_text(
            "1️⃣ *First*, what name or nickname should I show on the leaderboard?",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASK_NICKNAME
    elif choice == '📲 Login (Existing Account)':
        await update.message.reply_text(
            "🔑 *Login* 🔑\n\n"
            "Please enter the *Nickname* of your existing account:",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        return LOGIN_NICKNAME
    else:
        await update.message.reply_text("Please use the buttons provided.")
        return START_MODE

async def save_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the nickname and checks for uniqueness."""
    nickname = update.message.text.strip()
    if len(nickname) < 2 or len(nickname) > 20:
        await update.message.reply_text("⚠️ Please enter a name between 2 and 20 characters.")
        return ASK_NICKNAME
    
    # Check if nickname already taken
    existing = UserService.get_user_by_nickname(nickname)
    if existing:
        await update.message.reply_text("❌ This nickname is already taken. Please try another one:")
        return ASK_NICKNAME
    
    context.user_data['nickname'] = nickname
    esc_nickname = escape_markdown(nickname, version=1)
    await update.message.reply_text(
        f"Nice to meet you, *{esc_nickname}*! 😊\n\n"
        "2️⃣ *Finally*, please enter the access password to unlock the quizzes:",
        parse_mode="Markdown"
    )
    return ASK_PASSWORD

async def login_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the nickname for login."""
    nickname = update.message.text.strip()
    context.user_data['login_nickname'] = nickname
    await update.message.reply_text(f"Logging in as `{nickname}`. Please enters your password:")
    return LOGIN_PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the password for login and links account."""
    password = update.message.text.strip()
    nickname = context.user_data.get('login_nickname')
    
    success = UserService.link_account(nickname, password, update.effective_user.id)
    
    if success:
        esc_nickname = escape_markdown(nickname, version=1)
        await update.message.reply_text(
            f"✅ *Login Successful!* 🎉\n\n"
            f"Welcome back, {esc_nickname}. Your progress and scores have been transferred to this device.",
            parse_mode="Markdown"
        )
        return await show_main_menu(update, context, nickname)
    else:
        await update.message.reply_text(
            "❌ *Login Failed*\n\n"
            "Incorrect Nickname or Password. Please try again from /start."
        )
        return ConversationHandler.END

async def finish_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifies password and completes registration."""
    password = update.message.text.strip()
    from ..config import Config
    
    # In a real app, we might check against a database of course passwords,
    # but for now, we use a global student password from config.
    expected_password = Config.STUDENT_ACCESS_PASSWORD
    
    if password != expected_password:
        await update.message.reply_text(
            "❌ *Incorrect password!*\n"
            "Please try again or contact your instructor for the code.",
            parse_mode="Markdown"
        )
        return ASK_PASSWORD
    
    nickname = context.user_data.get('nickname')
    UserService.update_registration(update.effective_user.id, nickname, password)
    
    success_msg = (
        "✅ *Registration Complete!* 🎉\n\n"
        "You now have full access to the C++ Mastery Bot.\n\n"
        "Commands:\n"
        "🚀 /quiz - Start a quick quiz\n"
        "📊 /stats - View your progress\n"
        "🏆 /leaderboard - See the top students\n"
        "ℹ️ /help - Show available commands"
    )
    await update.message.reply_text(success_msg, parse_mode="Markdown")
    return await show_main_menu(update, context, nickname)

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the registration process."""
    await update.message.reply_text(
        "🚫 Registration cancelled. You won't be able to access the quizzes until you register via /start."
    )
    return ConversationHandler.END

# Removed old random quiz_command in favor of structured sessions.

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles quiz answer button clicks."""
    query = update.callback_query
    await query.answer()
    
    # Data format: quiz_ans_{question_id}_{selected_option}
    data = query.data.split('_')
    question_id = int(data[2])
    selected_option = data[3]
    
    telegram_id = update.effective_user.id
    db_user = UserService.get_or_create_user(telegram_id)
    
    try:
        submission = QuizService.submit_answer(
            user_id=db_user.id,
            telegram_id=telegram_id,
            question_id=question_id,
            selected_answer=selected_option
        )
        
        if submission.is_correct:
            result_text = "✅ *Correct!* Well done."
        else:
            result_text = f"❌ *Incorrect.*"
            # Optional: Add explanation here if available in model
            
        await query.edit_message_text(
            f"{query.message.text}\n\n{result_text}",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error processing answer: {e}")
        await query.message.reply_text("⚠️ An error occurred while processing your answer.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /stats command with a rich visual layout."""
    if not await check_user_registration(update, context):
        return
    
    user = UserService.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("❌ User not found. Please use /start to register.")
        return
    
    stats = UserService.get_user_stats(user.id)
    
    # Progress Bar Calculation
    xp_in_level = stats.get('xp_in_level', 0)
    xp_needed = stats.get('xp_needed', 100)
    filled_length = int(10 * xp_in_level // xp_needed)
    bar = "▬▬" * filled_length + "▭▭" * (10 - filled_length)
    
    # Titles based on Level
    level = stats.get('level', 1)
    title = "Novice" if level < 5 else "Apprentice" if level < 10 else "Scholar" if level < 20 else "Master"
    
    # Badge formatting
    badges = stats.get('badges', [])
    badge_text = " ".join(badges) if badges else "None yet 🎖"

    stats_msg = (
        f"📊 *{user.nickname}'s Student Profile* 📊\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *Rank*: #{stats.get('rank', 'N/A')} | {title}\n"
        f"🎖 *Level*: {level}\n"
        f"✨ *XP*: {xp_in_level}/{xp_needed}\n"
        f"`{bar}`\n\n"
        f"📈 *Performance Metrics*\n"
        f"  ├ ✅ Accuracy: {stats.get('avg_accuracy', 0)}%\n"
        f"  ├ ⏱ Avg Time: {stats.get('avg_time', 0)}m\n"
        f"  └ 📝 Total Quizzes: {stats.get('total_quizzes', 0)}\n\n"
        f"🔥 *Consistency*\n"
        f"  ├ 🔥 Daily Streak: {stats.get('streak_count', 0)} days\n"
        f"  └ 🏆 Total Score: {user.score} XP\n\n"
        f"🎖 *Achievements*\n"
        f"  {badge_text}\n\n"
        f"🚀 _Keep learning to climb the leaderboard!_"
    )
    
    await update.message.reply_text(stats_msg, parse_mode="Markdown")
    return ConversationHandler.END

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /leaderboard command."""
    if not await check_user_registration(update, context):
        return
    
    # Get overall leaderboard
    leaderboard = UserService.get_overall_leaderboard(limit=10)
    
    if not leaderboard:
        await update.message.reply_text("🏆 No quiz data available yet. Be the first to take a quiz!")
        return
    
    lb_text = "🏆 *Overall Leaderboard* 🏆\n\n"
    
    for i, user in enumerate(leaderboard, 1):
        icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        streak_icon = " 🔥" if user.get('streak_count', 0) >= 3 else ""
        lb_text += f"{icon} *{user['nickname']}*{streak_icon}\n"
        lb_text += f"   └ 📝 {user['total_quizzes']} quizzes | 🎯 {user['avg_accuracy']}% avg\n"
    
    lb_text += "\n🚀 _Complete more quizzes to climb the ranks!_"
    
    await update.message.reply_text(lb_text, parse_mode="Markdown")
    return ConversationHandler.END

async def cls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resets the user session and clears the menu."""
    from telegram import ReplyKeyboardRemove
    
    # Clear session data
    context.user_data.clear()
    
    # Send a clearing message (lots of empty space) followed by reset confirmation
    # This pushes old messages out of view
    clearing_text = "\n" * 50 + "🧹 *System Reset Complete*\nSession cleared and menu removed. Use /start to begin again."
    
    await update.message.reply_text(
        clearing_text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /logout command."""
    user_id = update.effective_user.id
    
    # Actually perform the logout in the database
    UserService.logout_user(user_id)
    
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(
        "🚪 *Logged Out successfully.*\nAll personal data access from this session has been restricted.\n\n"
        "Use /start to log back in or create a new account.", 
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def start_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the feedback collection process."""
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(
        "📝 *Give Feedback*\n\n"
        "Please share your suggestions, questions, or comments about the course or the bot below.\n"
        "Type /cancel to abort.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return COLLECT_FEEDBACK

async def collect_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects and saves the feedback."""
    content = update.message.text.strip()
    user = UserService.get_user(update.effective_user.id)
    
    if user:
        UserService.add_feedback(user.id, content)
        await update.message.reply_text("✅ *Thank you for your feedback!* Your suggestion has been saved.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ *Error*: User not found. Please log in first.", parse_mode="Markdown")
        
    return await show_main_menu(update, context)

# --- Course & Week Menu System ---

async def show_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Level 1: Course Selection Menu"""
    # Define courses
    courses = [
        ("C++", "course_cpp"),
        ("Python", "course_python"),
        ("Web Dev", "course_webdev")
    ]
    
    keyboard = []
    for name, callback_data in courses:
        keyboard.append([InlineKeyboardButton(name, callback_data=callback_data)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg_text = "📚 *Choose a Course*\nSelect a course below to explore its content:"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")
    
    return COURSE_SELECT

async def handle_course_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles course selection callback."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "course_cpp":
        return await show_weeks(update, context, "C++")
    else:
        # Coming soon for other courses
        await query.message.reply_text("⚠️ *Coming Soon*: This course is currently under development.", parse_mode="Markdown")
        return COURSE_SELECT

async def show_weeks(update: Update, context: ContextTypes.DEFAULT_TYPE, course_name: str):
    """Level 2: Week Selection Menu (Weeks 1-12)"""
    keyboard = []
    # Grid of 3x4
    for i in range(1, 13, 3):
        row = []
        for j in range(3):
            week_num = i + j
            row.append(InlineKeyboardButton(f"Week {week_num}", callback_data=f"week_{week_num}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Courses", callback_data="back_to_courses")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg_text = f"📚 *{course_name} - Week Selection*\nChoose a week to see the learning materials:"
    await update.callback_query.edit_message_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")
    
    context.user_data['selected_course'] = course_name
    return WEEK_SELECT

async def handle_week_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles week selection callback."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "back_to_courses":
        return await show_courses(update, context)
        
    week_num = int(data.split("_")[1])
    context.user_data['selected_week'] = week_num
    
    return await show_content_options(update, context, week_num)

async def show_content_options(update: Update, context: ContextTypes.DEFAULT_TYPE, week_num: int):
    """Level 3: Content Options for a Week"""
    course_name = context.user_data.get('selected_course', 'Course')
    
    keyboard = [
        [InlineKeyboardButton("📄 PDF Materials", callback_data="content_pdf")],
        [InlineKeyboardButton("🎥 Video Lessons", callback_data="content_video")],
        [InlineKeyboardButton("📝 Test your Potential", callback_data="content_test")],
        [InlineKeyboardButton("🌐 Learn on Web", callback_data="content_web")],
        [InlineKeyboardButton("🔙 Back to Weeks", callback_data="back_to_weeks")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg_text = f"📘 *{course_name} - Week {week_num}*\n\nSelect an option below to start learning:"
    await update.callback_query.edit_message_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")
    return CONTENT_OPTIONS

async def handle_content_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles content type selection (PDF, Video, etc.)."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "back_to_weeks":
        course_name = context.user_data.get('selected_course', 'C++')
        return await show_weeks(update, context, course_name)
    
    week_num = context.user_data.get('selected_week')
    course_name = context.user_data.get('selected_course')
    
    course = CourseService.get_course_by_name(course_name)
    content = CourseService.get_weekly_content(course.id, week_num) if course else None
    
    if data == "content_pdf":
        if content and content.pdf_file_id:
            try:
                # Try as file_id first
                await query.message.reply_document(document=content.pdf_file_id, caption=f"📄 Week {week_num} PDF Materials")
            except:
                # Fallback to text link
                await query.message.reply_text(f"📄 *Week {week_num} PDF Materials*:\n{escape_markdown(content.pdf_file_id)}", parse_mode="Markdown")
        else:
            await query.message.reply_text("ℹ️ PDF materials for this week are not yet available.")
            
    elif data == "content_video":
        if content and content.video_link:
            await query.message.reply_text(f"🎥 *Week {week_num} Video Lesson*:\n{escape_markdown(content.video_link)}", parse_mode="Markdown")
        else:
            await query.message.reply_text("ℹ️ Video lessons for this week are not yet available.")
            
    elif data == "content_web":
        if content and content.web_link:
            await query.message.reply_text(f"🌐 *Learn more on the web*:\n{escape_markdown(content.web_link)}", parse_mode="Markdown")
        else:
            # Default or placeholder
            await query.message.reply_text("🌐 *Explore More*:\nClick here for the recommended web learning platform: [Learn C++ Web](https://example.com)", parse_mode="Markdown")
            
    elif data == "content_test":
        # Integrating real quizzes for the week
        from ..services.quiz_service import QuizService
        quizzes = QuizService.get_quizzes_by_week(week_num)
        
        if not quizzes:
            await query.message.reply_text(f"ℹ️ No quizzes available for Week {week_num} yet. Check back later!")
            return CONTENT_OPTIONS
            
        keyboard = [[InlineKeyboardButton(q.title, callback_data=f"std_quiz_{q.id}")] for q in quizzes]
        keyboard.append([InlineKeyboardButton("🔙 Back to Options", callback_data="back_to_options")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text(f"📝 *{course_name} - Week {week_num} Quizzes*\nChoose a challenge to start:", 
                                     reply_markup=reply_markup, parse_mode="Markdown")
        return COURSE_QUIZ_SELECT

    return CONTENT_OPTIONS

async def handle_content_selection_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navigates back from weekly quiz list to week content options."""
    query = update.callback_query
    await query.answer()
    week_num = context.user_data.get('selected_week')
    return await show_content_options(update, context, week_num)

async def handle_quiz_info_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navigates back from quiz info to weekly quiz list."""
    query = update.callback_query
    await query.answer()
    
    week_num = context.user_data.get('selected_week')
    course_name = context.user_data.get('selected_course')
    
    week_name = f"Week {week_num}" if week_num <= 12 else "Mid Exam" if week_num == 13 else "Final Exam" if week_num == 14 else "Funny Question"
    
    quizzes = QuizService.get_quizzes_by_week(week_num)
    keyboard = [[InlineKeyboardButton(q.title, callback_data=f"std_quiz_{q.id}")] for q in quizzes]
    keyboard.append([InlineKeyboardButton("🔙 Back to Options", callback_data="back_to_options")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"📝 *{course_name} - {week_name} Quizzes*\nChoose a challenge to start:", 
                                 reply_markup=reply_markup, parse_mode="Markdown")
    return COURSE_QUIZ_SELECT

# --- Old Quiz Handlers (Kept for /quiz command) ---
quiz_list_handler = ConversationHandler(
    entry_points=[
        CommandHandler("quizzes", quizzes_command),
        CommandHandler("quiz", quizzes_command),
        MessageHandler(filters.Regex('^📝 Quizzes$'), quizzes_command)
    ],
    states={
        SELECT_WEEK: [CallbackQueryHandler(std_select_week, pattern="^std_week_")],
        SELECT_QUIZ: [
            CallbackQueryHandler(std_quiz_info, pattern="^std_quiz_"),
            CallbackQueryHandler(std_select_week, pattern="^std_week_"), # Redundant but safe
            CallbackQueryHandler(std_quiz_info, pattern="^back_to_weeks$")
        ],
        QUIZ_INFO: [
            CallbackQueryHandler(start_timed_quiz, pattern="^start_confirmed$"),
            CallbackQueryHandler(std_select_week, pattern="^std_week_")
        ],
        QUIZ_QUESTION: [CallbackQueryHandler(handle_timed_answer, pattern="^t_ans_")]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_registration),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
    ],
    per_message=False
)

# The ConversationHandler for onboarding
student_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        START_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_mode)],
        ASK_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_nickname)],
        ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_registration)],
        LOGIN_NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_nickname)],
        LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        COLLECT_FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_feedback)],
        SETTINGS_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_settings_choice)],
        CONFIRM_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_account_deletion)],
    },
    fallbacks=[CommandHandler("cancel", cancel_registration)],
    per_message=False
)

feedback_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex('^💬 Give Feedback$'), start_feedback)
    ],
    states={
        COLLECT_FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_feedback)],
    },
    fallbacks=[CommandHandler("cancel", cancel_registration)],
    per_message=False
)

course_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex('^📚 Courses$'), show_courses),
        CommandHandler("courses", show_courses)
    ],
    states={
        COURSE_SELECT: [CallbackQueryHandler(handle_course_selection, pattern="^course_")],
        WEEK_SELECT: [CallbackQueryHandler(handle_week_selection, pattern="^week_|back_to_courses")],
        CONTENT_OPTIONS: [CallbackQueryHandler(handle_content_selection, pattern="^content_|back_to_weeks")],
        COURSE_QUIZ_SELECT: [
            CallbackQueryHandler(std_quiz_info, pattern="^std_quiz_"),
            CallbackQueryHandler(handle_content_selection_back, pattern="^back_to_options$")
        ],
        QUIZ_INFO: [
            CallbackQueryHandler(start_timed_quiz, pattern="^start_confirmed$"),
            CallbackQueryHandler(handle_quiz_info_back, pattern="^std_week_")
        ],
        QUIZ_QUESTION: [CallbackQueryHandler(handle_timed_answer, pattern="^t_ans_")]
    },
    fallbacks=[CommandHandler("cancel", cancel_registration), CommandHandler("start", start)],
    per_message=False
)

settings_conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex('^⚙️ Settings$'), show_settings_menu)
    ],
    states={
        SETTINGS_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_settings_choice)],
        CONFIRM_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_account_deletion)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_registration),
        CommandHandler("start", start),
        MessageHandler(filters.Regex('^🔙 Back to Main Menu$'), show_main_menu)
    ],
    per_message=False
)
