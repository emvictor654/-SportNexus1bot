import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Setup Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

# API Configuration (API-Football via RapidAPI or Direct)
FOOTBALL_API_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": FOOTBALL_API_KEY
}

# Key League IDs
LEAGUES = {
    "Premier League": 39,
    "La Liga": 140,
    "UEFA Champions League": 2,
    "Serie A": 135,
    "Bundesliga": 78
}

def fetch_data(endpoint: str, params: dict = None):
    """Utility function to make GET requests to Football API"""
    try:
        response = requests.get(f"{FOOTBALL_API_URL}/{endpoint}", headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("response", [])
    except Exception as e:
        logger.error(f"Error fetching data from API: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    welcome_text = (
        "⚡ *Welcome to SportNexus!* ⚡\n\n"
        "Your smart sports companion for live scores, fixtures, stats & match updates.\n\n"
        "Select an option below to get started:"
    )
    keyboard = [
        [InlineKeyboardButton("⚽ Live Scores", callback_data="live_scores")],
        [InlineKeyboardButton("📅 Today's Fixtures", callback_data="today_fixtures")],
        [InlineKeyboardButton("🏆 Top Leagues", callback_data="leagues_menu")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline button clicks"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "main_menu":
        await start(update, context)

    elif data == "live_scores":
        await query.edit_message_text("🔍 Fetching live matches...")
        matches = fetch_data("fixtures", {"live": "all"})
        
        if not matches:
            text = "❌ No live matches currently in progress."
        else:
            text = "🔴 *LIVE MATCHES*\n\n"
            for m in matches[:10]:  # Limit to 10 for clean display
                home = m["teams"]["home"]["name"]
                away = m["teams"]["away"]["name"]
                gh = m["goals"]["home"]
                ga = m["goals"]["away"]
                elapsed = m["fixture"]["status"]["elapsed"]
                text += f"⏱ `{elapsed}'` - *{home}* {gh} - {ga} *{away}*\n"

        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="live_scores")],
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "today_fixtures":
        await query.edit_message_text("📅 Fetching today's fixtures...")
        import datetime
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        matches = fetch_data("fixtures", {"date": today})

        if not matches:
            text = "❌ No fixtures scheduled for today."
        else:
            text = f"📅 *TODAY'S FIXTURES ({today})*\n\n"
            for m in matches[:10]:
                home = m["teams"]["home"]["name"]
                away = m["teams"]["away"]["name"]
                time = m["fixture"]["date"][11:16]  # Extract HH:MM UTC
                text += f"⏰ `{time} UTC` | {home} vs {away}\n"

        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "leagues_menu":
        text = "🏆 *Select a League to View Top Scorers:*"
        keyboard = []
        for name, l_id in LEAGUES.items():
            keyboard.append([InlineKeyboardButton(name, callback_data=f"league_{l_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("league_"):
        league_id = data.split("_")[1]
        await query.edit_message_text("📊 Fetching league stats...")
        
        # Get top scorers for current season (2024/2025)
        top_scorers = fetch_data("players/topscorers", {"league": league_id, "season": 2024})

        if not top_scorers:
            text = "❌ Top scorers data not available."
        else:
            league_name = top_scorers[0]["statistics"][0]["league"]["name"]
            text = f"⚽ *TOP SCORERS - {league_name}*\n\n"
            for i, item in enumerate(top_scorers[:5], 1):
                p_name = item["player"]["name"]
                goals = item["statistics"][0]["goals"]["total"]
                team = item["statistics"][0]["team"]["name"]
                text += f"{i}. *{p_name}* ({team}) - 🎯 *{goals} Goals*\n"

        keyboard = [[InlineKeyboardButton("🔙 Back to Leagues", callback_data="leagues_menu")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "help":
        help_text = (
            "ℹ️ *SportNexus Bot Help*\n\n"
            "/start - Show main menu\n"
            "/live - Get instant live scores\n\n"
            "For stats & updates, use the inline buttons."
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
        await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable missing!")
        return

    # Build Application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("live", button_handler))

    # Add Callback Query Handler
    app.add_handler(CallbackQueryHandler(button_handler))

    # Run the bot in Polling mode
    logger.info("SportNexus Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
