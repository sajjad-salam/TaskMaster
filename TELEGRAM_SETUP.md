# Telegram Bot Setup for TaskMaster

## How to Setup Telegram Bot Integration

### Step 1: Install Required Library
Open terminal/command prompt and run:
```bash
pip install pyTelegramBotAPI
```

### Step 2: Create Your Telegram Bot
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "MyTaskMasterBot")
4. Choose a username (e.g., "MyTaskMasterBot")
5. Copy the **bot token** (looks like: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`)

### Step 3: Configure TaskMaster
1. Open the file `telegram_config.json` in the TaskMaster folder
2. Replace `YOUR_BOT_TOKEN_HERE` with your bot token
3. Set `"enabled": true`

Example:
```json
{
  "bot_token": "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ",
  "enabled": true,
  "instructions": "..."
}
```

### Step 4: Run TaskMaster
- Start TaskMaster with `python app.py`
- The bot will automatically start
- You'll see "🤖 Telegram bot is running..." in the console

### How to Use
1. Open Telegram and find your bot
2. Send `/start` to see welcome message
3. Send any text message → it will be saved as a pending task
4. When you open TaskMaster, pending tasks are automatically imported!

### Features
- ✅ Send tasks from anywhere via Telegram
- ✅ Tasks are saved while app is closed
- ✅ Auto-import when you open TaskMaster
- ✅ Tasks go to "General" folder
- ✅ Bot only runs when TaskMaster is running

### Commands
- `/start` - Welcome message
- `/help` - Show help
- `/tasks` - Count pending tasks

### Troubleshooting
**Bot not responding?**
- Check that `telegram_config.json` has `"enabled": true`
- Check that the bot token is correct
- Make sure you installed `pyTelegramBotAPI`

**Tasks not importing?**
- Check console for error messages
- Make sure `pending_telegram_tasks.json` exists in the folder
