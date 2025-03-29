import os
import logging
from typing import Final

import openai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------- LangChain and RAG Imports ----------------- #
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.agents import Tool, AgentType, initialize_agent
from langchain.prompts import PromptTemplate


# ----------------- Telegram Bot Credentials ----------------- #
TOKEN: Final = "7684522067:AAHk5vbK7cCkjCLICSrwNikOrKqjk79Psr4"
BOT_USERNAME: Final = "@hcdksbfckwsdcbot"  # (Optional) Not strictly required for basic usage

# ----------------- OpenAI API Key ----------------- #
# For best practice, set this via an environment variable instead:
#   export OPENAI_API_KEY='sk-...'
# Here, for demonstration, we'll directly set it:
openai.api_key = " __  "
# ----------------- Global Setup: RAG / Agent ----------------- #

# 1) Load your PDF
pdf_path = "info.pdf"  # Make sure this file is in the same directory
loader = PyPDFLoader(pdf_path)
docs = loader.load()

# 2) Split text into manageable chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100
)
split_docs = text_splitter.split_documents(docs)

# 3) Create embeddings and store in a Vector DB (FAISS here)
embeddings = OpenAIEmbeddings()  # Uses text-embedding-ada-002 by default
vectorstore = FAISS.from_documents(split_docs, embeddings)

# 4) Build a RetrievalQA chain
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(temperature=0),  # or ChatOpenAI(model_name="gpt-3.5-turbo")
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=False,
)

# 5) Define a tool that the agent can use to query the PDF’s content
tool = Tool(
    name="PDF-Info-Tool",
    func=qa_chain.run,
    description=(
        "Useful for answering questions about the content of info.pdf. "
        "Input should be a fully formed question."
    ),
)

# 6) Create a prompt template for the agent if desired (optional)
custom_prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad"],
    template=(
        "You are a helpful assistant. "
        "You have access to a single tool for answering PDF-related questions.\n\n"
        "Question: {input}\n"
        "Thought: {agent_scratchpad}\n"
        "Provide a concise answer below.\n"
    ),
)

# 7) Initialize an agent that can use the tool
agent = initialize_agent(
    tools=[tool],
    llm=ChatOpenAI(temperature=0),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False,
    prompt=custom_prompt,
)


# ----------------- Telegram Handlers ----------------- #

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(
        "Hello! Thanks for chatting with me. Ask me anything about info.pdf!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "I’m a RAG-based bot using LangChain. "
        "Just ask any question related to info.pdf, and I’ll do my best to help!"
    )
    await update.message.reply_text(help_text)

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /custom command."""
    await update.message.reply_text("This is a custom command. Ask away!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user messages."""
    user_message = update.message.text

    # Pass the user message to the agent
    try:
        answer = agent.run(user_message)
        await update.message.reply_text(answer)
    except Exception as e:
        logging.exception("Error during agent run: %s", e)
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your request."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logging.error(msg="Exception while handling an update:", exc_info=context.error)


# ----------------- Main: Run the Bot ----------------- #

def main() -> None:
    """Start the Telegram bot."""
    # Set up application
    application = ApplicationBuilder().token(TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("custom", custom_command))

    # Messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Errors
    application.add_error_handler(error_handler)

    # Run bot
    print("Bot is running... Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
