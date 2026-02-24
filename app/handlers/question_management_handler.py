import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from ..services.quiz_service import QuizService
from ..models import DifficultyLevel

logger = logging.getLogger(__name__)

# --- Conversation States ---
(
    MG_SELECT_WEEK,
    MG_SELECT_QUIZ,
    MG_SELECT_QUESTION,
    MG_QUESTION_ACTIONS,
    EDIT_Q_FIELD,
    EDIT_Q_TEXT,
    EDIT_Q_OPTIONS,
    EDIT_Q_ANSWER,
    CONFIRM_DELETE
) = range(30, 39)

def get_mg_back_button(callback_data: str):
    return [InlineKeyboardButton("⬅️ Back", callback_data=callback_data)]

async def start_manage_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for managing questions."""
    query = update.callback_query
    await query.answer()
    
    weeks = [[InlineKeyboardButton(f"Week {i}", callback_data=f"mg_q_week_{i}")] for i in range(1, 16)]
    # weeks.append([InlineKeyboardButton("📋 All Questions", callback_data="mg_q_all")])
    weeks.append([InlineKeyboardButton("🏠 Back to Admin", callback_data="back_to_admin")])
    
    reply_markup = InlineKeyboardMarkup(weeks)
    await query.edit_message_text("🔧 *Manage Questions*\nSelect Week:", reply_markup=reply_markup, parse_mode="Markdown")
    return MG_SELECT_WEEK

async def list_quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List quizzes for the selected week."""
    query = update.callback_query
    await query.answer()
    
    # Try to get week from user_data first, then parse from query.data (mg_q_week_{i})
    week = context.user_data.get('mg_week')
    if not week and query.data and query.data.startswith('mg_q_week_'):
        try:
            week = int(query.data.split('_')[3])
            context.user_data['mg_week'] = week
        except (IndexError, ValueError):
            pass

    if not week:
        await query.edit_message_text("❌ Week selection lost. Please start over.")
        return await start_manage_questions(update, context)
    
    quizzes = QuizService.get_quizzes_by_week(week, include_expired=True)
    if not quizzes:
        await query.edit_message_text(f"❌ No quizzes found for Week {week}.", 
                                    reply_markup=InlineKeyboardMarkup([get_mg_back_button("admin_manage_questions")]))
        return MG_SELECT_WEEK
        
    keyboard = [[InlineKeyboardButton(q.title, callback_data=f"mg_q_quiz_{q.id}")] for q in quizzes]
    keyboard.append(get_mg_back_button("admin_manage_questions"))
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"📅 *Week {week} Quizzes*\nSelect Quiz:", reply_markup=reply_markup, parse_mode="Markdown")
    return MG_SELECT_QUIZ

async def list_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List questions for the selected quiz."""
    query = update.callback_query
    await query.answer()
    
    # Try to get quiz_id from user_data first (e.g. if called from confirm_delete)
    # Otherwise parse from query.data (e.g. mg_q_quiz_{id})
    quiz_id = context.user_data.get('mg_quiz_id')
    if not quiz_id and query.data and query.data.startswith('mg_q_quiz_'):
        try:
            quiz_id = int(query.data.split('_')[3])
            context.user_data['mg_quiz_id'] = quiz_id
        except (IndexError, ValueError):
            pass

    if not quiz_id:
        await query.edit_message_text("❌ Quiz selection lost. Please start over.")
        return await start_manage_questions(update, context)
    
    questions = QuizService.get_quiz_questions(quiz_id)
    if not questions:
        await query.edit_message_text("❌ No questions found in this quiz.", 
                                    reply_markup=InlineKeyboardMarkup([get_mg_back_button(f"mg_q_week_{context.user_data['mg_week']}")]))
        return MG_SELECT_QUIZ
        
    keyboard = []
    for q in questions:
        # Truncate text for button
        text = q.question_text[:30] + "..." if len(q.question_text) > 30 else q.question_text
        keyboard.append([InlineKeyboardButton(text, callback_data=f"mg_q_item_{q.id}")])
    
    keyboard.append(get_mg_back_button(f"mg_q_week_{context.user_data['mg_week']}"))
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"📝 *Quiz Questions*\nSelect a question to manage:", reply_markup=reply_markup, parse_mode="Markdown")
    return MG_SELECT_QUESTION

async def show_question_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show details and actions for a specific question."""
    query = update.callback_query
    await query.answer()
    
    # Try to get q_id from user_data first, then parse from query.data (mg_q_item_{id})
    q_id = context.user_data.get('mg_q_id')
    if not q_id and query.data and query.data.startswith('mg_q_item_'):
        try:
            q_id = int(query.data.split('_')[3])
            context.user_data['mg_q_id'] = q_id
        except (IndexError, ValueError):
            pass

    if not q_id:
        await query.edit_message_text("❌ Question selection lost. Please start over.")
        return await list_questions(update, context)

    question = QuizService.get_question(q_id)
    
    if not question:
        await query.edit_message_text("❌ Question not found.")
        return await list_questions(update, context)
        
    context.user_data['mg_q_id'] = q_id
    
    detail_text = (
        f"❓ *Question Details*\n\n"
        f"Text: {question.question_text}\n\n"
        f"A: {question.option_a}\n"
        f"B: {question.option_b}\n"
        f"C: {question.option_c}\n"
        f"D: {question.option_d}\n\n"
        f"✅ Correct: {question.correct_answer}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📝 Edit Text", callback_data="mg_edit_q_text")],
        [InlineKeyboardButton("🔢 Edit Options", callback_data="mg_edit_q_options")],
        [InlineKeyboardButton("✅ Edit Answer", callback_data="mg_edit_q_answer")],
        [InlineKeyboardButton("🗑️ Delete Question", callback_data="mg_delete_q")],
        get_mg_back_button(f"mg_q_quiz_{context.user_data['mg_quiz_id']}")
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(detail_text, reply_markup=reply_markup, parse_mode="Markdown")
    return MG_QUESTION_ACTIONS

