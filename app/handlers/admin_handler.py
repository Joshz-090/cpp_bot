import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CommandHandler, 
    MessageHandler, 
    filters,
    CallbackQueryHandler
)
from telegram.helpers import escape_markdown
from ..services.user_service import UserService
from ..services.quiz_service import QuizService
from ..services.course_service import CourseService
from ..models import DifficultyLevel
from . import question_management_handler as qm

logger = logging.getLogger(__name__)

# --- Conversation States ---
START_MODE, ASK_TEXT, ASK_OPTIONS, ASK_CORRECT_ANSWER = range(4)
SELECT_QUIZ_WEEK, SELECT_QUIZ_ID = range(4, 6)
BROADCAST_MSG = 6
SELECT_LB_WEEK, SELECT_LB_QUIZ = range(7, 9)
# Quiz Creation States
ASK_QUIZ_TITLE, ASK_QUIZ_DESC, ASK_QUIZ_WEEK, ASK_QUIZ_DURATION, ASK_QUIZ_AVAILABILITY = range(10, 15)
# Content Management States
MGMT_SELECT_COURSE, MGMT_SELECT_WEEK, MGMT_SELECT_TYPE, MGMT_ASK_VALUE = range(100, 104)
# Multi-file upload states
MGMT_COLLECT_FILES, MGMT_FILE_CONFIRMATION = range(104, 106)
# Multi-question addition states
MULTI_Q_SELECT_QUIZ, MULTI_Q_COLLECT_QUESTIONS = range(15, 17)

