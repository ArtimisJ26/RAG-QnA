'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import FileUpload from './components/FileUpload';
import QuestionInput from './components/QuestionInput';
import DocumentList from './components/DocumentList';

interface Document {
  name: string;
  size: number;
  uploadedAt: string;
}

interface Message {
  type: 'user' | 'assistant';
  content: string;
  sources?: { text: string; document: string; }[];
  timestamp: string;
}

export default function Home() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleUploadSuccess = (uploadedFiles: Document[]) => {
    setDocuments(prev => [...prev, ...uploadedFiles]);
  };

  const handleAskQuestion = async (question: string) => {
    setIsLoading(true);
    
    const userMessage: Message = {
      type: 'user',
      content: question,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);
    
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
      
      const assistantMessage: Message = {
        type: 'assistant',
        content: data.answer || 'No answer was generated.',
        sources: data.sources?.map((source: string) => ({
          text: '',
          document: source
        })) || [],
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error asking question:', error);
      const errorMessage: Message = {
        type: 'assistant',
        content: 'Sorry, there was an error processing your question. Please try again.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
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

  if (documents.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800 p-6">
        <div className="max-w-xl w-full">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white text-center mb-8">
            Document Q&A Assistant
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 text-center mb-12">
            Upload your documents to start asking questions
          </p>
          <FileUpload onUploadSuccess={handleUploadSuccess} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
      {/* Sidebar */}
      <aside className="w-80 h-screen sticky top-0 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-y-auto">
        <div className="p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
            Documents
          </h2>
          <FileUpload onUploadSuccess={handleUploadSuccess} />
          
          {documents.length > 0 && (
            <div className="mt-8">
              <DocumentList
                documents={documents}
                onDelete={handleDeleteDocument}
              />
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen">
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-5xl mx-auto space-y-6">
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-8">
              Document Q&A Assistant
            </h1>
            
            {/* Chat Messages */}
            <div className="space-y-8">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} px-4`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg p-6 ${
                      message.type === 'user'
                        ? 'bg-blue-500 text-white'
                        : 'bg-white dark:bg-gray-800 shadow-sm'
                    }`}
                  >
                    <div className={`prose ${
                      message.type === 'user' 
                        ? 'prose-invert' 
                        : 'dark:prose-invert'
                    } max-w-none`}>
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({children}) => <p className="mt-0 mb-4 last:mb-0">{children}</p>,
                          ul: ({children}) => <ul className="mt-0 mb-4 list-disc list-inside">{children}</ul>,
                          ol: ({children}) => <ol className="mt-0 mb-4 list-decimal list-inside">{children}</ol>,
                          li: ({children}) => <li className="mt-1">{children}</li>,
                          code: ({children}) => (
                            <code className="px-1 py-0.5 rounded-md bg-gray-100 dark:bg-gray-700 text-sm">
                              {children}
                            </code>
                          ),
                          pre: ({children}) => (
                            <pre className="block p-4 rounded-md bg-gray-100 dark:bg-gray-700 text-sm overflow-x-auto mt-0 mb-4">
                              {children}
                            </pre>
                          ),
                          blockquote: ({children}) => (
                            <blockquote className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 my-4 italic">
                              {children}
                            </blockquote>
                          ),
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-4 text-sm border-t border-gray-200 dark:border-gray-700 pt-3">
                        <p className="font-medium mb-2 opacity-90">Sources:</p>
                        <ul className="space-y-1 list-disc list-inside">
                          {message.sources.map((source, idx) => (
                            <li key={idx} className="opacity-75">
                              {source.document}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Fixed Question Input */}
        <div className="bg-transparent p-6">
          <div className="max-w-5xl mx-auto px-4">
            <QuestionInput
              onAskQuestion={handleAskQuestion}
              isLoading={isLoading}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
