from datetime import datetime
from .vector_store import get_vector_store, get_llm, memory, embeddings, supabase
from .symptom_checker import symptom_checker
from .clinic_locator import clinic_locator

def store_conversation(user_id: str, query: str, response: dict):
    """Store conversation in vector database for future context"""
    document = f"User: {query}\nResponse: {str(response)}"
    metadata = {
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "query_type": detect_query_type(query)
    }
    
    # Create embedding
    embedding = embeddings.embed_documents([document])[0]
    
    # Store in Supabase
    supabase.table("medical_conversations").insert({
        "content": document,
        "metadata": metadata,
        "embedding": embedding
    }).execute()
    
    print(f"Stored conversation for user {user_id}")

def retrieve_context(user_id: str, query: str) -> list:
    """Retrieve relevant past conversations from vector store"""
    print(f"Retrieving context for user_id: {user_id}, query: {query}")
    
    vector_store = get_vector_store()
    results = vector_store.similarity_search(
        query, 
        k=3,
        filter={"user_id": user_id}
    )
    
    print(f"Found {len(results)} relevant past conversations")
    return [doc.page_content for doc in results]

def detect_query_type(query: str) -> str:
    """Detect type of query based on keywords"""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["symptom", "feel", "pain", "hurt", "sick", "ache"]):
        return "symptom"
    elif any(word in query_lower for word in ["clinic", "hospital", "doctor", "facility", "nearby"]):
        return "location"
    else:
        return "general"

def chatbot_response(user_id: str, query: str, user_location: str = None) -> dict:
    """Process user query and generate appropriate response"""
    # Get past context
    past_context = retrieve_context(user_id, query)
    context_str = "\n".join(past_context) if past_context else "No prior context."
    
    # Add user message to memory
    memory.add_user_message(query)
    
    # Determine query type and process accordingly
    query_type = detect_query_type(query)
    llm = get_llm()
    
    if query_type == "symptom":
        # Use symptom checker for symptom-related queries
        result = symptom_checker(query)
        response = result["possible_causes"]
        
    elif query_type == "location":
        # Use clinic locator for location-related queries
        location = user_location if user_location else "Unknown location"
        if location == "Unknown location":
            response = "Please provide your location so I can find nearby medical facilities."
            result = {"response": response}
        else:
            clinics = clinic_locator(location)
            
            if clinics and "error" in clinics[0]:
                response = f"Error finding clinics: {clinics[0]['error']}"
                result = {"response": response, "clinics": []}
            else:
                # Format clinic information for display
                response = "I found these medical facilities near you:"
                result = {"response": response, "clinics": clinics}
                
    else:
        # General medical question
        prompt = f"""
        Previous conversation context:
        {context_str}
        
        Current query: {query}
        
        Respond as a helpful medical assistant providing accurate information.
        Be empathetic but clear about medical facts.
        Recommend seeking professional medical advice when appropriate.
        
        Response:
        """
        
        response = llm(prompt)
        result = {"response": response}
    
    # Add AI response to memory
    memory.add_ai_message(response)
    
    # Store conversation
    store_conversation(user_id, query, result)
    
    return {
        "response": response,
        "result": result,
        "query_type": query_type
    }
