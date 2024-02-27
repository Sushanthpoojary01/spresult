import datetime
import pytz
import re
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
from telegram.utils.helpers import escape_markdown
from telegram.error import Unauthorized, BadRequest
import requests
from bs4 import BeautifulSoup
from keep_alive import keep_alive

keep_alive()
# Replace 'YOUR_BOT_TOKEN' with your actual bot token
TOKEN = os.environ.get('TOKEN')
#TOKEN = '6317382912:AAGF4ELdq-qhQQAJFcEjfe-iUw6rknbhpbg'

# Replace 'CHANNEL_USERNAME' with the username of the channel you want to forward messages from
CHANNEL_USERNAME = 'efghijkll'

# Replace 'GROUP_CHAT_IDS' with the IDs of the groups you want to forward messages to
GROUP_CHAT_IDS = [-1001921827807, -1001173211941]  # List of target group chat IDs
RELAY_GROUP_ID = -1001977723321
RELAY_GROUP_CHAT_ID = -1001978328470

specific_chat_id = -1001173211941

SUBSCRIBERS_FILE = 'subscribers2.txt'
SUBSCRIBERS = set()
CHAT_IDS_FILE = 'chat_ids2.txt'
CHAT_IDS = set()
FORWARDED_MESSAGE_IDS = set()

user_messages = {}

latest_message_timestamp = None

def is_valid_message(text):
    lines = text.strip().split('\n')

    if len(lines) != 6 or lines[1] or lines[4]:
        return False

    try:
        date_str = lines[0].strip()
        datetime.datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        return False

    market_name = lines[2].strip().upper()
    allowed_market_names = [
        'SRIDEVI DAY', 'SUPREME DAY', 'TIME BAZAR', 'MADHUR DAY', 'MILAN DAY', 'RAJDHANI DAY', 'SUPREME DAY', 'KALYAN', 'Kalyan', 'STATUS',
        'SRIDEVI NIGHT', 'SUPREME NIGHT', 'MADHUR NIGHT', 'SUPREME NIGHT', 'MILAN NIGHT', 'KALYAN NIGHT', 'RAJDHANI NIGHT', 'MAIN BAZAR'
    ]
    if market_name not in allowed_market_names:
        return False

    # Define the time ranges for allowed markets in Asia/Kolkata timezone
    allowed_market_times = {
        'SRIDEVI DAY': [('11:33', '11:45'), ('12:33', '12:45')],
        'TIME BAZAR': [('13:00', '13:19'), ('14:00', '14:19')],
        'MADHUR DAY': [('13:31', '13:49'), ('14:31', '14:49')],
        'MILAN DAY': [('15:00', '15:25'), ('17:00', '17:25')],
        'RAJDHANI DAY': [('15:10', '15:24'), ('17:10', '17:24')],
        'SUPREME DAY': [('15:33', '15:49'), ('17:33', '17:49')],
        'KALYAN': [('16:13', '16:32'), ('17:13', '18:36')],
        'SRIDEVI NIGHT': [('18:58', '19:08'), ('19:58', '20:08')],
        'MADHUR NIGHT': [('20:30', '20:59'), ('22:30', '22:59')],
        'SUPREME NIGHT': [('20:41', '20:55'), ('22:41', '22:55')],
        'MILAN NIGHT': [('20:59', '21:25'), ('22:59', '23:25')],
        'KALYAN NIGHT': [('21:25', '21:49'), ('23:32', '23:56')],
        'RAJDHANI NIGHT': [('21:32', '21:52'), ('23:42', '23:59')],
        'MAIN BAZAR': [('21:50', '22:05'), ('00:00', '00:35')]
    }

    # Get the current time in Asia/Kolkata timezone
    ist_timezone = pytz.timezone('Asia/Kolkata')
    current_time_ist = datetime.datetime.now(ist_timezone).strftime('%H:%M')

    # Check if the current time is within the allowed market time range
    for start_time, end_time in allowed_market_times[market_name]:
        if start_time <= current_time_ist <= end_time:
            return True

    return False

    link_line = lines[5].strip()
    if not any(x in link_line for x in [".com", ".org", ".net"]):
        return False

    return True

