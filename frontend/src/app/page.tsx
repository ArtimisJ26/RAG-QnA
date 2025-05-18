'use client';

import { useState } from 'react';
import FileUpload from './components/FileUpload';
import QuestionInput from './components/QuestionInput';
import AnswerDisplay from './components/AnswerDisplay';
import DocumentList from './components/DocumentList';

interface Document {
  name: string;
  size: number;
  uploadedAt: string;
}

export default function Home() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<{ text: string; document: string; }[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleUploadSuccess = (uploadedFiles: Document[]) => {
    setDocuments(prev => [...prev, ...uploadedFiles]);
  };

  const handleAskQuestion = async (question: string) => {
    setIsLoading(true);
    setAnswer(''); // Clear previous answer
    setSources([]); // Clear previous sources
    
    try {
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          query: question
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to get answer (${response.status})`);
      }

      const data = await response.json();
      setAnswer(data.answer || 'No answer was generated.');
      setSources(data.sources?.map((source: string) => ({
        text: '', // The backend doesn't send text content
        document: source // The backend sends source strings directly
      })) || []);
    } catch (error) {
      console.error('Error asking question:', error);
      setAnswer('Sorry, there was an error processing your question. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteDocument = async (doc: Document) => {
    try {
      const response = await fetch(`/api/documents/${encodeURIComponent(doc.name)}/`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to delete document');
      }

      setDocuments(documents.filter((d) => d.name !== doc.name));
    } catch (error) {
      console.error('Error deleting document:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
      <main className="container mx-auto px-4 py-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Document Q&A Assistant
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300">
            Upload your documents and get intelligent answers to your questions
          </p>
        </div>
        
        <div className="max-w-4xl mx-auto space-y-8">
          <FileUpload onUploadSuccess={handleUploadSuccess} />
          
          {documents.length > 0 && (
            <DocumentList
              documents={documents}
              onDelete={handleDeleteDocument}
            />
          )}
          
          <QuestionInput
            onAskQuestion={handleAskQuestion}
            isLoading={isLoading}
          />
          
          <AnswerDisplay
            answer={answer}
            sources={sources}
          />
        </div>
      </main>
    </div>
  );
}
