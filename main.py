import os
import uvicorn
import smtplib
from typing import Dict
from email.message import EmailMessage

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_groq import ChatGroq
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

load_dotenv()

app = FastAPI(title="HCLA Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FILE_PATH = "Annual-Report-2024-25.pdf"
DB_NAME = "hlc_vector_db"
pending_emails: Dict[str, dict] = {}

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0.2
)

def process_pdf():
    loader = PyMuPDFLoader(FILE_PATH)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    chunks = splitter.split_documents(documents)
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(DB_NAME)

@app.on_event("startup")
def startup_event():
    if not os.path.exists(DB_NAME):
        process_pdf()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

@tool
def draft_hr_email(topic: str) -> dict:
    """Create an HR email draft. Does NOT send email."""
    subject = f"Employee Request: {topic.capitalize()}"
    body = f"Dear HR Team,\n\nI hope this email finds you well.\n\nI am writing to inform/request regarding the following matter:\n\n{topic}\n\nKindly let me know if any additional information is required.\n\nThank you for your support.\nBest regards,\nEmployee"
    return {
        "to": os.getenv("HR_EMAIL"),
        "subject": subject,
        "body": body
    }

@tool
def send_hr_email(to: str, subject: str, body: str) -> str:
    """Send email to HR (called ONLY after confirmation)."""
    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_EMAIL")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("SMTP_EMAIL"), os.getenv("SMTP_PASSWORD"))
        server.send_message(msg)
    return "Email successfully sent to HR."

tools = [draft_hr_email, send_hr_email]
llm_with_tools = llm.bind_tools(tools)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an HLC Bank assistant.\n- Use RAG for factual answers\n- If employee wants to contact HR, create an email draft\n- NEVER send an email without explicit user confirmation\n- Always ask for confirmation before sending\n\nCONTEXT:\n{context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])

class QueryRequest(BaseModel):
    session_id: str
    user_query: str

@app.post("/query")
async def ask_hlc(req: QueryRequest):
    session_id = req.session_id
    user_query = req.user_query.strip().lower()
    
    if user_query in ["yes", "send", "confirm", "yes send it"]:
        if session_id not in pending_emails:
            return {"answer": "No pending email to send."}
        draft = pending_emails.pop(session_id)
        result = send_hr_email.invoke(draft)
        return {"answer": result}

    db = FAISS.load_local(DB_NAME, embeddings, allow_dangerous_deserialization=True)
    docs = db.similarity_search(user_query, k=5)
    context = "\n\n".join(doc.page_content for doc in docs)
    chain = prompt | llm_with_tools
    
    result = chain.invoke({
        "context": context,
        "question": user_query,
        "chat_history": []
    })

    if result.tool_calls:
        tool_call = result.tool_calls[0]
        if tool_call["name"] == "draft_hr_email":
            draft = draft_hr_email.invoke(tool_call["args"])
            pending_emails[session_id] = draft
            return {
                "draft_email": draft,
                "confirmation_required": True,
                "message": "Do you want me to send this email? (Yes / No)"
            }

    return {"answer": result.content}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)