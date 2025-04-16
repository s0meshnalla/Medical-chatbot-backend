import requests
from datetime import datetime
from .vector_store import get_llm

def symptom_checker(symptoms: str) -> dict:
    """Check symptoms using Wikipedia API and LLM for analysis"""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query", 
        "format": "json", 
        "titles": symptoms, 
        "prop": "extracts", 
        "exintro": True, 
        "explaintext": True
    }
    
    response = requests.get(url, params=params).json()
    info = next(iter(response.get("query", {}).get("pages", {}).values())).get("extract", "No information found.")
    
    llm = get_llm()
    prompt = f"""
    Symptoms: {symptoms}
    Medical Information: {info}
    
    As a medical assistant, please provide:
    1. Possible causes of these symptoms
    2. Severity assessment (mild, moderate, severe)
    3. When to seek professional care
    4. Home care recommendations

    Format your response in a clear, helpful way.
    """
    
    analysis = llm(prompt)
    
    return {
        "symptoms": symptoms,
        "possible_causes": analysis,
        "timestamp": datetime.now().isoformat()
    }
