import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import asyncio
import nest_asyncio
from datetime import datetime, timedelta

nest_asyncio.apply()

SERVICE_ACCOUNT_FILE = 'C:/Users/KVK/Downloads/bot/service_account.json'
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPE)
client = gspread.authorize(creds)
sheet = client.open("График").sheet1

# Состояния
WAITING_FOR_TAG = 1
WAITING_FOR_DATE = 2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_tag = "@" + update.effective_user.username
    
    if user_tag is None:
        await update.message.reply_text("У вас нет тега. Пожалуйста, введите его вручную с помощью команды /tag.")
        return

    context.user_data['name'] = user_tag
    context.user_data['state'] = WAITING_FOR_DATE

    all_users = sheet.row_values(1)
    if user_tag in all_users:
        user_col = all_users.index(user_tag) + 1
        context.user_data['user_col'] = user_col
        third_row_value = sheet.cell(3, user_col).value
        trimmed_value = third_row_value.split(' ', 1)[1] if ' ' in third_row_value else third_row_value
        
        await update.message.reply_text(f"Привет, {trimmed_value}!")

        keyboard = [
            [InlineKeyboardButton("Выбрать дату", callback_data='select_date'), 
             InlineKeyboardButton("Это не я", callback_data='not_me')],
##      
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Что вы хотите сделать?", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"Тег {user_tag} не найден в таблице.")
        await prompt_manual_tag(update)

async def prompt_manual_tag(message):
    keyboard = [
        [InlineKeyboardButton("Указать тег вручную", callback_data='manual_tag'),
         InlineKeyboardButton("Назад", callback_data='delete_message')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("Пожалуйста, укажите тег пользователя.", reply_markup=reply_markup)

async def handle_manual_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Введите ваш тег (например, @username):")
    context.user_data['state'] = WAITING_FOR_TAG

async def handle_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') == WAITING_FOR_TAG:
        user_tag = update.message.text.strip()
        context.user_data['name'] = user_tag

        all_users = sheet.row_values(1)
        if user_tag in all_users:
            user_col = all_users.index(user_tag) + 1
            context.user_data['user_col'] = user_col
            third_row_value = sheet.cell(3, user_col).value
            trimmed_value = third_row_value.split(' ', 1)[1] if ' ' in third_row_value else third_row_value
            await update.message.reply_text(f"Привет, {trimmed_value}!")

            keyboard = [
                [InlineKeyboardButton("Выбрать дату", callback_data='select_date'), 
                 InlineKeyboardButton("Это не я", callback_data='not_me')],
                [InlineKeyboardButton("Назад", callback_data='delete_message')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Что вы хотите сделать?", reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"Тег {user_tag} не найден в таблице.")
            await prompt_manual_tag(update)
    else:
        await update.message.reply_text("Сначала напишите /start.")

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await prompt_manual_tag(query.message)

async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Сегодня", callback_data='today'), 
         InlineKeyboardButton("Завтра", callback_data='tomorrow')],
        [InlineKeyboardButton("На неделю", callback_data='next_7_days')],
        [InlineKeyboardButton("Назад", callback_data='delete_message')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Выберите дату:", reply_markup=reply_markup)

async def handle_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selection = query.data
    
    if selection == 'today':
        await output_data(update, context, datetime.now().strftime('%d.%m'))
    elif selection == 'tomorrow':
        await output_data(update, context, (datetime.now() + timedelta(days=1)).strftime('%d.%m'))
    elif selection == 'next_7_days':
        await output_next_7_days(update, context)

async def output_next_7_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_tag = context.user_data.get('name')
    user_col = context.user_data.get('user_col')
    today = datetime.now()
    response = []

    for i in range(7):
        date_str = (today + timedelta(days=i)).strftime('%d.%m')
        try:
            date_column = sheet.col_values(1)
            date_row = date_column.index(date_str) + 1

            data = sheet.cell(date_row, user_col).value
            trimmed_data = data.split(' ', 1)[1] if ' ' in data else data
            
            if trimmed_data:
                response.append(f"{date_str}:    {trimmed_data}")
            else:
                response.append(f"{date_str}:    Нет данных.")

        except ValueError:
            response.append(f"{date_str}:    Дата не найдена в таблице.")
        except Exception as e:
            response.append(f"{date_str}:    Произошла ошибка: {str(e)}")
            print(f"Ошибка: {str(e)}")
      
    
    await update.callback_query.message.reply_text("\n".join(response))

      # Сообщение о возврате
    await update.callback_query.message.reply_text("Для возврата введите /start.")
    context.user_data['state'] = None

async def output_data(update: Update, context: ContextTypes.DEFAULT_TYPE, date_str: str):
    user_tag = context.user_data.get('name')
    user_col = context.user_data.get('user_col')

    try:
        date_column = sheet.col_values(1)
        date_row = date_column.index(date_str) + 1

        data = sheet.cell(date_row, user_col).value
        trimmed_data = data.split(' ', 1)[1] if ' ' in data else data
        
        if trimmed_data:
            await update.callback_query.message.reply_text(f"Данные для {user_tag} на {date_str}: \n{trimmed_data}")
        else:
            await update.callback_query.message.reply_text(f"Нет данных для {user_tag} на {date_str}.")

    except ValueError:
        await update.callback_query.message.reply_text("Дата не найдена в таблице.")
    except Exception as e:
        await update.callback_query.message.reply_text(f"Произошла ошибка: {str(e)}")
        print(f"Ошибка: {str(e)}")

        # Сообщение о возврате
    await update.callback_query.message.reply_text("Для возврата введите /start.")
    
    context.user_data['state'] = None

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') == WAITING_FOR_DATE:
        await handle_date(update, context)
    elif context.user_data.get('state') == WAITING_FOR_TAG:
        await handle_tag(update, context)

async def handle_delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.delete()

async def main():
    print("Бот запускается...")
    try:
        application = ApplicationBuilder().token("7719061201:AAHggc_TI55nk7fP4nMooIZFmskmsuE2uf0").build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(handle_confirmation, pattern='not_me'))
        application.add_handler(CallbackQueryHandler(select_date, pattern='select_date'))
        application.add_handler(CallbackQueryHandler(handle_date_selection, pattern='today|tomorrow|next_7_days'))
        application.add_handler(CallbackQueryHandler(handle_manual_tag, pattern='manual_tag'))
        application.add_handler(CallbackQueryHandler(handle_delete_message, pattern='delete_message'))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        print("Бот готов к работе.")
        await application.run_polling()
    except Exception as e:
        print(f"Ошибка при запуске бота: {str(e)}")

         

if __name__ == "__main__":
    asyncio.run(main())







  #  7719061201:AAHggc_TI55nk7fP4nMooIZFmskmsuE2uf0