async def delete_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for confirmation before deletion."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data="mg_confirm_delete")],
        [InlineKeyboardButton("❌ No, Cancel", callback_data=f"mg_q_item_{context.user_data['mg_q_id']}")]
    ]
    
    await query.edit_message_text("⚠️ *Are you sure you want to delete this question?*", 
                                reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return CONFIRM_DELETE

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Perform the deletion."""
    query = update.callback_query
    await query.answer()
    
    q_id = context.user_data['mg_q_id']
    if QuizService.delete_question(q_id):
        await query.edit_message_text("✅ Question deleted successfully!")
    else:
        await query.edit_message_text("❌ Failed to delete question.")
        
    # Return to question list
    return await list_questions(update, context)

async def edit_q_text_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✏️ Enter the new question text:")
    return EDIT_Q_TEXT

async def edit_q_text_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_text = update.message.text
    q_id = context.user_data['mg_q_id']
    
    QuizService.update_question(q_id, {'question_text': new_text})
    await update.message.reply_text("✅ Question text updated!")
    
    # Manually trigger details view
    class FakeQuery:
        def __init__(self, message, q_id):
            self.message = message
            self.data = f"mg_q_item_{q_id}"
        async def answer(self): pass
        async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
            return await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

    update.callback_query = FakeQuery(update.message, q_id)
    return await show_question_details(update, context)

async def edit_q_options_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✏️ Enter the new options in this format:\n"
        "A: option text\n"
        "B: option text\n"
        "C: option text\n"
        "D: option text"
    )
    return EDIT_Q_OPTIONS

async def edit_q_options_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = update.message.text.split('\n')
    try:
        options = {}
        for line in lines:
            if ':' not in line: continue
            key, val = line.split(':', 1)
            options[key.strip().upper()] = val.strip()
            
        if len(options) < 4: raise ValueError("Missing options")
        
        data = {
            'option_a': options['A'],
            'option_b': options['B'],
            'option_c': options['C'],
            'option_d': options['D']
        }
        
        QuizService.update_question(context.user_data['mg_q_id'], data)
        await update.message.reply_text("✅ Options updated!")
    except Exception:
        await update.message.reply_text("❌ Invalid format. Please try again.")
        return EDIT_Q_OPTIONS
        
    # Manually trigger details view
    class FakeQuery:
        def __init__(self, message, q_id):
            self.message = message
            self.data = f"mg_q_item_{q_id}"
        async def answer(self): pass
        async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
            return await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

    update.callback_query = FakeQuery(update.message, context.user_data['mg_q_id'])
    return await show_question_details(update, context)

async def edit_q_answer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("A", callback_data="mg_ans_A"), InlineKeyboardButton("B", callback_data="mg_ans_B")],
        [InlineKeyboardButton("C", callback_data="mg_ans_C"), InlineKeyboardButton("D", callback_data="mg_ans_D")]
    ]
    await query.edit_message_text("✏️ Select the correct answer:", reply_markup=InlineKeyboardMarkup(keyboard))
    return EDIT_Q_ANSWER

async def edit_q_answer_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    new_ans = query.data.split('_')[2]
    QuizService.update_question(context.user_data['mg_q_id'], {'correct_answer': new_ans})
    
    await query.edit_message_text(f"✅ Correct answer set to {new_ans}!")
    return await show_question_details(update, context)