def is_valid_live_results_message(text):
    lines = text.strip().split('\n')

    # Check if there are at least 13 lines
    if len(lines) < 13:
        return False

    # Check if the first line starts with 'LIVE RESULTS ✅'
    if not lines[0].strip().startswith('LIVE RESULTS ✅'):
        return False
    market_name = lines[4].strip().upper()
    # Check if the 5th line contains a valid market name
    allowed_market_names = [
        'SRIDEVI', 'SRIDEVI DAY', 'TIME BAZAR', 'MADHUR DAY', 'MADHUR', 'MILAN DAY', 'RAJDHANI DAY', 'SUPREME DAY', 'KALYAN', 'Kalyan', 'STATUS',
        'SRIDEVI NIGHT', 'SUPREME NIGHT', 'MADHUR NIGHT', 'SUPREME NIGHT', 'MILAN NIGHT', 'KALYAN NIGHT', 'RAJDHANI NIGHT', 'MAIN BAZAR', 'MAIN BAZAAR'
    ]
    if lines[4].strip() not in allowed_market_names:
        return False

    if not (any(char.isdigit() for char in lines[6]) or any(char.isdigit() for char in lines[7])):
        return False

    # Define the time ranges for allowed markets in Asia/Kolkata timezone
    allowed_market_times = {
        'SRIDEVI': [('11:13', '11:49'), ('12:33', '12:45')],
        'TIME BAZAR': [('13:00', '13:49'), ('14:00', '14:19')],
        'MADHUR DAY': [('13:31', '13:49'), ('14:31', '14:49')],
        'MILAN DAY': [('15:00', '15:25'), ('17:00', '17:25')],
        'RAJDHANI DAY': [('15:10', '15:24'), ('17:10', '17:24')],
        'SUPREME DAY': [('15:33', '15:49'), ('17:33', '17:49')],
        'KALYAN': [('16:19', '16:45'), ('17:18', '18:46')],
        'SRIDEVI NIGHT': [('18:58', '19:13'), ('19:58', '20:13')],
        'MADHUR NIGHT': [('20:30', '20:49'), ('22:30', '22:49')],
        'SUPREME NIGHT': [('20:41', '20:55'), ('22:41', '22:55')],
        'MILAN NIGHT': [('20:59', '21:25'), ('22:59', '23:25')],
        'KALYAN NIGHT': [('21:25', '21:49'), ('23:32', '23:56')],
        'RAJDHANI NIGHT': [('21:32', '21:52'), ('23:42', '23:59')],
        'MAIN BAZAAR': [('21:50', '21:59'), ('00:00', '00:35')],
        'MAIN BAZAR': [('21:50', '21:59'), ('00:00', '00:35')]
    }

    # Get the current time in Asia/Kolkata timezone
    ist_timezone = pytz.timezone('Asia/Kolkata')
    current_time_ist = datetime.datetime.now(ist_timezone).strftime('%H:%M')

    # Check if the current time is within the allowed market time range
    for start_time, end_time in allowed_market_times[market_name]:
        if start_time <= current_time_ist <= end_time:
            return True

    return False
    # All conditions passed, return True
    return True

def modify_message(text):
    lines = text.strip().split('\n')

    allowed_market_line = lines[4]
    numbers_line = None

    # Find the line that contains digits
    for line in lines:
        if any(char.isdigit() for char in line):
            numbers_line = line
            break

    if numbers_line is None:
        return "Numbers line not found."

    modified_link = (
        "⌖⋙📲 SFG BOOKIE📱⋘<\n\n"
        "     ❣ 8817556937 ❣\n\n"
        "           🏆❤"
    )

    modified_text = (
        f"✧✺❖LIVE RESULTS❖✺✧\n\n"
        f"  {allowed_market_line}\n\n"
        f"  {numbers_line}\n\n{modified_link}\n\n@joinsattama❤ @kalyanmatkaliveresults️"
    )

    return modified_text

