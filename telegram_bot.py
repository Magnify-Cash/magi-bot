from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr
import structlog
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from config import config

log = structlog.stdlib.get_logger()

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=3,
    api_key=SecretStr(config.openai_api_key),
)


async def say_hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.info("Saying hello", update=update, context=context)
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
    log.info("Handling message", update=update, context=context)

    if not update.message or not update.message.text:
        log.error("Update message or text is None")
        return

    try:
        response = llm.invoke(update.message.text)
        assert isinstance(response.content, str)
        await update.message.reply_text(response.content)
    except Exception as e:
        log.error("Error generating response", error=str(e))
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
