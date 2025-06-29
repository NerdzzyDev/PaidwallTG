Antow New Life Telegram Bot

A Telegram bot with paywall functionality for channel access.

Setup





Clone the Repository:

git clone <your-repository-url>
cd antow_new_life_bot



Install Dependencies:

pip install -r requirements.txt



Set Up PostgreSQL:





Install PostgreSQL and create a database named antow_new_life.



Update the .env file with your database credentials, bot token, admin ID, and channel ID.



Run the Bot:

python -m app.bot

Environment Variables





BOT_TOKEN: Your Telegram bot token from BotFather.



ADMIN_ID: Telegram ID of the admin.



CHANNEL_ID: Telegram channel ID (e.g., @YourChannelName).



PAYMENT_LINK: URL for payment instructions.



DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE: PostgreSQL connection details.

Features





Users can start the bot and receive payment instructions.



Users with active subscriptions receive a channel link.



Admins can approve or reject payment screenshots.



Admins can reply to users using /reply_<user_id> <message>.



Scheduler checks for expiring/expired subscriptions daily, sending reminders and removing users from the channel as needed.