def modify_custom_message(text):
    lines = text.strip().split('\n')

    allowed_market_line = lines[4]
    numbers_line = None

    # Find the line that contains digits
    for line in lines:
        if any(char.isdigit() for char in line):
            numbers_line = line
            break

    if numbers_line is None:
        return "Numbers line not found."

    modified_text = (
        f"✧✺❖ LIVE RESULTS ❖✺✧\n\n"
        f"     {allowed_market_line}\n\n"
        f"       {numbers_line}\n\n"
        f"    FAST AND ACCURATE 🚀\n\n    @kalyanmatkaliveresults"
    )

    return modified_text

def modify_live_message(text):
    lines = text.strip().split('\n')
    date_line = lines[0]
    allowed_market_line = lines[2]
    numbers_line = lines[3]  # Escape hyphens

    modified_text = (
        f"✧✺❖ LIVE RESULTS ❖✺✧\n\n"
        f"       {date_line}\n\n       {allowed_market_line}\n\n"
        f"       {numbers_line}\n\n"
        f"    FAST AND ACCURATE 🚀\n\n    @kalyanmatkaliveresults"
    )

    return modified_text


def subscribe(update, context):
    user = update.message.from_user
    user_id = user.id
    user_name = user.first_name
    full_name = user.full_name

    chat = update.effective_chat
    chat_name = chat.title

    # Check if the user is already a subscriber
    if (user_id, user_name) in SUBSCRIBERS:
        update.message.reply_text("Welcome to SATTA MATKA LIVE UPDATES.\nYou are already subscribed to result updates.\nJoin @kalyanmatkaliveresults for Official Live Updates.")
        print(f"User {full_name or user_name} started the bot.")

        # Send the welcome message to the relay group
        context.bot.send_message(chat_id=RELAY_GROUP_CHAT_ID, text=f"User {full_name or user_name} Welcome to SATTA MATKA LIVE UPDATES.\nYou are already subscribed to result updates.\nJoin @kalyanmatkaliveresults for Official Live Updates.")
        print(f"User {full_name or user_name} started the bot in the relay group.")
    else:
        # Get the current time
        your_timezone = pytz.timezone('Asia/Kolkata')

        # Get the current time in the specified time zone
        current_time = datetime.datetime.now(your_timezone)
        time_of_day = "morning"  # Default to morning

        # Define time ranges for different greetings
        if 1 <= current_time.hour < 12:
            time_of_day = "morning"
        elif 12 <= current_time.hour < 17:
            time_of_day = "afternoon"
        elif 17 <= current_time.hour:
            time_of_day = "evening"

        # Send a welcome message with a greeting based on the time of the day
        if full_name:
            welcome_message = f"Good {time_of_day}, {full_name}!\nWelcome to SATTA MATKA LIVE UPDATES.\nJoin @kalyanmatkaliveresults for Official Live Updates."
        else:
            welcome_message = f"Good {time_of_day}, {user_name}!\nWelcome to SATTA MATKA LIVE UPDATES.\nJoin @kalyanmatkaliveresults for Official Live Updates."

        # Send the welcome message to the user
        context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)
        print(f"User {full_name or user_name} started the bot.")

        # Send the welcome message to the relay group
        context.bot.send_message(chat_id=RELAY_GROUP_CHAT_ID, text=welcome_message)
        print(f"User {full_name or user_name} started the bot in the relay group.")

        subscribers.add((user_id, full_name or user_name))
        save_subscribers()
        update.message.reply_text("You have subscribed to result updates. You will receive results from me. Make me admin in groups or channel and send /updates there to get live updates")
        print(f"User {full_name or user_name} started the bot in {chat_name}.")

        with open(SUBSCRIBERS_FILE, 'a') as f:
            f.write(f"# User ID: {user_id}, User Name: {full_name}\n")

