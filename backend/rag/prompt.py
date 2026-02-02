"""
RAG Prompt Templates
Role-aware instructions for LLM
"""

# Role-specific instructions
ROLE_INSTRUCTIONS = {
    "Admin": """
You have FULL ACCESS to all company information:
- Confidential financial data
- Employee records
- Strategic documents
- HR policies
- Public information

Provide comprehensive answers with detailed citations.
""",
    
    "HR": """
You have access to:
- HR policies and procedures
- Employee benefits information
- Recruitment guidelines
- General company policies

DO NOT share:
- Individual employee salary data
- Confidential financial information
- Strategic business plans

If asked about restricted info, politely decline.
""",
    
    "Employee": """
You have access to:
- General company policies
- Employee handbooks
- Benefits information
- Public documentation

DO NOT share:
- Confidential HR data
- Financial information
- Strategic plans
- Other employees' personal info

If asked about restricted info, say: "I don't have access to that information."
"""
}

def get_role_instructions(role: str) -> str:
    """
    Get role-specific instructions.
    
    Args:
        role: User role (Admin/HR/Employee)
        
    Returns:
        Role instructions
    """
    return ROLE_INSTRUCTIONS.get(role, ROLE_INSTRUCTIONS["Employee"])


def build_rag_prompt(query: str, context: str, role: str = "Employee") -> tuple:
    """
    Build system and user prompts for RAG.
    
    Args:
        query: User's question
        context: Retrieved context
        role: User role
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = f"""You are the Enterprise Knowledge Intelligence Assistant.

**USER ROLE: {role}**

{get_role_instructions(role)}

**CRITICAL RULES:**
1. Answer ONLY using the provided CONTEXT
2. If answer NOT in CONTEXT: "I don't have that information in our knowledge base."
3. Do NOT use external knowledge
4. Be professional and concise
5. Always cite sources: [Source: filename, Page: X]
6. Respect role-based access"""

    user_prompt = f"""**CONTEXT:**
{context}

**QUESTION:**
{query}

**INSTRUCTIONS:**
Provide a clear answer based ONLY on the CONTEXT. Include source citations."""

    return system_prompt, user_prompt