# Quiz and question management states
MANAGE_QUIZ_SELECT, MANAGE_QUIZ_ACTION, MANAGE_QUESTION_SELECT, MANAGE_QUESTION_ACTION = range(17, 21)
# --- Role Check Decorator ---
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not UserService.is_admin(user_id):
            await update.effective_message.reply_text("⛔ Access Denied. Admin privileges required.")
            logger.warning(f"Unauthorized access attempt by user {user_id}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# --- Admin Menu ---
@admin_only
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the admin main menu and starts the conversation."""
    keyboard = [
        [InlineKeyboardButton("➕ Add Question", callback_data="admin_add_question")],
        [InlineKeyboardButton("📝 Add Multiple Questions", callback_data="admin_add_multiple")],
        [InlineKeyboardButton("📝 Create Quiz", callback_data="admin_create_quiz")],
        [InlineKeyboardButton("🔧 Manage Quizzes", callback_data="admin_manage_quizzes")],
        [InlineKeyboardButton("🔧 Manage Questions", callback_data="admin_manage_questions")],
        [InlineKeyboardButton("📚 Manage Course Content", callback_data="admin_manage_content")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 Quiz Leaderboards", callback_data="admin_view_lb")],
        [InlineKeyboardButton("📋 View Feedbacks", callback_data="admin_view_feedback")],
        [InlineKeyboardButton("📈 View Overall Stats", callback_data="admin_stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg_text = "🛠 Admin Dashboard\nSelect an operation:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg_text, reply_markup=reply_markup)
    else:
        await update.effective_message.reply_text(msg_text, reply_markup=reply_markup)
        
    return START_MODE

# --- Broadcast Logic ---
@admin_only
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Please enter the message you want to broadcast to all users. Type /cancel to abort.")
    return BROADCAST_MSG

async def do_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # Filter for users with a valid telegram_id up front
    all_users = UserService.get_all_users()
    users = [u for u in all_users if u.telegram_id]
    
    count = 0
    failure = 0
    
    await update.message.reply_text(f"🚀 Broadcasting to {len(users)} active users...")
    
    for user in users:
        try:
            await context.bot.send_message(chat_id=user.telegram_id, text=text)
            count += 1
            # Add small delay to avoid rate limiting
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user.telegram_id}: {e}")
            failure += 1
            
    await update.message.reply_text(f"🏁 Broadcast finished.\n✅ Success: {count}\n❌ Failed: {failure}")
    return ConversationHandler.END

# --- Add Question Conversation ---
@admin_only
async def start_add_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # First, choose week
    # Standard 12 weeks in a grid
    keyboard = []
    for i in range(1, 13, 3):
        keyboard.append([
            InlineKeyboardButton(f"Week {i}", callback_data=f"sel_week_{i}"),
            InlineKeyboardButton(f"Week {i+1}", callback_data=f"sel_week_{i+1}"),
            InlineKeyboardButton(f"Week {i+2}", callback_data=f"sel_week_{i+2}")
        ])
    
    # Special categories
    keyboard.append([
        InlineKeyboardButton("🎓 Mid Exam", callback_data="sel_week_13"),
        InlineKeyboardButton("🏆 Final Exam", callback_data="sel_week_14")
    ])
    keyboard.append([InlineKeyboardButton("🤡 Funny Question", callback_data="sel_week_15")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Select the Week or Category for this question:", reply_markup=reply_markup)
    return SELECT_QUIZ_WEEK

async def select_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    week = int(query.data.split('_')[2])
    context.user_data['sel_week'] = week
    
    quizzes = QuizService.get_quizzes_by_week(week)
    if not quizzes:
        await query.message.reply_text(f"❌ No quizzes found for Week {week}. Please create a quiz first.")
        return START_MODE
        
    keyboard = [[InlineKeyboardButton(q.title, callback_data=f"sel_quiz_{q.id}")] for q in quizzes]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f"Select Quiz in Week {week}:", reply_markup=reply_markup)
    return SELECT_QUIZ_ID

async def select_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    quiz_id = int(query.data.split('_')[2])
    context.user_data['sel_quiz_id'] = quiz_id
    
    await query.message.reply_text("Enter the question text:")
    return ASK_TEXT

async def get_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['q_text'] = update.message.text
    await update.message.reply_text(
        "Enter the options in this format:\nA: Option A\nB: Option B\nC: Option C\nD: Option D"
    )
    return ASK_OPTIONS

async def get_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = update.message.text.split('\n')
    try:
        options = {}
        for line in lines:
            key, val = line.split(':', 1)
            options[key.strip().upper()] = val.strip()
        
        if len(options) < 4:
            raise ValueError("Not enough options")
            
        context.user_data['q_options'] = options
        await update.message.reply_text("Which one is the correct answer? (A, B, C, or D)")
        return ASK_CORRECT_ANSWER
    except Exception:
        await update.message.reply_text("❌ Invalid format. Please use 'A: text' format for each line.")
        return ASK_OPTIONS

async def get_correct_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.message.text.strip().upper()
    if ans not in ['A', 'B', 'C', 'D']:
        await update.message.reply_text("❌ Invalid answer. Please enter A, B, C, or D.")
        return ASK_CORRECT_ANSWER
    
    context.user_data['q_answer'] = ans
    # For now we'll use a default course ID until we have a course selection UI
    # We'll try to find the first course
    context.user_data['course_id'] = 1 
    
    # Save the question
    data = {
        'quiz_id': context.user_data['sel_quiz_id'],
        'question_text': context.user_data['q_text'],
        'option_a': context.user_data['q_options']['A'],
        'option_b': context.user_data['q_options']['B'],
        'option_c': context.user_data['q_options']['C'],
        'option_d': context.user_data['q_options']['D'],
        'correct_answer': context.user_data['q_answer'],
        'difficulty': DifficultyLevel.EASY
    }
    
    try:
        QuizService.add_question(context.user_data['course_id'], data)
        msg = await update.message.reply_text("✅ Question added and linked to Quiz successfully!")
        await asyncio.sleep(2)
        await msg.delete()
    except Exception as e:
        logger.error(f"Error saving question: {e}")
        await update.message.reply_text("❌ Failed to save question to database.")
        
    return await admin_menu(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current operation and return to admin menu."""
    # Clear any user data that might be lingering
    keys_to_clear = [
        'sel_week', 'sel_quiz_id', 'q_text', 'q_options', 'q_answer',
        'quiz_title', 'quiz_desc', 'quiz_week', 'quiz_duration', 'multi_questions',
        'current_question_num', 'multi_quiz_id', 'multi_week', 'current_q_data',
        'mg_week', 'mg_quiz'
    ]
    
    for key in keys_to_clear:
        if key in context.user_data:
            del context.user_data[key]
    
    await update.message.reply_text("❌ Operation cancelled. Returning to admin menu...")
    return ConversationHandler.END

# --- Multi-Question Addition Logic ---
@admin_only
async def start_add_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start multi-question addition flow."""
    query = update.callback_query
    await query.answer()
    
    # Initialize multi-question session data
    context.user_data['multi_questions'] = []
    context.user_data['current_question_num'] = 1
    
    # First, select week
    # Standard 12 weeks in a grid
    keyboard = []
    for i in range(1, 13, 3):
        keyboard.append([
            InlineKeyboardButton(f"Week {i}", callback_data=f"multi_week_{i}"),
            InlineKeyboardButton(f"Week {i+1}", callback_data=f"multi_week_{i+1}"),
            InlineKeyboardButton(f"Week {i+2}", callback_data=f"multi_week_{i+2}")
        ])
    
    # Special categories
    keyboard.append([
        InlineKeyboardButton("🎓 Mid Exam", callback_data="multi_week_13"),
        InlineKeyboardButton("🏆 Final Exam", callback_data="multi_week_14")
    ])
    keyboard.append([InlineKeyboardButton("🤡 Funny Question", callback_data="multi_week_15")])
    
    # Ensure nested list is initialized for multi-question addition
    context.user_data['multi_questions'] = []
    context.user_data['current_question_num'] = 1
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("📝 *Add Multiple Questions*\nSelect the Week or Category:", reply_markup=reply_markup, parse_mode="Markdown")
    return MULTI_Q_SELECT_QUIZ

async def multi_select_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle week selection for multi-question addition."""
    query = update.callback_query
    await query.answer()
    
    week = int(query.data.split('_')[2])
    context.user_data['multi_week'] = week
    
    quizzes = QuizService.get_quizzes_by_week(week)
    if not quizzes:
        await query.message.reply_text(f"❌ No quizzes found for Week {week}. Please create a quiz first.")
        return START_MODE
        
    keyboard = [[InlineKeyboardButton(q.title, callback_data=f"multi_quiz_{q.id}")] for q in quizzes]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f"Select Quiz for Week {week}:", reply_markup=reply_markup)
    return MULTI_Q_SELECT_QUIZ

