import { RefreshCw } from 'lucide-react';

interface LoadingSpinnerProps {
  message?: string;
  submessage?: string;
}

export default function LoadingSpinner({ message = 'Loading...', submessage }: LoadingSpinnerProps) {
  return (
    <div className="flex items-center justify-center min-h-[70vh]">
      <div className="text-center">
        <RefreshCw className="w-20 h-20 mx-auto mb-6 animate-spin text-blue-400" />
        <p className="text-3xl font-bold">{message}</p>
        {submessage && <p className="text-gray-400 mt-2">{submessage}</p>}
      </div>
    </div>
  );
}