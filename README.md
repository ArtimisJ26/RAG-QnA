# RAG-QnA

A Retrieval-Augmented Generation (RAG) system for question answering on PDF documents using Google's Gemini API.

## Features

- PDF document ingestion and processing
- Vector database storage using ChromaDB
- Semantic search for relevant document chunks
- AI-powered question answering with Google Gemini

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Google API key for Gemini

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ArtimisJ26/RAG-QnA.git
   cd RAG-QnA
   ```

2. **Create a virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   - Create a `.env` file in the project root
   - Add your Google API key:
     ```
     GOOGLE_API_KEY=your_google_api_key_here
     ```

5. **Add PDF documents**
   - Create a `pdfs` directory if it doesn't exist
   - Place your PDF files in the `pdfs` directory

### Usage

Run the main script:
```bash
python RAG_backend.py
```

The system will:
1. Load and process all PDFs in the `pdfs` directory
2. Create embeddings and store them in a vector database
3. Prompt you to enter a question
4. Retrieve relevant document chunks
5. Generate an AI response based on the retrieved information

## Notes

- If no PDFs are found, the system will use sample documents
- Make sure your Google API key has access to the Gemini API
