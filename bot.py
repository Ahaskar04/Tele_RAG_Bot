import os
import logging
from typing import Final

import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ----------------- Telegram Bot Credentials ----------------- #
TOKEN: Final = "7634853763:AAHi4v0QsMAqW-tIQ5HSeGlSxAjIDA_nLck"
BOT_USERNAME: Final = "@DaxAsiaBot"  # (Optional)

# ----------------- OpenAI API Key ----------------- #
# Retrieve the API key from the environment variable
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")
openai.api_key = openai_api_key

# ----------------- LangChain RAG Setup ----------------- #
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOpenAI


# 1. Load the PDF file
pdf_path = "info.pdf"  # Ensure info.pdf is in the same directory as this script
loader = PyPDFLoader(pdf_path)
docs = loader.load()

# 2. Split the PDF into manageable chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
split_docs = text_splitter.split_documents(docs)

# 3. Create embeddings and build a FAISS vector store from the documents
embeddings = OpenAIEmbeddings()
vectorstore = FAISS.from_documents(split_docs, embeddings)

# 4. Set up a retriever using the vector store and build the RetrievalQA chain
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(temperature=0),
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=False,
)

# ----------------- Telegram Bot Handlers ----------------- #
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text("Hello! Ask me any question about info.pdf!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "I am a RAG-based bot using LangChain. "
        "Ask me any question related to info.pdf, and I'll do my best to help!"
    )
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user messages."""
    user_message = update.message.text
    try:
        # Use the RAG system to generate an answer from the PDF
        answer = qa_chain.run(user_message)
        await update.message.reply_text(answer)
    except Exception as e:
        logging.exception("Error during qa_chain run: %s", e)
        await update.message.reply_text("Sorry, an error occurred while processing your request.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logging.error(msg="Exception while handling an update:", exc_info=context.error)

# ----------------- Main: Run the Telegram Bot ----------------- #
def main() -> None:
    """Start the Telegram bot."""
    application = ApplicationBuilder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Add message handler for text messages (ignoring commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add error handler
    application.add_error_handler(error_handler)

    print("Bot is running... Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
