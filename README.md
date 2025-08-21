Telegram Request Forwarder Bot

A Telegram bot built with Python that helps manage movie and series requests by forwarding them to an admin group in a structured format. Ideal for groups that handle requests regularly.

✨ Features

Accepts requests only if they start with #Request or the word "Request".

Parses the request for Name, Year, Quality, and Language.

Forwards the request to a dedicated admin group with inline buttons for approval.

Admin buttons:

✅ Mark done → Notifies the user the request is fulfilled.

❌ Reject → Notifies the user the request was rejected.

Easy to configure using environment variables (.env).

Handles errors gracefully (timeouts, forbidden access, etc.).

Customizable ETA (default: 12 hours) for fulfilling requests.

📝 Request Format

Users must follow this format when sending a request:

#Request
Name: <Movie/Series Title>
Year: <Release Year>
Quality: <e.g., 1080p, 720p>
Language: <e.g., English, Hindi, Dual Audio>


Example:

#Request
Name: Example Movie
Year: 2024
Quality: 1080p
Language: Hindi


✅ Including all fields ensures faster processing.

⚙️ Setup
1. Clone the repository
git clone https://github.com/YourUsername/direct-forward-bot.git
cd direct-forward-bot

2. Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

3. Install dependencies
pip install -r requirements.txt

4. Configure environment variables

Create a .env file in the project root (or copy .env.example) and fill your credentials:

BOT_TOKEN=your_bot_token_here
BOT_OWNER_ID=your_telegram_id
ADMIN_CHAT_ID=your_admin_group_chat_id


Make sure .env is never pushed to GitHub. .env.example is safe to share.

5. Run the bot
python direct_forward_bot.py

🛠️ Commands

/start → Welcome message & ETA info

/help → Instructions & request format

/setdeadline <hours> → Owner only; change request ETA for future requests

📂 Project Structure
direct-forward-bot/
│-- direct_forward_bot.py   # Main bot code
│-- requirements.txt        # Python dependencies
│-- .env.example            # Example environment file
│-- README.md               # Project documentation
│-- .gitignore              # Ignore secrets & unnecessary files

🖥️ Deployment

You can run the bot on:

Local machine

VPS / Cloud Server (e.g., AWS, DigitalOcean)

Free hosting platforms like Heroku, Render, Railway

👥 Tips for Contributors / Usage

Fork the repo and create a .env file locally with your own bot token and admin chat ID.

Do not commit your .env file to your fork — keep tokens secret.

If you want to modify behavior (like ETA, parsing logic, or admin actions), feel free to edit direct_forward_bot.py.

Submit pull requests if you improve functionality or add features — make sure to exclude secrets.

📜 License

MIT License – free and open-source.
