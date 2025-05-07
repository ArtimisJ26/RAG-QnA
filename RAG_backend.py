# Import necessary libraries
from google import genai  # Google's Generative AI library
from google.genai import types  # Types for Gemini API
from IPython.display import Markdown  # For displaying formatted text in notebooks
import chromadb  # Vector database for storing embeddings
from chromadb import Documents, EmbeddingFunction, Embeddings  # ChromaDB types
from google.api_core import retry  # For handling API rate limits
import os
import glob  # For finding files matching a pattern
from dotenv import load_dotenv

# Load API key from environment file
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API key for accessing Google's Generative AI services
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Try to import PyPDF2, but provide a fallback if it's not available
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    print("PyPDF2 not found. PDF functionality will be limited.")
    print("To install: pip install PyPDF2")
    PYPDF2_AVAILABLE = False

# Print the version of the Google Generative AI library
print(genai.__version__)

# Initialize the Gemini client with the API key
client = genai.Client(api_key=GOOGLE_API_KEY)

# Function to load text from PDF files
def load_pdfs_from_directory(directory_path):
    """
    Load and extract text from all PDF files in a directory.
    Returns a list of document chunks and their source information.
    """
    documents = []
    document_sources = []
    
    # If PyPDF2 is not available, return empty lists
    if not PYPDF2_AVAILABLE:
        print("Cannot load PDFs because PyPDF2 is not installed.")
        return documents, document_sources
    
    # Find all PDF files in the directory
    pdf_files = glob.glob(os.path.join(directory_path, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {directory_path}")
        return documents, document_sources
    
    for pdf_path in pdf_files:
        try:
            # Open the PDF file
            with open(pdf_path, 'rb') as file:
                try:
                    # Create a PDF reader object with strict=False to be more lenient with errors
                    pdf_reader = PyPDF2.PdfReader(file, strict=False)
                    
                    # Get the filename for source tracking
                    filename = os.path.basename(pdf_path)
                    
                    # Extract text from each page
                    for page_num, page in enumerate(pdf_reader.pages):
                        try:
                            text = page.extract_text()
                            
                            # Skip empty pages
                            if not text or text.isspace():
                                continue
                            
                            # Add the text and source information
                            documents.append(text)
                            document_sources.append(f"{filename} (Page {page_num+1})")
                            
                            print(f"Loaded {filename} - Page {page_num+1}")
                        except Exception as page_error:
                            print(f"Error extracting text from {filename} page {page_num+1}: {page_error}")
                            # Continue to the next page
                            continue
                except PyPDF2.errors.PdfReadError as pdf_error:
                    print(f"PDF read error in {pdf_path}: {pdf_error}")
                    print("This PDF may be corrupted or password-protected.")
                    # Continue to the next file
                    continue
        except Exception as e:
            print(f"Error opening {pdf_path}: {e}")
    
    print(f"Successfully loaded {len(documents)} document chunks from {len(set(document_sources))} PDF files")
    return documents, document_sources

# Define a helper function to retry API calls when rate limits are hit
# Returns True if the error is retriable (429=rate limit, 503=service unavailable)
is_retriable = lambda e: (isinstance(e, genai.errors.APIError) and e.code in {429, 503})

# Custom embedding function class that uses Gemini to create embeddings
class GeminiEmbeddingFunction(EmbeddingFunction):
    # Flag to switch between document embedding and query embedding modes
    # Different embedding types are optimal for documents vs. queries
    document_mode = True

    # The __call__ method makes the class callable like a function
    @retry.Retry(predicate=is_retriable)  # Automatically retry on rate limits
    def __call__(self, input: Documents) -> Embeddings:
        # Select the appropriate embedding task based on mode
        if self.document_mode:
            embedding_task = "retrieval_document"  # For indexing documents
        else:
            embedding_task = "retrieval_query"  # For processing queries

        # Call Gemini API to generate embeddings
        response = client.models.embed_content(
            model="models/text-embedding-004",  # Gemini's embedding model
            contents=input,  # Text to embed
            config=types.EmbedContentConfig(
                task_type=embedding_task,  # Specify document or query embedding
            ),
        )
        # Extract and return the embedding vectors
        return [e.values for e in response.embeddings]

# Directory containing PDF files - change this to your PDF directory
pdf_directory = "./pdfs"  # Create this directory and add your PDFs here

# Load documents from PDFs
documents, document_sources = load_pdfs_from_directory(pdf_directory)

# If no PDFs were found, use sample documents as fallback
if not documents:
    print("No PDF documents found. Using sample documents instead.")
    # Sample documents about a fictional "Googlecar"
    documents = [
        "Operating the Climate Control System  Your Googlecar has a climate control system that allows you to adjust the temperature and airflow in the car. To operate the climate control system, use the buttons and knobs located on the center console.  Temperature: The temperature knob controls the temperature inside the car. Turn the knob clockwise to increase the temperature or counterclockwise to decrease the temperature. Airflow: The airflow knob controls the amount of airflow inside the car. Turn the knob clockwise to increase the airflow or counterclockwise to decrease the airflow. Fan speed: The fan speed knob controls the speed of the fan. Turn the knob clockwise to increase the fan speed or counterclockwise to decrease the fan speed. Mode: The mode button allows you to select the desired mode. The available modes are: Auto: The car will automatically adjust the temperature and airflow to maintain a comfortable level. Cool: The car will blow cool air into the car. Heat: The car will blow warm air into the car. Defrost: The car will blow warm air onto the windshield to defrost it.",
        'Your Googlecar has a large touchscreen display that provides access to a variety of features, including navigation, entertainment, and climate control. To use the touchscreen display, simply touch the desired icon.  For example, you can touch the "Navigation" icon to get directions to your destination or touch the "Music" icon to play your favorite songs.',
        "Shifting Gears Your Googlecar has an automatic transmission. To shift gears, simply move the shift lever to the desired position.  Park: This position is used when you are parked. The wheels are locked and the car cannot move. Reverse: This position is used to back up. Neutral: This position is used when you are stopped at a light or in traffic. The car is not in gear and will not move unless you press the gas pedal. Drive: This position is used to drive forward. Low: This position is used for driving in snow or other slippery conditions."
    ]
    document_sources = ["Sample Document 1", "Sample Document 2", "Sample Document 3"]

# Print summary of loaded documents
print(f"Loaded {len(documents)} document chunks")

# Name for the ChromaDB collection
DB_NAME = "document_db"

# Initialize the embedding function in document mode (for adding documents)
embed_fn = GeminiEmbeddingFunction()
embed_fn.document_mode = True

# Create a ChromaDB client (in-memory database)
chroma_client = chromadb.Client()
# Create a collection (or get it if it already exists)
db = chroma_client.get_or_create_collection(name=DB_NAME, embedding_function=embed_fn)

# Add the documents to the collection with sequential IDs and source metadata
# ChromaDB will use our embedding function to generate embeddings
db.add(
    documents=documents, 
    ids=[f"doc_{i}" for i in range(len(documents))],
    metadatas=[{"source": source} for source in document_sources]
)

# Print the number of documents in the collection
print(f"Documents in database: {db.count()}")

# Switch the embedding function to query mode for searching
embed_fn.document_mode = False

# Get user query
query = input("Enter your question: ")
if not query:
    # Default query if none provided
    query = "How do you use the touchscreen to play music?"
    print(f"Using default query: {query}")

# Search the database for documents relevant to the query
# Returns the most similar documents based on embedding similarity
n_results = min(3, len(documents))  # Get up to 3 results, but not more than we have documents
result = db.query(
    query_texts=[query], 
    n_results=n_results,
    include=["documents", "metadatas", "distances"]
)

# Extract the lists of retrieved documents and their sources
all_passages = result["documents"][0]
all_sources = [item["source"] for item in result["metadatas"][0]]
all_distances = result["distances"][0]

# Display the retrieved passages with their sources and similarity scores
print("\nRetrieved relevant documents:")
for i, (passage, source, distance) in enumerate(zip(all_passages, all_sources, all_distances)):
    print(f"\nDocument {i+1} (Source: {source}, Similarity: {1-distance:.4f}):")
    print(f"{passage[:150]}..." if len(passage) > 150 else passage)

# Prepare the query for inclusion in the prompt by removing newlines
query_oneline = query.replace("\n", " ")

# Create a prompt for the LLM that includes instructions and the query
# This prompt template guides the model on how to respond
prompt = f"""You are a helpful and informative bot that answers questions using text from the reference passages included below. 
Be sure to respond in a complete sentence, being comprehensive, including all relevant background information. 
However, you are talking to a non-technical audience, so be sure to break down complicated concepts and 
strike a friendly and conversational tone. If the passages are irrelevant to the answer, you may say so.

QUESTION: {query_oneline}
"""

# Add each retrieved passage to the prompt with its source
for i, (passage, source) in enumerate(zip(all_passages, all_sources)):
    # Remove newlines from the passage for cleaner formatting
    passage_oneline = passage.replace("\n", " ")
    prompt += f"PASSAGE {i+1} ({source}): {passage_oneline}\n\n"

# Print the complete prompt for debugging/transparency
print("\nPrompt sent to Gemini:")
print(prompt)

# Generate a response using Gemini with the constructed prompt
answer = client.models.generate_content(
    model="gemini-2.0-flash",  # Using Gemini's fast model
    contents=prompt)  # The prompt with query and context

# Print the generated answer
print("\nGemini's Response:")
print(answer.text)