# Function to save subscribers to a file
def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, "r") as file:
            lines = file.readlines()
            for line in lines:
                if line.startswith("# User ID: "):
                    user_id = int(re.search(r"# User ID: (\d+), User Name: (.+)", line).group(1))
                    user_name = re.search(r"# User ID: (\d+), User Name: (.+)", line).group(2)
                    SUBSCRIBERS.add((user_id, user_name))
    except FileNotFoundError:
        pass

load_subscribers()

def save_subscribers():
    with open(SUBSCRIBERS_FILE, "w") as file:
        for user_id, user_name in SUBSCRIBERS:
            file.write(f"# User ID: {user_id}, User Name: {user_name}\n")

def update_command(update, context):
    chat = update.effective_chat
    user = update.effective_user
    chat_id = chat.id
    user_id = user.id

    if context.bot.get_chat_member(chat_id, user_id).status in ('creator', 'administrator'):
        CHAT_IDS.add(chat_id)
        with open(CHAT_IDS_FILE, 'a') as f:
            f.write(f"# Chat ID: {chat_id}, Chat Name: {chat.title}\n")  # Include chat title
        update.message.reply_text("This chat has been added to receive updates.")
    else:
        update.message.reply_text("You must be an admin to add this chat for updates.")

def send_to_saved_chats(context, text):
    try:
        for chat_id in CHAT_IDS:
            try:
                context.bot.send_message(chat_id=chat_id, text=text)
                print(f"Message sent successfully to chat ID: {chat_id}")
            except Unauthorized as e:
                BLOCKED_USERS.add(chat_id)
                print(f"User {chat_id} has blocked the bot.")
            except ChatNotFound as e:
                print(f"Chat ID {chat_id} not found. The bot may have left the chat.")
            except Exception as e:
                print(f"Error in send_to_saved_chats: {e}, Chat ID: {chat_id}")
    except Exception as e:
        print(f"Error in send_to_saved_chats (outer): {e}")



def send_to_subscribers(context, text):
    for user_id, _ in SUBSCRIBERS:
        context.bot.send_message(chat_id=user_id, text=text)

BLOCKED_USERS = set()

def is_user_blocked(context, user_id):
    try:
        context.bot.send_message(chat_id=user_id, text="Checking if blocked")
    except Unauthorized as e:
        return True  # User has blocked the bot
    return False  # User has not blocked the bot