async def multi_select_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz selection for multi-question addition."""
    query = update.callback_query
    await query.answer()
    
    quiz_id = int(query.data.split('_')[2])
    context.user_data['multi_quiz_id'] = quiz_id
    
    instructions = (
        "📝 *Multi-Question Addition*\n\n"
        "Please enter questions in this format:\n\n"
        "1) Question text here?\n"
        "A: Option A\n"
        "B: Option B\n" 
        "C: Option C\n"
        "D: Option D\n"
        "CORRECT: B\n\n"
        "2) Next question?\n"
        "A: Option A\n"
        "B: Option B\n"
        "C: Option C\n"
        "D: Option D\n"
        "CORRECT: A\n\n"
        "Type 'done' when finished or 'cancel' to abort."
    )
    
    await query.message.reply_text(instructions, parse_mode="Markdown")
    return MULTI_Q_COLLECT_QUESTIONS

async def collect_multiple_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect and parse multiple questions."""
    text = update.message.text.strip().lower()
    
    if text == 'done':
        return await save_multiple_questions(update, context)
    elif text == 'cancel':
        await update.message.reply_text("Multi-question addition cancelled.")
        return await admin_menu(update, context)
    
    # Check if we have partial question data
    if 'current_q_data' not in context.user_data:
        # Start collecting a new question
        context.user_data['current_q_data'] = {
            'number': context.user_data['current_question_num'],
            'raw_text': update.message.text
        }
        
        # Try to parse if it looks complete
        question = parse_question_text(update.message.text)
        if question:
            context.user_data['multi_questions'].append(question)
            context.user_data['current_question_num'] += 1
            del context.user_data['current_q_data']
            
            await update.message.reply_text(
                f"✅ Question {context.user_data['current_question_num']-1} added!\n"
                f"Total questions: {len(context.user_data['multi_questions'])}\n\n"
                f"Enter next question or type 'done' to finish."
            )
        else:
            await update.message.reply_text(
                "❌ Invalid format. Please use:\n"
                "1) Question?\nA: Option\nB: Option\nC: Option\nD: Option\nCORRECT: B"
            )
    else:
        # Continue collecting current question
        context.user_data['current_q_data']['raw_text'] += '\n' + update.message.text
        
        # Try to parse the complete question
        full_text = context.user_data['current_q_data']['raw_text']
        question = parse_question_text(full_text)
        
        if question:
            context.user_data['multi_questions'].append(question)
            context.user_data['current_question_num'] += 1
            del context.user_data['current_q_data']
            
            await update.message.reply_text(
                f"✅ Question {context.user_data['current_question_num']-1} added!\n"
                f"Total questions: {len(context.user_data['multi_questions'])}\n\n"
                f"Enter next question or type 'done' to finish."
            )
        else:
            await update.message.reply_text("Continue adding options for this question...")
    
    return MULTI_Q_COLLECT_QUESTIONS

def parse_question_text(text):
    """Parse question text and return structured data."""
    try:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Extract question number and text
        question_line = lines[0]
        if not question_line[0].isdigit() or ')' not in question_line:
            return None
            
        question_text = question_line.split(')', 1)[1].strip()
        
        # Extract options and correct answer
        options = {}
        correct_answer = None
        
        for line in lines[1:]:
            if line.startswith(('A:', 'B:', 'C:', 'D:')):
                key = line[0]
                value = line[2:].strip()
                options[key] = value
            elif line.startswith('CORRECT:'):
                correct_answer = line.split(':')[1].strip().upper()
        
        if len(options) != 4 or not correct_answer or correct_answer not in options:
            return None
            
        return {
            'question_text': question_text,
            'options': options,
            'correct_answer': correct_answer
        }
        
    except Exception:
        return None

async def save_multiple_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save all collected questions to the database."""
    questions = context.user_data.get('multi_questions', [])
    quiz_id = context.user_data.get('multi_quiz_id')
    
    if not questions:
        await update.message.reply_text("❌ No questions to save.")
        return await admin_menu(update, context)
    
    if not quiz_id:
        await update.message.reply_text("❌ Quiz not selected.")
        return await admin_menu(update, context)
    
    saved_count = 0
    failed_count = 0
    
    for q_data in questions:
        try:
            data = {
                'quiz_id': quiz_id,
                'question_text': q_data['question_text'],
                'option_a': q_data['options']['A'],
                'option_b': q_data['options']['B'],
                'option_c': q_data['options']['C'],
                'option_d': q_data['options']['D'],
                'correct_answer': q_data['correct_answer'],
                'difficulty': DifficultyLevel.EASY
            }
            
            QuizService.add_question(1, data)  # Using default course ID 1
            saved_count += 1
        except Exception as e:
            logger.error(f"Error saving question: {e}")
            failed_count += 1
    
    # Clean up session data
    for key in ['multi_questions', 'current_question_num', 'multi_quiz_id', 'multi_week', 'current_q_data']:
        if key in context.user_data:
            del context.user_data[key]
    
    await update.message.reply_text(
        f"🎉 *Multi-Question Addition Complete!*\n\n"
        f"✅ Successfully saved: {saved_count}\n"
        f"❌ Failed: {failed_count}\n\n"
        f"Returning to admin dashboard...",
        parse_mode="Markdown"
    )
    
    await asyncio.sleep(2)
    return await admin_menu(update, context)

# --- Quiz and Question Management Logic ---
@admin_only
async def start_manage_quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start quiz management interface."""
    query = update.callback_query
    await query.answer()
    
    # Standard 12 weeks in a grid
    keyboard = []
    for i in range(1, 13, 3):
        keyboard.append([
            InlineKeyboardButton(f"Week {i}", callback_data=f"mg_quiz_week_{i}"),
            InlineKeyboardButton(f"Week {i+1}", callback_data=f"mg_quiz_week_{i+1}"),
            InlineKeyboardButton(f"Week {i+2}", callback_data=f"mg_quiz_week_{i+2}")
        ])
    
    # Special categories
    keyboard.append([
        InlineKeyboardButton("🎓 Mid Exam", callback_data="mg_quiz_week_13"),
        InlineKeyboardButton("🏆 Final Exam", callback_data="mg_quiz_week_14")
    ])
    keyboard.append([InlineKeyboardButton("🤡 Funny Question", callback_data="mg_quiz_week_15")])
    weeks = keyboard # For consistency with naming below
    
    weeks.append([InlineKeyboardButton("📋 All Quizzes", callback_data="mg_quiz_all")])
    reply_markup = InlineKeyboardMarkup(weeks)
    await query.message.reply_text("🔧 *Manage Quizzes*\nSelect week or category:", reply_markup=reply_markup, parse_mode="Markdown")
    return MANAGE_QUIZ_SELECT

