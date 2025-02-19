import structlog
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from agent import run_agent
from config import config
import telegram

log = structlog.stdlib.get_logger()


async def say_hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.info("Saying hello", update=update)
    if not update.message:
        log.error("Update message is None")
        return

    if user := update.message.from_user:
        name = user.first_name or user.last_name or user.username
    name = name or "stranger"

    await update.message.reply_text(f"Hello! {name}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error(
        "Encountered Telegram error",
        update=str(update),
        error=str(context.error),
        chat_id=update.effective_chat.id if update and update.effective_chat else None,
        user_id=update.effective_user.id if update and update.effective_user else None,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.info("Handling message", update=update)

    if not update.message or not update.message.text:
        log.error("Update message or text is None")
        return

    try:
        response = await run_agent(update.message.text)
        try:
            await update.message.reply_text(response, parse_mode="HTML")
        except telegram.error.BadRequest as e:
            # Fallback to plain text if markdown parsing fails
            await update.message.reply_text(
                f"Error with markdown formatting. Sending as plain text:\n\n{response}"
            )
            log.exception("Error with Telegram response", response=response, error=e)

    except Exception as e:
        log.exception("Error generating response", error=e)
        await update.message.reply_text(
            "Sorry, I encountered an error processing your request."
        )


def main() -> None:
    log.info("Telegram bot starting")
    application = Application.builder().token(config.telegram_bot_token).build()

    application.add_handler(CommandHandler("hello", say_hello))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_error_handler(error_handler)  # pyright:ignore[reportArgumentType]

    application.run_polling()


if __name__ == "__main__":
    main()
