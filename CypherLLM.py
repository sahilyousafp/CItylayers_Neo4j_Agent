from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts import PromptTemplate

# Database connection
def connect():
    return Neo4jGraph(
        url="neo4j+s://02f54a39.databases.neo4j.io",
        username="neo4j",
        password="U9WSV67C8evx4nWCk48n3M0o7dX79T2XQ3cU1OJfP9c"
    )

# Initialize AI model
def init_model():
    return ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=0,
        convert_system_message_to_human=True
    )

# Format results if AI can't answer
def format_results(context):
    if not context:
        return "**No results found.**"
    
    total_count = len(context)
    output = [f"### 📍 Found {total_count} locations\n"]
    
    # Create a markdown table
    output.append("| # | Location | Place ID | Coordinates |")
    output.append("|---|----------|----------|-------------|")
    
    for i, record in enumerate(context, 1):
        if 'p' in record:
            place = record['p']
            location = place.get('location', 'Unknown')
            pid = place.get('place_id', 'N/A')
            lat = place.get('latitude', 'N/A')
            lon = place.get('longitude', 'N/A')
            
            # Format coordinates
            if lat != 'N/A' and lon != 'N/A':
                coords = f"{lat:.6f}, {lon:.6f}"
            else:
                coords = "N/A"
            
            output.append(f"| {i} | **{location}** | `{pid}` | {coords} |")
    
    return "\n".join(output)

# Main chat loop
def chat():
    print("Neo4j Chat Assistant")
    print("Ask questions about places in the database. Type 'quit' to exit.\n")
    
    graph = connect()
    llm = init_model()
    
    # Conversation history
    chat_history = []
    
    while True:
        question = input("You: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("Thank You!")
            break
        
        if not question:
            continue
        
        try:
            # Add conversation context to the question
            if chat_history:
                context_text = "\n".join([f"Previous Q: {q}\nPrevious A: {a}" for q, a in chat_history[-2:]])
                enhanced_question = f"{context_text}\n\nCurrent question: {question}"
            else:
                enhanced_question = question
            
            # Create chain with enhanced QA prompt
            qa_template = """You are a helpful assistant answering questions about places in a database.

Question: {question}

Database results:
{context}

IMPORTANT: Provide your answer in proper Markdown format that will be rendered as HTML.
Use standard markdown syntax:
- Use ### for headers
- Use **text** for bold
- Use - or * for bullet lists
- Use tables with | for structured data
- Use `text` for code/IDs
- Use proper paragraphs

Format your response with clear structure and emphasis on important information.

Answer:"""
            
            qa_prompt = PromptTemplate(
                input_variables=["question", "context"],
                template=qa_template
            )
            
            chain = GraphCypherQAChain.from_llm(
                llm=llm,
                graph=graph,
                qa_prompt=qa_prompt,
                allow_dangerous_requests=True,
                verbose=True,
                return_intermediate_steps=True
            )
            
            result = chain.invoke({"query": enhanced_question})
            answer = result['result']
            
            # If AI doesn't know, format manually
            if "don't know" in answer.lower():
                if 'intermediate_steps' in result:
                    context = result['intermediate_steps'][0].get('context', [])
                    answer = format_results(context)
            
            print(f"\nAssistant: {answer}\n")
            
            # Save to history (store original question, not enhanced)
            chat_history.append((question, answer))
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")

if __name__ == "__main__":
    chat()