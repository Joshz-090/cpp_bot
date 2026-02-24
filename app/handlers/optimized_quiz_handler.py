import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from ..services.optimized_quiz_service import (
    OptimizedQuizService, 
    AdminMiddleware,
    QuizSession
)
from ..services.user_service import UserService

logger = logging.getLogger(__name__)

class OptimizedQuizHandler:
    """High-performance quiz handler with session caching"""
    
    @staticmethod
    async def start_optimized_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_id: int):
        """Start a quiz with optimized session management"""
        telegram_id = update.effective_user.id
        
        # Verify user registration
        if not UserService.is_registered(telegram_id):
            await update.message.reply_text("🛑 Please /start to register before taking quizzes.")
            return
        
        # Get user from database
        user = UserService.get_or_create_user(telegram_id, update.effective_user.username, update.effective_user.full_name)
        
        try:
            # Create optimized quiz session
            session = await OptimizedQuizService.start_quiz_session(user.id, telegram_id, quiz_id)
            
            # Send first question immediately
            await OptimizedQuizHandler._send_question(update, context, session)
            
        except ValueError as e:
            await update.message.reply_text(f"❌ Error starting quiz: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error starting quiz: {e}")
            await update.message.reply_text("❌ An unexpected error occurred. Please try again.")
    
    @staticmethod
    async def handle_answer_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle answer submission with immediate feedback"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = update.effective_user.id
        user = UserService.get_or_create_user(telegram_id, update.effective_user.username, update.effective_user.full_name)
        
        try:
            # Extract answer from callback data
            callback_data = query.data
            if not callback_data.startswith("quiz_answer_"):
                return
            
            selected_answer = callback_data.split("_")[-1]  # Extract A, B, C, or D
            
            # Submit answer using optimized service
            result = await OptimizedQuizService.submit_answer_in_session(user.id, selected_answer)
            
            # Provide immediate feedback
            await OptimizedQuizHandler._send_feedback(query, result)
            
            # If quiz is completed, show final results
            if result.get('quiz_completed'):
                await OptimizedQuizHandler._send_final_results(query, result)
            else:
                # Send next question
                await OptimizedQuizHandler._send_next_question(query, result)
                
        except ValueError as e:
            await query.edit_message_text(f"❌ {str(e)}")
        except Exception as e:
            logger.error(f"Error handling answer submission: {e}")
            await query.edit_message_text("❌ An error occurred processing your answer.")
    
    @staticmethod
    async def handle_quiz_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Resume an existing quiz session"""
        telegram_id = update.effective_user.id
        user = UserService.get_or_create_user(telegram_id, update.effective_user.username, update.effective_user.full_name)
        
        session = await OptimizedQuizService.get_active_session(user.id)
        if not session:
            await update.message.reply_text("📝 No active quiz session. Start a new quiz!")
            return
        
        await OptimizedQuizHandler._send_question(update, context, session)
    
    @staticmethod
    async def handle_quiz_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quiz timeout and force completion"""
        telegram_id = update.effective_user.id
        user = UserService.get_or_create_user(telegram_id, update.effective_user.username, update.effective_user.full_name)
        
        result = await OptimizedQuizService.force_complete_session(user.id)
        if result:
            await OptimizedQuizHandler._send_timeout_results(update, result)
    
    @staticmethod
    async def _send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, session: QuizSession):
        """Send current question with inline keyboard"""
        question_data = await OptimizedQuizService.get_current_question(session.user_id)
        if not question_data:
            await update.message.reply_text("❌ No question available.")
            return
        
        question = question_data['question']
        progress = question_data['progress']
        time_remaining = int(question_data['time_remaining'])
        
        # Format question text
        question_text = (
            f"📝 *Question {progress[0]} of {progress[1]}*\n\n"
            f"{question['question_text']}\n\n"
            f"⏱️ Time remaining: {time_remaining//60}:{time_remaining%60:02d}"
        )
        
        # Create inline keyboard with options
        keyboard = []
        options = [
            ('A', question['option_a']),
            ('B', question['option_b']),
            ('C', question['option_c']),
            ('D', question['option_d'])
        ]
        
        for label, text in options:
            keyboard.append([InlineKeyboardButton(
                f"{label}. {text}", 
                callback_data=f"quiz_answer_{label}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                question_text, 
                reply_markup=reply_markup, 
                parse_mode="Markdown"
            )
        else:
            await update.callback_query.edit_message_text(
                question_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    
    @staticmethod
    async def _send_feedback(query, result: Dict[str, Any]):
        """Send immediate feedback for answer"""
        is_correct = result['is_correct']
        explanation = result.get('explanation', '')
        
        feedback_emoji = "✅" if is_correct else "❌"
        feedback_text = f"{feedback_emoji} {'Correct!' if is_correct else 'Incorrect!'}"
        
        if explanation:
            feedback_text += f"\n\n💡 *Explanation:* {explanation}"
        
        await query.edit_message_text(
            feedback_text,
            parse_mode="Markdown"
        )
    
    @staticmethod
    async def _send_next_question(query, result: Dict[str, Any]):
        """Send next question after feedback"""
        next_question = result.get('next_question')
        progress = result.get('progress', (0, 0))
        
        if not next_question:
            return
        
        question_text = (
            f"📝 *Question {progress[0]} of {progress[1]}*\n\n"
            f"{next_question['question_text']}"
        )
        
        keyboard = []
        options = [
            ('A', next_question['option_a']),
            ('B', next_question['option_b']),
            ('C', next_question['option_c']),
            ('D', next_question['option_d'])
        ]
        
        for label, text in options:
            keyboard.append([InlineKeyboardButton(
                f"{label}. {text}", 
                callback_data=f"quiz_answer_{label}"
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.bot.send_message(
            chat_id=query.message.chat_id,
            text=question_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    @staticmethod
    async def _send_final_results(query, result: Dict[str, Any]):
        """Send final quiz results"""
        final_score = result['final_score']
        total_questions = result['total_questions']
        accuracy = (final_score / total_questions * 100) if total_questions > 0 else 0
        
        results_text = (
            f"🎉 *Quiz Completed!*\n\n"
            f"📊 Final Score: {final_score}/{total_questions}\n"
            f"🎯 Accuracy: {accuracy:.1f}%\n"
        )
        
        if accuracy >= 80:
            results_text += "🏆 Excellent work!"
        elif accuracy >= 60:
            results_text += "👍 Good effort!"
        else:
            results_text += "📚 Keep practicing!"
        
        await query.bot.send_message(
            chat_id=query.message.chat_id,
            text=results_text,
            parse_mode="Markdown"
        )
    
    @staticmethod
    async def _send_timeout_results(update, result: Dict[str, Any]):
        """Send timeout results"""
        final_score = result['final_score']
        total_questions = result['total_questions']
        questions_answered = result['questions_answered']
        
        timeout_text = (
            f"⏰ *Time's Up!*\n\n"
            f"📊 Score: {final_score}/{total_questions}\n"
            f"📝 Questions answered: {questions_answered}/{total_questions}\n"
            f"⏱️ Time taken: {result['time_taken']:.1f} seconds\n"
        )
        
        await update.message.reply_text(timeout_text, parse_mode="Markdown")

class AdminQuizHandler:
    """Admin operations with middleware authorization"""
    
    @staticmethod
    async def add_question_to_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add question with admin authorization check"""
        # Verify admin role
        if not await AdminMiddleware.verify_admin_or_chat_admin(update, context):
            await update.message.reply_text("🚫 Admin access required.")
            return
        
        # Proceed with question addition logic
        await update.message.reply_text("✅ Admin verified. Proceeding with question addition...")
        # Implementation would continue here
    
    @staticmethod
    async def broadcast_to_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast message with admin authorization"""
        # Verify admin role
        if not await AdminMiddleware.verify_admin_or_chat_admin(update, context):
            await update.message.reply_text("🚫 Admin access required.")
            return
        
        # Proceed with broadcast logic
        await update.message.reply_text("✅ Admin verified. Proceeding with broadcast...")
        # Implementation would continue here

# Register handlers
def register_optimized_quiz_handlers(application):
    """Register optimized quiz handlers with the application"""
    application.add_handler(CallbackQueryHandler(
        OptimizedQuizHandler.handle_answer_submission,
        pattern=r"^quiz_answer_[ABCD]$"
    ))
    
    # Add other handlers as needed
    # application.add_handler(CommandHandler("resume_quiz", OptimizedQuizHandler.handle_quiz_resume))
    # application.add_handler(CommandHandler("admin_add_question", AdminQuizHandler.add_question_to_quiz))
