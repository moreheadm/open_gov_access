// components/SearchResultsContainer.tsx
"use client";

import { ReactNode } from "react";

type Props = {
  isLoading: boolean;
  error: string | null;
  count?: number;        // <— pass how many results to show in the header
  children: ReactNode;   // <— cards (and empty state) are rendered by the page
};

export default function SearchResultsContainer({
  isLoading,
  error,
  count = 0,
  children,
}: Props) {
  if (error) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800">
          {error}
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto py-12 text-center">
        <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600" />
        <p className="mt-4 text-gray-600">Loading legislation…</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      {children}
    </div>
  );
}