def forward_message(update, context):
    try:
        message = update.effective_message
        text = message.text
        message_id = message.message_id

        if message_id in FORWARDED_MESSAGE_IDS:
            return

        if datetime.datetime.today().weekday() == 6:  # Sunday
            if message.chat.username == CHANNEL_USERNAME and is_valid_message(text):
                modified_live_text = modify_live_message(text)
                modified_live_text = escape_markdown(modified_live_text, version=2)
                modified_live_text = f"**{modified_live_text}**"
                # Forward to groups
                # Forward to channels
                for chat_id in GROUP_CHAT_IDS:
                    try:
                        context.bot.send_message(chat_id=chat_id, text=modified_live_text)
                    except Unauthorized:
                        print(f"Group chat {chat_id} has blocked the bot.")
                try:
                    context.bot.send_message(chat_id="@kalyanmatkaliveresults", text=modified_live_text)
                except Unauthorized:
                    print("Channel @kalyanmatkaliveresults has blocked the bot.")
                # Forward to saved chat IDs
                for chat_id in CHAT_IDS:
                    if chat_id not in BLOCKED_USERS:
                        try:
                            context.bot.send_message(chat_id=chat_id, text=modified_live_text)
                        except Unauthorized:
                            BLOCKED_USERS.add(chat_id)
                            print(f"User {chat_id} has blocked the bot.")
                    else:
                        print(f"User {chat_id} has blocked the bot.")
                # Send to saved chats
                send_to_saved_chats(context, modified_live_text)
                context.bot.send_message(chat_id="-1001973683766", text=modified_live_text)
                # Forward to subscribers
                for user_id, _ in subscribers:
                    if user_id not in BLOCKED_USERS:
                        try:
                            context.bot.send_message(chat_id=user_id, text=modified_live_text)
                        except Unauthorized:
                            BLOCKED_USERS.add(user_id)
                            print(f"User {user_id} has blocked the bot.")
                    else:
                        print(f"User {user_id} has blocked the bot.")
                FORWARDED_MESSAGE_IDS.add(message_id)
        else:
            if message.chat.username == CHANNEL_USERNAME and is_valid_live_results_message(text):
                modified_text = modify_message(text)
                modified_text = escape_markdown(modified_text, version=2)
                modified_text = f"**{modified_text}**"
                modified_text_custom = modify_custom_message(text)
                modified_text_custom = escape_markdown(modified_text_custom, version=2)
                modified_text_custom = f"**{modified_text_custom}**"
                for chat_id in GROUP_CHAT_IDS:
                    try:
                        context.bot.send_message(chat_id=chat_id, text=modified_text)
                    except Unauthorized:
                        print(f"Group chat {chat_id} has blocked the bot.")
                # Forward to groups
                try:
                    context.bot.send_message(chat_id="@kalyanmatkaliveresults", text=modified_text_custom)
                except Unauthorized:
                    print("Channel @kalyanmatkaliveresults has blocked the bot.")
                context.bot.send_message(chat_id="-1001973683766", text=modified_text_custom)
                send_to_saved_chats(context, modified_text_custom)
                for chat_id in CHAT_IDS:
                    if chat_id not in BLOCKED_USERS:
                        try:
                            context.bot.send_message(chat_id=chat_id, text=modified_text_custom)
                        except Unauthorized:
                            BLOCKED_USERS.add(chat_id)
                            print(f"User {chat_id} has blocked the bot.")
                    else:
                        print(f"User {chat_id} has blocked the bot.")
                for user_id, _ in subscribers:
                    if user_id not in BLOCKED_USERS:
                        try:
                            context.bot.send_message(chat_id=user_id, text=modified_text_custom)
                        except Unauthorized:
                            BLOCKED_USERS.add(user_id)
                            print(f"User {user_id} has blocked the bot.")
                    else:
                        print(f"User {user_id} has blocked the bot.")
                FORWARDED_MESSAGE_IDS.add(message_id)
    except Unauthorized as e:
        if update.effective_user:
            blocked_user_id = update.effective_user.id
            if (blocked_user_id, None) in SUBSCRIBERS:
                SUBSCRIBERS.remove((blocked_user_id, None))
                save_subscribers()
                BLOCKED_USERS.add(blocked_user_id)
                print(f"User {blocked_user_id} has blocked the bot and has been removed from subscribers.")
            else:
                BLOCKED_USERS.add(blocked_user_id)
                print(f"User {blocked_user_id} has blocked the bot.")
    except Exception as e:
        print(f"An error occurred: {e}")


 # Send the custom modified message to the specific group chat
        #context.bot.send_message(chat_id=-1001973683766, text=modified_text_custom)

