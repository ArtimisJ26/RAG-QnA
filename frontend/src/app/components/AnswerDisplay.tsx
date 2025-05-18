'use client';

interface AnswerDisplayProps {
  answer: string;
  sources?: {
    text: string;
    document: string;
  }[];
}

export default function AnswerDisplay({ answer, sources }: AnswerDisplayProps) {
  if (!answer) return null;

  return (
    <div className="w-full space-y-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-lg">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Answer
        </h3>
        <div className="prose dark:prose-invert max-w-none">
          <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
            {answer}
          </p>
        </div>
      </div>

      {sources && sources.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Sources
          </h3>
          <div className="space-y-4">
            {sources.map((source, index) => (
              <div
                key={index}
                className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm"
              >
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                  From: {source.document}
                </p>
                <p className="text-gray-700 dark:text-gray-300 text-sm">
                  {source.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
} 