@admin_only
async def start_manage_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start question management interface."""
    return await qm.start_manage_questions(update, context)

async def manage_quiz_select_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle week selection for quiz management."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "mg_quiz_all":
        quizzes = []
        # Get all quizzes from all weeks
        for week in range(1, 16):
            week_quizzes = QuizService.get_quizzes_by_week(week, include_expired=True)
            quizzes.extend([(q, week) for q in week_quizzes])
    else:
        week = int(query.data.split('_')[3])
        context.user_data['mg_week'] = week
        quizzes = QuizService.get_quizzes_by_week(week, include_expired=True)
        quizzes = [(q, week) for q in quizzes]
    
    if not quizzes:
        await query.edit_message_text("❌ No quizzes found for the selected criteria.")
        return await admin_menu(update, context)
    
    # Create quiz list with management options
    keyboard = []
    for quiz, week_num in quizzes:
        status = "✅ Active" if quiz.available_from and quiz.available_until else "⏰ Expired"
        keyboard.append([
            InlineKeyboardButton(f"{quiz.title} {status}", callback_data=f"mg_quiz_{quiz.id}"),
            InlineKeyboardButton("🔧 Actions", callback_data=f"mg_quiz_actions_{quiz.id}")
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="back_to_admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query.data == "mg_quiz_all":
        await query.edit_message_text("📋 *All Quizzes*\nSelect a quiz to manage:", reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await query.edit_message_text(f"📅 *Week {week_num} Quizzes*\nSelect a quiz to manage:", reply_markup=reply_markup, parse_mode="Markdown")
    
    return MANAGE_QUIZ_ACTION

async def manage_quiz_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quiz management actions."""
    query = update.callback_query
    await query.answer()
    
    quiz_id = int(query.data.split('_')[2])
    quiz = QuizService.get_quiz(quiz_id)
    
    if not quiz:
        await query.edit_message_text("❌ Quiz not found.")
        return await admin_menu(update, context)
    
    context.user_data['mg_quiz'] = quiz
    
    # Get quiz statistics
    questions = QuizService.get_quiz_questions(quiz_id)
    
    action_text = (
        f"🔧 *Manage Quiz: {quiz.title}*\n\n"
        f"📊 *Statistics:*\n"
        f"   • Questions: {len(questions)}\n"
        f"   • Week: {quiz.week_number}\n"
        f"   • Duration: {quiz.duration_minutes} minutes\n"
        f"   • Status: {'✅ Active' if quiz.available_from and quiz.available_until else '⏰ Expired'}\n\n"
        f"🎯 *Select Action:*\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📝 Edit Quiz Info", callback_data="mg_edit_quiz_info")],
        [InlineKeyboardButton("🗑️ Delete Quiz", callback_data="mg_delete_quiz")],
        [InlineKeyboardButton("📝 Manage Questions", callback_data="mg_quiz_questions")],
        [InlineKeyboardButton("⬅️ Back", callback_data="mg_quiz_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(action_text, reply_markup=reply_markup, parse_mode="Markdown")
    return MANAGE_QUIZ_ACTION

# --- Create Quiz Conversation ---
@admin_only
async def start_create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📝 *Create Quiz*\nEnter the Quiz Title (e.g., Week 1 Basics):", parse_mode="Markdown")
    return ASK_QUIZ_TITLE

async def get_quiz_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['quiz_title'] = update.message.text
    await update.message.reply_text("Enter a short description for this quiz:")
    return ASK_QUIZ_DESC

async def get_quiz_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['quiz_desc'] = update.message.text
    await update.message.reply_text("Which Week does this quiz belong to? (1-15):")
    return ASK_QUIZ_WEEK

async def get_quiz_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        week = int(update.message.text)
        if not 1 <= week <= 15: raise ValueError()
        context.user_data['quiz_week'] = week
        await update.message.reply_text(
            "Enter the duration for this quiz in minutes (e.g., 15):\n\n"
            "💡 _Note: Week 13=Mid, 14=Final, 15=Funny_"
        )
        return ASK_QUIZ_DURATION
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number between 1 and 15.\n(1-12=Weeks, 13=Mid, 14=Final, 15=Funny)")
        return ASK_QUIZ_WEEK

async def get_quiz_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        duration = int(update.message.text)
        context.user_data['quiz_duration'] = duration
        await update.message.reply_text(
            "Final Step: How long from now should this quiz stay active? (Enter minutes, e.g., 15)\n"
            "The quiz will disappear for students after this time."
        )
        return ASK_QUIZ_AVAILABILITY
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number for duration.")
        return ASK_QUIZ_DURATION

async def get_quiz_availability(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        avail_mins = int(update.message.text)
        from datetime import datetime, timedelta
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=avail_mins)
        
        # Save Quiz
        QuizService.create_quiz(
            title=context.user_data['quiz_title'],
            description=context.user_data['quiz_desc'],
            duration=context.user_data['quiz_duration'],
            week=context.user_data['quiz_week'],
            start_time=start_time,
            end_time=end_time
        )
        
        msg = await update.message.reply_text(
            f"✅ *Quiz Created & Scheduled!*\n\n"
            f"Title: {context.user_data['quiz_title']}\n"
            f"Week: {context.user_data['quiz_week']}\n"
            f"Active for: {avail_mins} minutes\n"
            f"Session Limit: {context.user_data['quiz_duration']} mins",
            parse_mode="Markdown"
        )
        
        await asyncio.sleep(2)
        await msg.delete()
        return await admin_menu(update, context)
    except Exception as e:
        logger.error(f"Error creating quiz: {e}")
        await update.message.reply_text("❌ Failed to create quiz.")
        return await admin_menu(update, context)

# --- Leaderboard View Flow ---
@admin_only
async def start_view_lb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Standard 12 weeks in a grid
    keyboard = []
    for i in range(1, 13, 3):
        keyboard.append([
            InlineKeyboardButton(f"Week {i}", callback_data=f"lb_week_{i}"),
            InlineKeyboardButton(f"Week {i+1}", callback_data=f"lb_week_{i+1}"),
            InlineKeyboardButton(f"Week {i+2}", callback_data=f"lb_week_{i+2}")
        ])
    
    # Special categories
    keyboard.append([
        InlineKeyboardButton("🎓 Mid Exam", callback_data="lb_week_13"),
        InlineKeyboardButton("🏆 Final Exam", callback_data="lb_week_14")
    ])
    keyboard.append([InlineKeyboardButton("🤡 Funny Question", callback_data="lb_week_15")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Select Week or Category to view Leaderboards:", reply_markup=reply_markup)
    return SELECT_LB_WEEK

async def lb_select_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    week = int(query.data.split('_')[2])
    
    quizzes = QuizService.get_quizzes_by_week(week, include_expired=True)
    if not quizzes:
        await query.message.reply_text(f"ℹ️ No quizzes found for Week {week}.")
        return await admin_menu(update, context)
        
    keyboard = [[InlineKeyboardButton(q.title, callback_data=f"lb_quiz_{q.id}")] for q in quizzes]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Select Quiz for Week {week}:", reply_markup=reply_markup)
    return SELECT_LB_QUIZ

async def lb_show_quiz_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    quiz_id = int(query.data.split('_')[2])
    
    quiz = QuizService.get_quiz(quiz_id)
    results = QuizService.get_quiz_leaderboard(quiz_id)
    questions = QuizService.get_quiz_questions(quiz_id)
    
    if not results:
        await query.edit_message_text(f"🏁 No completions for *{quiz.title}* yet.", parse_mode="Markdown")
        await asyncio.sleep(2)
        return await admin_menu(update, context)
        
    lb_text = f"🏆 *Leaderboard: {quiz.title}* 🏆\n"
    lb_text += f"📅 Week {quiz.week_number} | 📝 {len(questions)} Questions\n\n"
    
    for i, res in enumerate(results, 1):
        # Format duration as mm:ss
        total_secs = int(res['time_taken'] * 60)
        m = total_secs // 60
        s = total_secs % 60
        time_str = f"{m}m {s}s" if m > 0 else f"{s}s"
        
        icon = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        streak_icon = " 🔥" if res.get('streak', 0) >= 3 else ""
        lb_text += f"{icon} *{res['nickname']}*{streak_icon}\n     └ {res['score']}/{res['total']} ({res['accuracy']}%) in {time_str}\n"
    
    lb_text += "\n🚀 _Keep practicing to climb the ranks!_"
    
    await query.edit_message_text(lb_text, parse_mode="Markdown")
    # Return to menu after a short wait or just stay there? 
    # Let's provide a "Back" button
    keyboard = [[InlineKeyboardButton("⬅️ Back to Dashboard", callback_data="back_to_admin")]]
    await query.edit_message_text(lb_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def view_feedbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all feedback entries."""
    query = update.callback_query
    if query:
        await query.answer()
    
    feedbacks = UserService.get_all_feedback()
    if not feedbacks:
        text = "📋 *No feedback received yet.*"
        if query:
            await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]]))
        else:
            await update.message.reply_text(text, parse_mode="Markdown")
        return
        
    fb_text = "📋 *Student Feedback*\n\n"
    for fb in feedbacks[:15]: # Show last 15
        user_name = escape_markdown(fb.user.nickname or fb.user.full_name or "Unknown", version=1)
        date = fb.created_at.strftime("%Y-%m-%d %H:%M")
        fb_text += f"👤 *{user_name}* ({date}):\n{fb.content}\n\n"
        
    keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin")]]
    if query:
        await query.message.edit_text(fb_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(fb_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Content Management Handlers ---

async def start_content_mgmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin Level 1: Select Course to Manage"""
    keyboard = [
        [InlineKeyboardButton("C++", callback_data="mgmt_course_cpp")],
        [InlineKeyboardButton("Python", callback_data="mgmt_course_python")],
        [InlineKeyboardButton("Web Dev", callback_data="mgmt_course_webdev")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "📚 *Content Management*\nSelect a course to update its weekly materials:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    return MGMT_SELECT_COURSE

async def mgmt_select_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin Level 2: Select Week to Manage"""
    query = update.callback_query
    await query.answer()
    
    course_map = {
        "mgmt_course_cpp": "C++",
        "mgmt_course_python": "Python",
        "mgmt_course_webdev": "Web Dev"
    }
    course_name = course_map.get(query.data)
    context.user_data['mgmt_course'] = course_name
    
    keyboard = []
    for i in range(1, 13, 3):
        row = []
        for j in range(3):
            week_num = i + j
            row.append(InlineKeyboardButton(f"Week {week_num}", callback_data=f"mgmt_week_{week_num}"))
        keyboard.append(row)
    
    # Special categories
    keyboard.append([
        InlineKeyboardButton("🎓 Mid Exam", callback_data="mgmt_week_13"),
        InlineKeyboardButton("🏆 Final Exam", callback_data="mgmt_week_14")
    ])
    keyboard.append([InlineKeyboardButton("🤡 Funny Question", callback_data="mgmt_week_15")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Courses", callback_data="admin_manage_content")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"📚 *{course_name} Management*\nSelect the week you want to update:", 
                                reply_markup=reply_markup, parse_mode="Markdown")
    return MGMT_SELECT_WEEK

async def mgmt_select_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin Level 3: Select Content Type (PDF, Video, etc.)"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "admin_manage_content":
        return await start_content_mgmt(update, context)
        
    week_num = int(query.data.split("_")[2])
    context.user_data['mgmt_week'] = week_num
    course_name = context.user_data.get('mgmt_course')
    
    keyboard = [
        [InlineKeyboardButton("📄 Add Multiple PDFs", callback_data="mgmt_type_multi_pdf")],
        [InlineKeyboardButton("🎥 Add Multiple Videos", callback_data="mgmt_type_multi_video")],
        [InlineKeyboardButton("📄 Update Single PDF (Legacy)", callback_data="mgmt_type_pdf")],
        [InlineKeyboardButton("🎥 Update Single Video (Legacy)", callback_data="mgmt_type_video")],
        [InlineKeyboardButton("🌐 Update Web Link", callback_data="mgmt_type_web")],
        [InlineKeyboardButton("📋 View Current Files", callback_data="mgmt_view_files")],
        [InlineKeyboardButton("🔙 Back to Weeks", callback_data=f"mgmt_course_{course_name.lower()}")],
        [InlineKeyboardButton("🏁 Done", callback_data="back_to_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"📘 *{course_name} - Week {week_num} Management*\nWhat would you like to update?",
                                reply_markup=reply_markup, parse_mode="Markdown")
    return MGMT_SELECT_TYPE

async def mgmt_ask_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin Level 4: Ask for the new value"""
    query = update.callback_query
    await query.answer()
    
    type_map = {
        "mgmt_type_pdf": ("pdf_file_id", "Please send the new PDF file ID or URL:"),
        "mgmt_type_video": ("video_link", "Please send the new Video URL:"),
        "mgmt_type_web": ("web_link", "Please send the new Web Link:"),
        "mgmt_type_multi_pdf": ("multi_pdf", "Send PDF files one by one. Type 'DONE' when finished:"),
        "mgmt_type_multi_video": ("multi_video", "Send video URLs one by one. Type 'DONE' when finished:")
    }
    
    field, prompt = type_map.get(query.data)
    context.user_data['mgmt_field'] = field
    
    await query.edit_message_text(f"*Updating {field.replace('_', ' ').title()}*\n\n{prompt}\nType /cancel to abort.", 
                                parse_mode="Markdown")
    return MGMT_ASK_VALUE

async def mgmt_save_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the new value for single file updates"""
    new_value = update.message.text.strip()
    field = context.user_data.get('mgmt_field')
    course_name = context.user_data.get('mgmt_course')
    week_num = context.user_data.get('mgmt_week')
    
    # Handle multi-file collection
    if field in ["multi_pdf", "multi_video"]:
        return await handle_multi_file_collection(update, context, new_value, field)
    
    course = CourseService.get_course_by_name(course_name)
    if not course:
        await update.message.reply_text("Error: Course not found in database.")
        return await admin_menu(update, context)
        
    CourseService.update_weekly_content(course.id, week_num, **{field: new_value})
    
    await update.message.reply_text(f"*Success!* {field.replace('_', ' ').title()} updated for {course_name} Week {week_num}.",
                                    parse_mode="Markdown")
    
    # Return to type selection for same week
    return await mgmt_select_type_internal(update, context, week_num, course_name)

async def mgmt_save_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the file_id of a sent document"""
    document = update.message.document
    field = context.user_data.get('mgmt_field')
    course_name = context.user_data.get('mgmt_course')
    week_num = context.user_data.get('mgmt_week')
    
    # Handle multi-file PDF collection
    if field == "multi_pdf":
        return await handle_multi_file_collection(update, context, "", field)
    
    if field != "pdf_file_id":
        await update.message.reply_text("⚠️ This field expects a link (text), not a file. Please send a text message or /cancel.", parse_mode="Markdown")
        return MGMT_ASK_VALUE
        
    file_id = document.file_id
    
    course = CourseService.get_course_by_name(course_name)
    if not course:
        await update.message.reply_text("❌ Error: Course not found in database.")
        return await admin_menu(update, context)
        
    CourseService.update_weekly_content(course.id, week_num, **{field: file_id})
    
    await update.message.reply_text(f"✅ *Success!* PDF File saved for {course_name} Week {week_num}.\n\n(ID: `{file_id}`)",
                                    parse_mode="Markdown")
    
    # Return to type selection for same week
    return await mgmt_select_type_internal(update, context, week_num, course_name)

async def mgmt_select_type_internal(update: Update, context: ContextTypes.DEFAULT_TYPE, week_num, course_name):
    keyboard = [
        [InlineKeyboardButton("📄 Update PDF (Link/ID)", callback_data="mgmt_type_pdf")],
        [InlineKeyboardButton("🎥 Update Video Link", callback_data="mgmt_type_video")],
        [InlineKeyboardButton("🌐 Update Web Link", callback_data="mgmt_type_web")],
        [InlineKeyboardButton("🔙 Back to Weeks", callback_data=f"mgmt_course_{course_name.lower()}")],
        [InlineKeyboardButton("🏁 Done", callback_data="back_to_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(f"📘 *{course_name} - Week {week_num} Management*\nWhat else would you like to update?",
                                reply_markup=reply_markup, parse_mode="Markdown")
    return MGMT_SELECT_TYPE

async def handle_multi_file_collection(update: Update, context: ContextTypes.DEFAULT_TYPE, new_value: str, field: str):
    """Handles collection of multiple files"""
    if new_value.upper() == "DONE":
        return await finish_multi_file_upload(update, context, field)
    
    course_name = context.user_data.get('mgmt_course')
    week_num = context.user_data.get('mgmt_week')
    course = CourseService.get_course_by_name(course_name)
    
    if not course:
        await update.message.reply_text("❌ Error: Course not found in database.")
        return await admin_menu(update, context)
    
    # Store files in context
    if 'collected_files' not in context.user_data:
        context.user_data['collected_files'] = []
    
    file_type = "pdf" if field == "multi_pdf" else "video"
    
    if field == "multi_pdf":
        # Handle PDF document upload
        if update.message.document:
            file_id = update.message.document.file_id
            file_name = update.message.document.file_name
            context.user_data['collected_files'].append({
                'type': file_type,
                'file_id': file_id,
                'file_name': file_name
            })
            await update.message.reply_text(f"✅ PDF '{file_name}' added. Send another PDF or type 'DONE' to finish.")
        else:
            await update.message.reply_text("⚠️ Please send a PDF file, not text. Type 'DONE' when finished.")
    else:  # multi_video
        # Handle video URL
        context.user_data['collected_files'].append({
            'type': file_type,
            'file_url': new_value,
            'file_name': f"Video_{len(context.user_data['collected_files']) + 1}"
        })
        await update.message.reply_text(f"✅ Video URL added. Send another URL or type 'DONE' to finish.")
    
    return MGMT_COLLECT_FILES


async def finish_multi_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str):
    """Finishes the multi-file upload process"""
    collected_files = context.user_data.get('collected_files', [])
    if not collected_files:
        await update.message.reply_text("❌ No files were added. Please try again.")
        return await mgmt_select_type_internal(update, context, 
                                              context.user_data.get('mgmt_week'), 
                                              context.user_data.get('mgmt_course'))
    
    course_name = context.user_data.get('mgmt_course')
    week_num = context.user_data.get('mgmt_week')
    course = CourseService.get_course_by_name(course_name)
    
    if not course:
        await update.message.reply_text("❌ Error: Course not found in database.")
        return await admin_menu(update, context)
    
    # Save all files to database
    saved_count = 0
    for file_data in collected_files:
        CourseService.add_content_file(
            course_id=course.id,
            week_number=week_num,
            file_type=file_data['type'],
            file_id=file_data.get('file_id'),
            file_url=file_data.get('file_url'),
            file_name=file_data.get('file_name')
        )
        saved_count += 1
    
    # Clear collected files
    context.user_data['collected_files'] = []
    
    file_type = "PDFs" if field == "multi_pdf" else "Videos"
    await update.message.reply_text(f"✅ *Success!* {saved_count} {file_type} saved for {course_name} Week {week_num}.",
                                    parse_mode="Markdown")
    
    # Return to type selection for same week
    return await mgmt_select_type_internal(update, context, week_num, course_name)


async def mgmt_view_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows current files for the selected week"""
    query = update.callback_query
    await query.answer()
    
    course_name = context.user_data.get('mgmt_course')
    week_num = context.user_data.get('mgmt_week')
    course = CourseService.get_course_by_name(course_name)
    
    if not course:
        await query.edit_message_text("❌ Error: Course not found in database.")
        return await admin_menu(update, context)
    
    files = CourseService.list_content_files(course.id, week_num)
    
    if not files:
        await query.edit_message_text(f"📂 *No files found* for {course_name} Week {week_num}.\n\nAdd some files using the options below!",
                                     parse_mode="Markdown")
        return await mgmt_select_type_internal(update, context, week_num, course_name)
    
    # Format file list
    file_text = f"📂 *Files for {course_name} Week {week_num}*\n\n"
    
    pdf_files = [f for f in files if f.file_type == 'pdf']
    video_files = [f for f in files if f.file_type == 'video']
    
    if pdf_files:
        file_text += "📄 *PDFs:*\n"
        for i, pdf in enumerate(pdf_files, 1):
            name = pdf.file_name or f"PDF_{i}"
            file_text += f"  {i}. {name}\n"
        file_text += "\n"
    
    if video_files:
        file_text += "🎥 *Videos:*\n"
        for i, video in enumerate(video_files, 1):
            name = video.file_name or f"Video_{i}"
            file_text += f"  {i}. {name}\n"
        file_text += "\n"
    
    file_text += f"Total: {len(files)} files"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Management", callback_data=f"mgmt_course_{course_name.lower()}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(file_text, reply_markup=reply_markup, parse_mode="Markdown")
    return MGMT_SELECT_TYPE


async def back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await admin_menu(update, context)

# --- Management Helper Functions ---
async def handle_management_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back navigation in management interfaces."""
    query = update.callback_query
    await query.answer()
    return await admin_menu(update, context)

    return await admin_menu(update, context)

async def edit_quiz_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz info editing."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 Quiz editing coming soon!")
    return MANAGE_QUIZ_ACTION

async def delete_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz deletion."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🗑️ Quiz deletion coming soon!")
    return MANAGE_QUIZ_ACTION

async def manage_quiz_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz question management."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 Quiz question management coming soon!")
    return MANAGE_QUIZ_ACTION

async def process_quiz_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process quiz edit."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 Quiz edit processing coming soon!")
    return MANAGE_QUIZ_ACTION

    return await admin_menu(update, context)

# --- Handler Configurations ---
admin_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("admin", admin_menu)],
    states={
        START_MODE: [
            CallbackQueryHandler(start_add_question, pattern="^admin_add_question$"),
            CallbackQueryHandler(start_add_multiple, pattern="^admin_add_multiple$"),
            CallbackQueryHandler(start_create_quiz, pattern="^admin_create_quiz$"),
            CallbackQueryHandler(start_manage_quizzes, pattern="^admin_manage_quizzes$"),
            CallbackQueryHandler(start_manage_questions, pattern="^admin_manage_questions$"),
            CallbackQueryHandler(start_broadcast, pattern="^admin_broadcast$"),
            CallbackQueryHandler(start_view_lb, pattern="^admin_view_lb$"),
            CallbackQueryHandler(view_feedbacks, pattern="^admin_view_feedback$"),
            CallbackQueryHandler(start_content_mgmt, pattern="^admin_manage_content$"),
            CallbackQueryHandler(back_to_admin, pattern="^back_to_admin$")
        ],
        MGMT_SELECT_COURSE: [CallbackQueryHandler(mgmt_select_week, pattern="^mgmt_course_"),
                             CallbackQueryHandler(back_to_admin, pattern="^back_to_admin$")],
        MGMT_SELECT_WEEK: [CallbackQueryHandler(mgmt_select_type, pattern="^mgmt_week_|admin_manage_content")],
        MGMT_SELECT_TYPE: [CallbackQueryHandler(mgmt_ask_value, pattern="^mgmt_type_"),
                             CallbackQueryHandler(mgmt_view_files, pattern="^mgmt_view_files$"),
                             CallbackQueryHandler(mgmt_select_week, pattern="^mgmt_course_"),
                             CallbackQueryHandler(back_to_admin, pattern="^back_to_admin$")],
        MGMT_ASK_VALUE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, mgmt_save_value),
            MessageHandler(filters.Document.PDF, mgmt_save_document)
        ],
        MGMT_COLLECT_FILES: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, mgmt_save_value),
            MessageHandler(filters.Document.PDF, mgmt_save_document)
        ],
        MANAGE_QUIZ_SELECT: [
            CallbackQueryHandler(manage_quiz_select_week, pattern="^mg_quiz_week_|mg_quiz_all$"),
            CallbackQueryHandler(handle_management_back, pattern="^mg_quiz_back$")
        ],
        MANAGE_QUIZ_ACTION: [
            CallbackQueryHandler(manage_quiz_actions, pattern="^mg_quiz_[0-9]"),
            CallbackQueryHandler(edit_quiz_info, pattern="^mg_edit_quiz_info$"),
            CallbackQueryHandler(delete_quiz, pattern="^mg_delete_quiz$"),
            CallbackQueryHandler(manage_quiz_questions, pattern="^mg_quiz_questions$"),
            CallbackQueryHandler(handle_management_back, pattern="^mg_quiz_back$")
        ],
        qm.MG_SELECT_WEEK: [
            CallbackQueryHandler(qm.list_quizzes, pattern="^mg_q_week_"),
            CallbackQueryHandler(back_to_admin, pattern="^back_to_admin$")
        ],
        qm.MG_SELECT_QUIZ: [
            CallbackQueryHandler(qm.list_questions, pattern="^mg_q_quiz_"),
            CallbackQueryHandler(qm.start_manage_questions, pattern="^admin_manage_questions$")
        ],
        qm.MG_SELECT_QUESTION: [
            CallbackQueryHandler(qm.show_question_details, pattern="^mg_q_item_"),
            CallbackQueryHandler(qm.list_quizzes, pattern="^mg_q_week_") # Back pattern
        ],
        qm.MG_QUESTION_ACTIONS: [
            CallbackQueryHandler(qm.edit_q_text_start, pattern="^mg_edit_q_text$"),
            CallbackQueryHandler(qm.edit_q_options_start, pattern="^mg_edit_q_options$"),
            CallbackQueryHandler(qm.edit_q_answer_start, pattern="^mg_edit_q_answer$"),
            CallbackQueryHandler(qm.delete_question, pattern="^mg_delete_q$"),
            CallbackQueryHandler(qm.list_questions, pattern="^mg_q_quiz_") # Back pattern
        ],
        qm.EDIT_Q_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, qm.edit_q_text_save)],
        qm.EDIT_Q_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, qm.edit_q_options_save)],
        qm.EDIT_Q_ANSWER: [CallbackQueryHandler(qm.edit_q_answer_save, pattern="^mg_ans_")],
        qm.CONFIRM_DELETE: [
            CallbackQueryHandler(qm.confirm_delete, pattern="^mg_confirm_delete$"),
            CallbackQueryHandler(qm.show_question_details, pattern="^mg_q_item_") # Cancel
        ],
        MULTI_Q_SELECT_QUIZ: [CallbackQueryHandler(multi_select_week, pattern="^multi_week_"), 
                                CallbackQueryHandler(multi_select_quiz, pattern="^multi_quiz_")],
        MULTI_Q_COLLECT_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_multiple_questions)],
        SELECT_QUIZ_WEEK: [CallbackQueryHandler(select_week, pattern="^sel_week_")],
        SELECT_QUIZ_ID: [CallbackQueryHandler(select_quiz, pattern="^sel_quiz_")],
        SELECT_LB_WEEK: [CallbackQueryHandler(lb_select_week, pattern="^lb_week_")],
        SELECT_LB_QUIZ: [CallbackQueryHandler(lb_show_quiz_results, pattern="^lb_quiz_")],
        ASK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_text)],
        ASK_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_options)],
        ASK_CORRECT_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_correct_answer)],
        ASK_QUIZ_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quiz_title)],
        ASK_QUIZ_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quiz_desc)],
        ASK_QUIZ_WEEK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quiz_week)],
        ASK_QUIZ_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quiz_duration)],
        ASK_QUIZ_AVAILABILITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quiz_availability)],
        BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, do_broadcast)]
    },
    fallbacks=[
    CommandHandler("cancel", cancel),
    CommandHandler("admin", admin_menu)
]
)
