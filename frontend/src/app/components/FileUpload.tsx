'use client';

import { useState } from 'react';

interface FileUploadProps {
  onUploadSuccess?: (uploadedFiles: { name: string; size: number; uploadedAt: string }[]) => void;
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    await uploadFiles(droppedFiles);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      await uploadFiles(selectedFiles);
    }
  };

  const uploadFiles = async (filesToUpload: File[]) => {
    setUploadStatus('uploading');
    setErrorMessage('');
    
    try {
      // Validate file size
      const maxSize = 50 * 1024 * 1024; // 50MB
      for (const file of filesToUpload) {
        if (file.size > maxSize) {
          throw new Error(`File ${file.name} is too large. Maximum size is 50MB.`);
        }
      }

      const formData = new FormData();
      filesToUpload.forEach((file) => {
        formData.append('file', file);
      });

      // Create AbortController with a longer timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort('Upload took too long');
      }, 120000); // 2 minutes timeout

      try {
        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
          signal: controller.signal,
          // Add proper headers for large file upload
          headers: {
            'Accept': 'application/json',
          },
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Upload failed (${response.status})`);
        }

        const data = await response.json();
        setUploadStatus('success');
        
        if (onUploadSuccess) {
          const uploadedFiles = filesToUpload.map(file => ({
            name: file.name,
            size: file.size,
            uploadedAt: new Date().toISOString()
          }));
          onUploadSuccess(uploadedFiles);
        }
      } catch (error) {
        console.error('Upload error:', error);
        setUploadStatus('error');
        setErrorMessage(error instanceof Error ? error.message : 'Upload failed. Please try again.');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus('error');
      setErrorMessage(error instanceof Error ? error.message : 'Upload failed. Please try again.');
    }
  };

  return (
    <div className="w-full">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-600'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center justify-center space-y-4">
          <svg
            className="w-12 h-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <div className="text-lg text-gray-600 dark:text-gray-300">
            Drag and drop your files here, or{' '}
            <label className="text-blue-500 hover:text-blue-600 cursor-pointer">
              browse
              <input
                type="file"
                className="hidden"
                multiple
                onChange={handleFileSelect}
                accept=".pdf,.txt,.doc,.docx"
              />
            </label>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Supported formats: PDF, TXT, DOC, DOCX (Max size: 50MB)
          </p>
        </div>
      </div>

      {uploadStatus === 'uploading' && (
        <div className="mt-4 text-center text-blue-500">
          <div className="animate-pulse">Uploading files...</div>
        </div>
      )}
      {uploadStatus === 'success' && (
        <div className="mt-4 text-center text-green-500">Upload successful!</div>
      )}
      {uploadStatus === 'error' && (
        <div className="mt-4 text-center text-red-500">
          {errorMessage || 'Upload failed. Please try again.'}
        </div>
      )}
    </div>
  );
} 