def ask_send_destination(update, context, message):
    keyboard = [
        [
            InlineKeyboardButton("Send to SUBSCRIBERS", callback_data="send_to_subscribers"),
            InlineKeyboardButton("Send to CHAT IDS", callback_data="send_to_chat_ids"),
        ],
        [
            InlineKeyboardButton("Send to CHANNEL", callback_data="send_to_channel"),
            InlineKeyboardButton("Send to ALL THE ABOVE", callback_data="send_to_all"),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    question = "Where would you like to send the message?"
    context.user_data['message'] = message  # Save the message in user_data
    update.message.reply_text(question, reply_markup=reply_markup)

def relay_message(update: Update, context: CallbackContext):
    if update.effective_chat.id == RELAY_GROUP_ID:
        # Check if the update contains a message
        if update.message and update.message.text:
            message = update.message.text
            print(f"Received message: {message}")
            # Ask the sender where they want to send the message
            ask_send_destination(update, context, message)

def button_callback(update, context):
    query = update.callback_query
    data = query.data
    message = context.user_data.get('message', None)
    message = escape_markdown(message, version=2)

    if message is not None:
        if data == "send_to_subscribers":
            for user_id, _ in SUBSCRIBERS:
                try:
                    context.bot.send_message(chat_id=user_id, text=message)
                except Unauthorized:
                    print(f"User {user_id} has blocked the bot.")
            query.answer("Message sent to SUBSCRIBERS")
        elif data == "send_to_chat_ids":
            for chat_id in CHAT_IDS:
                try:
                    context.bot.send_message(chat_id=chat_id, text=message)
                except BadRequest as e:
                    if "Chat not found" in str(e):
                        print(f"Ignoring error for chat ID {chat_id}: {e}")
                    else:
                        print(f"Error sending message to chat ID {chat_id}: {e}")
            query.answer("Message sent to CHAT IDS")
        elif data == "send_to_channel":
            context.bot.send_message(chat_id='@kalyanmatkaliveresults', text=message)
            query.answer("Message sent to CHANNEL")
        elif data == "send_to_all":
            for user_id, _ in SUBSCRIBERS:
                try:
                    context.bot.send_message(chat_id=user_id, text=message)
                except Unauthorized:
                    print(f"User {user_id} has blocked the bot.")
            with open(CHAT_IDS_FILE, 'r') as f:
                chat_ids = [int(line.strip()) for line in f]
            for chat_id in chat_ids:
                try:
                    context.bot.send_message(chat_id=chat_id, text=message)
                except BadRequest as e:
                    if "Chat not found" in str(e):
                        print(f"Ignoring error for chat ID {chat_id}: {e}")
                    else:
                        print(f"Error sending message to chat ID {chat_id}: {e}")
            context.bot.send_message(chat_id='@kalyanmatkaliveresults', text=message)
            query.answer("Message sent to ALL DESTINATIONS")

    query.answer()

def code(update, context):
    # Handle /code command
    code_message = "@SharathP23"

    context.bot.send_message(chat_id=update.effective_chat.id, text=code_message)

# Define the URL of the website
URL = 'https://dpboss.services/'
urls = 'https://dpboss.services/panel-chart-record/kalyan.php'
KALYANPAN_FILE_PATH = "kalyanpanel.txt"

# Function to fetch live results from the website
def fetch_live_results():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    live_results_div = soup.find('div', class_='liv-rslt')
    live_results = live_results_div.find_all('span', class_='h8')
    live_results_values = live_results_div.find_all('span', class_='h9')
    results = {}
    for market, value in zip(live_results, live_results_values):
        results[market.text.strip()] = value.text.strip()
    return results

# Function to handle the /live command
# Adjusted live function to accept update and context arguments
# Function to handle the /live command
# Adjusted live function to accept update and context arguments
def live(update, context):
    live_results = fetch_live_results()
    if live_results:
        message = "LIVE RESULTS:\n\n"
        for market, value in live_results.items():
            message += f"{market}: {value}\n\n"
        
        # Send the message to the user as a single message
        update.message.reply_text(message)
    else:
        update.message.reply_text("No live results available now, check /result for other market results.")

def result(update, context):
    specific_market_results = fetch_specific_market_results()
    message = "RESULTS:\n\n"
    for market in markets_to_fetch:
        if market in specific_market_results:
            message += f"{market}: {specific_market_results[market]}\n\n"
    return message  # Return the message string instead of sending it directly


def fetch_specific_market_results():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    tkt_val_divs = soup.find_all('div', class_='tkt-val')

    results = {}
    for tkt_val_div in tkt_val_divs:
        markets = tkt_val_div.find_all('div')
        for market in markets:
            market_name = market.find('h4').text.strip()
            if market_name in markets_to_fetch:
                market_value = market.find('span').text.strip()
                results[market_name] = market_value

    return results

# List of markets to fetch results for
markets_to_fetch = ['SRIDEVI', 'TIME BAZAR', 'MADHUR DAY', 'MILAN DAY', 'RAJDHANI DAY', 'SUPREME DAY',
                    'KALYAN', 'SRIDEVI NIGHT', 'SUPREME NIGHT', 'MADHUR NIGHT', 'MILAN NIGHT', 'KALYAN NIGHT',
                    'RAJDHANI NIGHT', 'MAIN BAZAR', 'KARNATAKA DAY', 'MILAN MORNING', 'MADHUR MORNING']
def result_command(update, context):
    # Call the result function to get the result message
    result_message = result(update, context)
    if result_message:
        # Send the result message to the user who sent the command
        update.message.reply_text(result_message)

def send_result_message_3pm(context):
    ist_timezone = pytz.timezone('Asia/Kolkata')
    current_time = datetime.datetime.now(ist_timezone)

    # Check if the current time is 3:59 PM
    if current_time.hour == 18 and current_time.minute == 25:
        # Call the result function to get the result message
        result_message = result(None, context)
        if result_message:
            # Send the result message to the desired chat or channel
            context.bot.send_message(chat_id='@kalyanmatkaliveresults', text=result_message)

# Define the function to send the result message at 12:20 AM
def send_result_message_12am(context):
    ist_timezone = pytz.timezone('Asia/Kolkata')
    current_time = datetime.datetime.now(ist_timezone)

    # Check if the current time is 12:20 AM
    if current_time.hour == 0 and current_time.minute == 17:
        # Call the result function to get the result message
        result_message = result(None, context)
        if result_message:
            # Send the result message to the desired chat or channel
            context.bot.send_message(chat_id='@kalyanmatkaliveresults', text=result_message)
      
JODIFAM_FILE_PATH = "jodifam.txt"
PAN_PATH = "Allpanels.txt"

def jodifam(update: Update, context: CallbackContext) -> None:
    with open(JODIFAM_FILE_PATH, 'r') as file:
        jodifam_text = file.read()
    update.message.reply_text(jodifam_text)

def allpan(update: Update, context: CallbackContext) -> None:
    with open(PAN_PATH, 'r') as file:
        Allpanels = file.read()
    update.message.reply_text(Allpanels)

def main():

    # Your main function where you initialize and start the bot
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher
            # Register the message handler
    message_handler = MessageHandler(Filters.text & Filters.update.channel_post, forward_message)
    dispatcher.add_handler(message_handler)

    start_handler = CommandHandler('start', subscribe)
    dispatcher.add_handler(start_handler)

    updates_handler = CommandHandler('updates', update_command)
    dispatcher.add_handler(updates_handler)

    dispatcher.add_handler(CommandHandler("live", live))
    dispatcher.add_handler(CommandHandler("result", result_command))
    dispatcher.add_handler(CommandHandler("jodifam", jodifam))

    dispatcher.add_handler(CommandHandler("allpan", allpan))

    button_handler = CallbackQueryHandler(button_callback)
    dispatcher.add_handler(button_handler)

    relay_handler = MessageHandler(Filters.text & (~Filters.command), relay_message)
    dispatcher.add_handler(relay_handler)

    code_handler = CommandHandler('code', code)
    dispatcher.add_handler(code_handler)

    updater.job_queue.start()
    job_queue = updater.job_queue
    job_queue.run_daily(send_result_message_3pm, time=datetime.time(18, 25, tzinfo=pytz.timezone('Asia/Kolkata')))
    job_queue.run_daily(send_result_message_12am, time=datetime.time(0, 17, tzinfo=pytz.timezone('Asia/Kolkata')))


            # Start the bot to receive updates using getUpdates method
    updater.start_polling()

            # Run the bot until you press Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()

