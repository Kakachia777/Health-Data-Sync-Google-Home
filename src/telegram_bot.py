from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler
)
import asyncio
import logging
from typing import Dict, List, Any
import plotly.express as px
import io
from datetime import datetime, timedelta

class HealthBot:
    def __init__(self, token: str, health_sync):
        self.token = token
        self.health_sync = health_sync
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        """Set up bot command handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("summary", self.summary))
        self.application.add_handler(CommandHandler("alerts", self.alerts))
        
        # Add callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.button_click))
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        keyboard = [
            [
                InlineKeyboardButton("Get Status", callback_data='status'),
                InlineKeyboardButton("View Summary", callback_data='summary')
            ],
            [
                InlineKeyboardButton("Check Alerts", callback_data='alerts'),
                InlineKeyboardButton("Help", callback_data='help')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Welcome to your Health Monitoring Bot! 🏥\n"
            "I can help you track your health metrics and notify you of important changes.\n"
            "Choose an option below or type /help for more information.",
            reply_markup=reply_markup
        )
        
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "Available commands:\n\n"
            "/status - Get current health metrics\n"
            "/summary - View health summary report\n"
            "/alerts - Check active health alerts\n"
            "/help - Show this help message"
        )
        await update.message.reply_text(help_text)
        
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        # Get latest metrics
        metrics = self.health_sync.get_latest_metrics()
        
        status_text = "Current Health Status:\n\n"
        
        if 'weight' in metrics:
            status_text += f"🏋️ Weight: {metrics['weight']['latest']}kg\n"
            
        if 'blood_pressure' in metrics:
            bp = metrics['blood_pressure']['latest']
            status_text += f"💓 BP: {bp['systolic']}/{bp['diastolic']} mmHg\n"
            
        if 'heart_rate' in metrics:
            status_text += f"❤️ HR: {metrics['heart_rate']['latest']} bpm\n"
            
        if 'sleep' in metrics:
            status_text += f"😴 Sleep: {metrics['sleep']['quality']}\n"
            
        await update.message.reply_text(status_text)
        
    async def summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /summary command"""
        # Generate health summary
        summary = self.health_sync.generate_health_summary()
        
        summary_text = "Health Summary Report:\n\n"
        
        for metric, data in summary['metrics'].items():
            if metric == 'weight':
                summary_text += f"🏋️ Weight Trend: {data['trend']}\n{data['analysis']}\n\n"
            elif metric == 'blood_pressure':
                summary_text += f"💓 Blood Pressure: {data['trend']}\n{data['analysis']}\n\n"
            elif metric == 'heart_rate':
                summary_text += (
                    f"❤️ Heart Rate Stats:\n"
                    f"Latest: {data['latest']} bpm\n"
                    f"Variability: {data['variability']:.1f}\n\n"
                )
            elif metric == 'sleep':
                summary_text += (
                    f"😴 Sleep Analysis:\n"
                    f"Average Duration: {data['average_duration']:.1f}h\n"
                    f"Quality: {data['quality']}\n\n"
                )
                
        await update.message.reply_text(summary_text)
        
    async def alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command"""
        alerts = self.health_sync.get_alerts()
        
        if not alerts:
            await update.message.reply_text("No active alerts! 👍")
            return
            
        alerts_text = "Active Health Alerts:\n\n"
        for alert in alerts:
            alerts_text += f"{alert}\n"
            
        await update.message.reply_text(alerts_text)
        
    async def button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'status':
            await self.status(update, context)
        elif query.data == 'summary':
            await self.summary(update, context)
        elif query.data == 'alerts':
            await self.alerts(update, context)
        elif query.data == 'help':
            await self.help(update, context)
            
    async def send_alert(self, chat_id: int, alert_text: str):
        """Send alert to specific chat"""
        await self.application.bot.send_message(
            chat_id=chat_id,
            text=f"🚨 Health Alert:\n\n{alert_text}"
        )
        
    def run(self):
        """Run the bot"""
        self.application.run_polling() 