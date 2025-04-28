import os
from datetime import datetime
import google.generativeai as genai
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase import create_client
from langchain.llms.base import LLM
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv


load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jbzkxnclqwsjbkcaczkd.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impiemt4bmNscXdzamJrY2FjemtkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ3MDIwMzQsImV4cCI6MjA2MDI3ODAzNH0.xZR7af9CAQLYBfckVUFxSnhDBo-rvk3qSLl_OB8JKOo")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDfCY7ZD-5sTiBTW_xb7WHKzzCxmtJJI14")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
genai.configure(api_key=GEMINI_API_KEY)

class GeminiLLM(LLM):
    def _call(self, prompt: str, stop: list = None) -> str:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    
    @property
    def _llm_type(self) -> str:
        return "gemini"


class CustomConversationBufferMemory:
    def __init__(self):
        self.chat_history = InMemoryChatMessageHistory()
    
    def add_user_message(self, message: str):
        self.chat_history.add_message(HumanMessage(content=message))
    
    def add_ai_message(self, message: str):
        self.chat_history.add_message(AIMessage(content=message))
    
    def get_messages(self):
        return self.chat_history.messages
    
    def clear(self):
        self.chat_history.clear()


memory = CustomConversationBufferMemory()
llm_instance = None

def get_llm():
    global llm_instance
    if llm_instance is None:
        llm_instance = GeminiLLM()
    return llm_instance


def get_vector_store():
    verify_supabase_schema()
    return SupabaseVectorStore(
        client=supabase, 
        embedding=embeddings, 
        table_name="medical_conversations", 
        query_name="match_documents"
    )


def verify_supabase_schema():
    try:

        supabase.table("medical_conversations").select("id").limit(1).execute()
        print("Supabase schema verified.")
        return True
    except Exception as e:
        print(f"Schema error: {e}")
        print("Creating schema...")
        
        create_schema_sql = """
        CREATE EXTENSION IF NOT EXISTS vector;
        
        CREATE TABLE IF NOT EXISTS medical_conversations (
            id BIGSERIAL PRIMARY KEY,
            content TEXT,
            metadata JSONB,
            embedding VECTOR(384)
        );
        
        CREATE OR REPLACE FUNCTION match_documents (
            query_embedding VECTOR(384),
            filter JSONB DEFAULT '{}'
        ) RETURNS TABLE (
            id BIGINT,
            content TEXT,
            metadata JSONB,
            similarity FLOAT
        ) LANGUAGE plpgsql AS $$
        BEGIN
            RETURN QUERY
            SELECT
                id,
                content,
                metadata,
                1 - (embedding <=> query_embedding) AS similarity
            FROM
                medical_conversations
            WHERE
                metadata @> filter
            ORDER BY
                embedding <=> query_embedding
            LIMIT 5;
        END;
        $$;
        """
        
        try:

            response = supabase.execute_sql(create_schema_sql)
            print("Schema created successfully")
            return True
        except Exception as schema_e:
            print(f"Failed to create schema: {schema_e}")
            return False 
