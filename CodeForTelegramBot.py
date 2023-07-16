import matplotlib
matplotlib.use('Agg')

from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, Filters
import matplotlib.pyplot as plt
import sqlite3
import threading
import random
import numpy as np



# Create a connection to the SQLite database
conn = sqlite3.connect('fitness.db', check_same_thread=False)
cursor = conn.cursor()

# Create a table to store user information
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  chat_id INTEGER,
                  username TEXT,
                  name TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS activities
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  activity TEXT,
                  points INTEGER,
                  date TEXT)''')
ACTIVITY = 1





updater = Updater('5949047508:AAGNWqWhs3cELin2ZhkVnm3pQNCkBM93mnY')
dispatcher = updater.dispatcher
db_lock = threading.Lock()

# List of motivational statements
MOTIVATIONAL_QUOTES = [
    "You're doing great! Keep up the good work! 👍",
    "Don't stop until you're proud! 💪",
    "Push yourself because no one else is going to do it for you! 🚀",
    "Success starts with self-discipline! 🌟",
    "The only bad workout is the one that didn't happen! ⚡️",
    "Strive for progress, not perfection! 🌱",
    "Believe in yourself and all that you are! 🌈",
    "Your only limit is you! 💫"
]

MAIN_MENU = (
    "Welcome to the Fitness Competition Bot! 🏋️‍♂️🏆\n\n"
    "You can register using /register command and log your activities using /log command. "
    "Here are the available commands:\n\n"
    "▶️ /start - Start the bot\n"
    "▶️ /register - Register for the fitness competition\n"
    "▶️ /log - Log your fitness activity\n"
    "▶️ /graph - View your fitness progress graph\n"
    "▶️ /winner - View the monthly competition winner\n"
    "▶️ /reset - Reset participant information and start fresh"
)






def start(update: Update, context):
    """Handler for the /start command."""
    update.message.reply_text(MAIN_MENU)


def register(update: Update, context):
    """Handler for the /register command."""
    user = update.message.from_user
    chat_id = user.id
    username = user.username
    name = user.full_name

    # Acquire the lock for database access
    with db_lock:
        # Insert user information into the database
        cursor.execute('INSERT INTO users (chat_id, username, name) VALUES (?, ?, ?)', (chat_id, username, name))
        conn.commit()

    message = f"You have been registered for the fitness competition, {name}! 🎉"
    update.message.reply_text(message)


def log_activity_start(update: Update, context):
    """Handler to start the activity logging conversation."""
    update.message.reply_text("Please enter your fitness activity:")

    return ACTIVITY


def log_activity_end(update: Update, context):
    """Handler to process the logged activity and end the conversation."""
    user = update.message.from_user
    chat_id = user.id
    activity = update.message.text

    # Calculate points for the activity
    points = calculate_points(activity)

    # Acquire the lock for database access
    with db_lock:
        # Insert activity log into the database
        cursor.execute('INSERT INTO activities (user_id, activity, points, date) VALUES (?, ?, ?, datetime("now"))',
                       (chat_id, activity, points))
        conn.commit()



  
    # Retrieve the total points for the user from the database
    cursor.execute('SELECT SUM(points) FROM activities WHERE user_id=?', (chat_id,))
    total_points_user = cursor.fetchone()[0] or 0

    # Send response message with motivational quote and total points
    message = f"Activity logged! 💪\n\nMotivational Quote: {random.choice(MOTIVATIONAL_QUOTES)}\n\n"
    message += f"Total Points: {total_points_user}"
    update.message.reply_text(message)

    return ConversationHandler.END


def calculate_points(activity: str) -> int:
    """Calculate points based on the activity."""
   

    if 'running' in activity.lower():
        return 5
    elif 'cycling' in activity.lower():
        return 3
    elif 'swimming' in activity.lower():
        return 4
    else:
        return 1

def display_graph(update: Update, context):
   
    user = update.message.from_user
    chat_id = user.id

    # Retrieve the points data for the user from the database
    with db_lock:
        cursor.execute('SELECT date, SUM(points) FROM activities WHERE user_id=? GROUP BY date', (chat_id,))
        data = cursor.fetchall()

    if not data:
        update.message.reply_text("No data available for graph.")
        return

    total_points = [row[1] or 0 for row in data]
    x_axis = range(1, len(total_points) + 1)

    # Generate the bar chart
    plt.bar(x_axis, total_points)
    plt.xlabel('Timeline')
    plt.ylabel('Total Points')
    plt.title('Fitness Points Progress')
    plt.grid(True)
    graph_path = 'graph.png'
    plt.savefig(graph_path, dpi=300, bbox_inches='tight')

    # Send the graph image to the user
    update.message.reply_photo(photo=open(graph_path, 'rb'))
    remove_file(graph_path)

def determine_winner() -> str:
    """Determine the monthly winner based on total points."""
    with db_lock:
        cursor.execute('SELECT users.chat_id, users.name, SUM(activities.points) as total_points '
                       'FROM users JOIN activities ON users.id = activities.user_id '
                       'GROUP BY users.chat_id, users.name')
        results = cursor.fetchall()

    if not results:
        return "No winner found."

    # Find the user with the highest total points
    winner = max(results, key=lambda x: x[2])

    return f"🏆 Fitness Competition Winner 🏆\n\nName: {winner[1]}\nChat ID: {winner[0]}\nTotal Points: {winner[2]}"


def announce_winner(update: Update, context):
  winner = determine_winner()
    update.message.reply_text(winner, parse_mode=ParseMode.MARKDOWN)


def reset_data(update: Update, context):
    """Handler for the /reset command to delete participant information."""
    with db_lock:
     
        cursor.execute('DELETE FROM activities')
        conn.commit()
        cursor.execute('DELETE FROM users')
        conn.commit()

    # Clear the graph
    plt.clf()

    update.message.reply_text("Participant information has been reset. You can start fresh.")



def remove_file(file_path: str):
    """Remove a file from the file system."""
    import os
    if os.path.exists(file_path):
        os.remove(file_path)



dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('register', register))
dispatcher.add_handler(CommandHandler('graph', display_graph))
dispatcher.add_handler(CommandHandler('winner', announce_winner))
dispatcher.add_handler(CommandHandler('reset', reset_data))





conv_handler = ConversationHandler(
    entry_points=[CommandHandler('log', log_activity_start)],
    states={
        ACTIVITY: [MessageHandler(Filters.text & ~Filters.command, log_activity_end)]
    },
    fallbacks=[]
)
dispatcher.add_handler(conv_handler)


def main():
    """Start the bot."""
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

# Close the database connection
conn.close()
