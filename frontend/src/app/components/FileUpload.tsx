'use client';

import { useState, useRef, useEffect } from 'react';

interface FileUploadProps {
  onUploadSuccess?: (uploadedFiles: { name: string; size: number; uploadedAt: string }[]) => void;
}

interface EmbeddingStatus {
  status: 'pending' | 'processing' | 'complete' | 'error';
  progress: number;
  fileName: string;
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollTimeoutRef = useRef<NodeJS.Timeout>();
  const abortControllerRef = useRef<AbortController>();

  // Cleanup function for unmounting
  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

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

  const handleBoxClick = () => {
    fileInputRef.current?.click();
  };

  const checkEmbeddingStatus = async (fileName: string) => {
    try {
      // Create new AbortController for this request
      abortControllerRef.current?.abort(); // Abort any existing request
      abortControllerRef.current = new AbortController();

      const response = await fetch(
        `/api/embedding-status/${encodeURIComponent(fileName)}`,
        { signal: abortControllerRef.current.signal }
      );
      
      if (!response.ok) {
        throw new Error('Failed to check embedding status');
      }
      
      const data = await response.json();
      console.log('Embedding status response:', { fileName, data });
      return data;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Status check aborted');
        return null;
      }
      console.error('Error checking embedding status:', error);
      return null;
    }
  };

  const monitorEmbeddingProgress = async (fileName: string) => {
    console.log('Starting embedding progress monitoring for:', fileName);
    
    // Clear any existing timeout
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
    }

    setEmbeddingStatus(prev => {
      console.log('Current embedding status:', prev);
      return [...prev, { 
        status: 'pending', 
        progress: 0, 
        fileName 
      }];
    });

    let attempts = 0;
    const maxAttempts = 60; // 5 minutes maximum (with 5-second intervals)

    const checkStatus = async () => {
      const status = await checkEmbeddingStatus(fileName);
      console.log('Status check result:', { fileName, status, attempts });
      
      if (status) {
        setEmbeddingStatus(prev => {
          const newStatus = prev.map(s => 
            s.fileName === fileName 
              ? { 
                  ...s, 
                  status: status.status,
                  progress: status.progress || s.progress 
                }
              : s
          );
          console.log('Updating embedding status:', newStatus);
          return newStatus;
        });

        if (status.status === 'complete' || status.status === 'error') {
          return true;
        }
      }

      attempts++;
      if (attempts >= maxAttempts) {
        setEmbeddingStatus(prev => prev.map(s => 
          s.fileName === fileName 
            ? { ...s, status: 'error' }
            : s
        ));
        return true;
      }

      return false;
    };

    const poll = async () => {
      try {
        const finished = await checkStatus();
        if (!finished) {
          // Store the timeout reference so we can clean it up if needed
          pollTimeoutRef.current = setTimeout(poll, 5000);
        } else {
          console.log('Finished monitoring embedding progress for:', fileName);
          pollTimeoutRef.current = undefined;
        }
      } catch (error) {
        console.error('Error in polling:', error);
        pollTimeoutRef.current = undefined;
      }
    };

    await poll();
  };

  const uploadFiles = async (filesToUpload: File[]) => {
    // Abort any ongoing status checks
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    setUploadStatus('uploading');
    setErrorMessage('');
    setUploadProgress({});
    
    try {
      // Validate file size
      const maxSize = 50 * 1024 * 1024; // 50MB
      for (const file of filesToUpload) {
        if (file.size > maxSize) {
          throw new Error(`File ${file.name} is too large. Maximum size is 50MB.`);
        }
      }

      const uploadPromises = filesToUpload.map(file => {
        return new Promise((resolve, reject) => {
          const xhr = new XMLHttpRequest();
          const formData = new FormData();
          formData.append('file', file);

          // Initialize embedding status before upload starts
          setEmbeddingStatus(prev => [...prev, {
            fileName: file.name,
            status: 'pending',
            progress: 0
          }]);

          xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
              const progress = Math.round((event.loaded * 100) / event.total);
              setUploadProgress(prev => ({
                ...prev,
                [file.name]: progress
              }));
            }
          });

          xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              try {
                const response = JSON.parse(xhr.responseText);
                console.log('Upload success, starting embedding:', file.name);
                // Update embedding status to processing
                setEmbeddingStatus(prev => 
                  prev.map(s => s.fileName === file.name 
                    ? { ...s, status: 'processing', progress: 10 } 
                    : s
                  )
                );
                // Start monitoring embedding progress
                monitorEmbeddingProgress(file.name).catch(console.error);
                resolve(response);
              } catch (error) {
                reject(new Error('Invalid response format'));
              }
            } else {
              try {
                const errorData = JSON.parse(xhr.responseText);
                reject(new Error(errorData.detail || `Upload failed (${xhr.status})`));
              } catch {
                reject(new Error(`Upload failed (${xhr.status})`));
              }
            }
          });

          xhr.addEventListener('error', () => {
            setEmbeddingStatus(prev => 
              prev.map(s => s.fileName === file.name 
                ? { ...s, status: 'error', progress: 0 } 
                : s
              )
            );
            reject(new Error('Network error occurred'));
          });

          xhr.addEventListener('timeout', () => {
            setEmbeddingStatus(prev => 
              prev.map(s => s.fileName === file.name 
                ? { ...s, status: 'error', progress: 0 } 
                : s
              )
            );
            reject(new Error('Upload timed out'));
          });

          xhr.open('POST', '/api/upload');
          xhr.setRequestHeader('Accept', 'application/json');
          xhr.timeout = 120000; // 2 minutes timeout
          xhr.send(formData);
        });
      });

      await Promise.all(uploadPromises);
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
  };

  const getStatusColor = (status: EmbeddingStatus['status']) => {
    switch (status) {
      case 'pending':
        return 'bg-gray-300';
      case 'processing':
        return 'bg-blue-500';
      case 'complete':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-300';
    }
  };

  const getStatusText = (status: EmbeddingStatus['status']) => {
    switch (status) {
      case 'pending':
        return 'Waiting...';
      case 'processing':
        return 'Creating embeddings...';
      case 'complete':
        return 'Complete';
      case 'error':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="w-full">
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-500'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleBoxClick}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          className="hidden"
          accept=".pdf"
          multiple
        />
        <div className="text-gray-600 dark:text-gray-300">
          <p className="mb-2">Drop PDF files here or click to select</p>
          <p className="text-sm opacity-75">Maximum file size: 50MB</p>
        </div>
      </div>

      {/* Progress Section */}
      <div className="mt-4 space-y-4">
        {/* Upload Progress */}
        {Object.entries(uploadProgress).length > 0 && (
          <div className="space-y-3">
            <h3 className="font-medium text-gray-700 dark:text-gray-300">Upload Progress</h3>
            {Object.entries(uploadProgress).map(([fileName, progress]) => (
              <div key={fileName} className="space-y-1">
                <div className="flex justify-between text-sm text-gray-600 dark:text-gray-300">
                  <span>{fileName}</span>
                  <span>{progress}%</span>
                </div>
                <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Embedding Progress */}
        {embeddingStatus.length > 0 && (
          <div className="space-y-3">
            <h3 className="font-medium text-gray-700 dark:text-gray-300">Embedding Progress</h3>
            {embeddingStatus.map((status) => (
              <div key={status.fileName} className="space-y-1">
                <div className="flex justify-between text-sm text-gray-600 dark:text-gray-300">
                  <span className="flex items-center gap-2">
                    {status.fileName}
                    <span className={`
                      px-2 py-0.5 rounded-full text-xs
                      ${status.status === 'processing' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : ''}
                      ${status.status === 'complete' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : ''}
                      ${status.status === 'error' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' : ''}
                      ${status.status === 'pending' ? 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-300' : ''}
                    `}>
                      {getStatusText(status.status)}
                    </span>
                  </span>
                  <span>{status.progress}%</span>
                </div>
                <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${getStatusColor(status.status)}`}
                    style={{ width: `${status.progress}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {errorMessage && (
        <div className="mt-4 p-3 bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg">
          {errorMessage}
        </div>
      )}
    </div>
  );
} 