from fastapi import FastAPI, UploadFile, File, HTTPException, Query
import asyncio
import os
import aiofiles
import chromadb
from chromadb import Client
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader
import docx
import mammoth
from fastapi.responses import FileResponse
import hashlib
from transformers import pipeline

app = FastAPI()

try:
    chroma_client = chromadb.PersistentClient(path="db_persist")
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to connect to ChromaDB: {str(e)}")

embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cpu')

try:
    collection = chroma_client.get_or_create_collection(name="documents")
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to create/retrieve collection: {str(e)}")

qa_pipeline = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")

def generate_id(file_name, text):
    return hashlib.md5((file_name + text).encode()).hexdigest()

async def parse_pdf(file_path):
    reader = PdfReader(file_path)
    text = ''.join([page.extract_text() for page in reader.pages if page.extract_text()])
    return text

async def parse_docx(file_path):
    doc = docx.Document(file_path)
    text = '\n'.join([para.text for para in doc.paragraphs])
    return text

async def parse_doc(file_path):
    with open(file_path, "rb") as doc_file:
        result = await asyncio.to_thread(mammoth.convert_to_plain_text, doc_file)
    return result.value

async def parse_txt(file_path):
    async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
        return await f.read()

async def get_embeddings(texts):
    return await asyncio.to_thread(embedding_model.encode, texts, show_progress_bar=False)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the FastAPI RAG Server!"}

@app.get("/favicon.png", include_in_schema=False)
async def favicon():
    return FileResponse("D:/professionalProjects/rag_project/icon/favicon.png")

@app.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    os.makedirs("temp_files", exist_ok=True)
    file_location = f"temp_files/{file.filename}"
    
    try:
        async with aiofiles.open(file_location, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
    
        if file.filename.endswith('.pdf'):
            text = await parse_pdf(file_location)
        elif file.filename.endswith('.docx'):
            text = await parse_docx(file_location)
        elif file.filename.endswith('.doc'):
            text = await parse_doc(file_location)
        elif file.filename.endswith('.txt'):
            text = await parse_txt(file_location)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        embeddings = await get_embeddings([text])
        doc_id = generate_id(file.filename, text)
        
        collection.add(
            documents=[text],
            embeddings=embeddings,
            ids=[doc_id]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during ingestion: {str(e)}")
    finally:
        os.remove(file_location)
    
    return {"status": "Document ingested successfully"}

@app.get("/query_doc")
async def query_document(query: str = Query(...), top_k: int = 5):
    try:
        query_embedding = await get_embeddings([query])
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=['documents', 'distances']
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during querying: {str(e)}")
    
@app.get("/query")
async def query_document(query: str = Query(...), top_k: int = 1):
    query_embedding = await get_embeddings([query])
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=['documents', 'distances']
    )
    document = results["documents"][0][0] 
    answer = qa_pipeline(question=query, context=document)
    return {
        "query": query,
        "answer": answer['answer'],
        "confidence": answer['score']
    }

@app.get("/check-health")
async def check_health():
    return {"message": "API Healthy!"}

@app.get("/db-health")
async def check_db_health():
    try:
        document_count = collection.count()
        return {"status": "Database is connected", "document_count": document_count}
    except Exception as e:
        return {"status": "Database connection failed", "error": str(e)}
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
