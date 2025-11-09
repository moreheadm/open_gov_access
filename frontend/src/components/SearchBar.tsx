// components/SearchBar.tsx
"use client";

import { useState, useMemo } from "react";
import { Search, ChevronDown } from "lucide-react";
import { Supervisor } from "@/types/legislation";

interface SearchBarProps {
  onSearch: (query: string, filters: SearchFilters) => void;
  isLoading?: boolean;
  supervisors?: Supervisor[]; // ← make optional
  categories?: string[]; // ← make optional
}

export interface SearchFilters {
  supervisor: string;
  category: string;
}

export default function SearchBar({
  onSearch,
  isLoading = false,
  supervisors = [], // ← safe defaults
  categories = [], // ← safe defaults
}: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<SearchFilters>({
    supervisor: "",
    category: "",
  });

  // Extra safety: normalize to arrays once.
  const safeSupervisors = useMemo(
    () => (Array.isArray(supervisors) ? supervisors : []),
    [supervisors]
  );
  const safeCategories = useMemo(
    () => (Array.isArray(categories) ? categories : []),
    [categories]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(query, filters);
  };

  const handleFilterChange = (
    filterType: keyof SearchFilters,
    value: string
  ) => {
    const newFilters = { ...filters, [filterType]: value };
    setFilters(newFilters);
    //onSearch(query, newFilters);
  };

  return (
    <div className="w-full bg-white border-b shadow-sm sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <h1 className="text-2xl font-semibold text-gray-900 mb-4">
          San Francisco Legislation
        </h1>

        <form onSubmit={handleSubmit}>
          <div className="flex gap-3 items-center">
            {/* Search Input */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search legislation by title, number, or keyword..."
                className="w-full pl-10 pr-4 py-3 text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none"
                disabled={isLoading}
              />
            </div>

            {/* Supervisor Filter */}
            <div className="relative">
              <select
                value={filters.supervisor}
                onChange={(e) =>
                  handleFilterChange("supervisor", e.target.value)
                }
                className="appearance-none pl-4 pr-10 py-3 border border-gray-300 rounded-lg bg-white text-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none cursor-pointer min-w-[200px]"
                disabled={isLoading}
              >
                <option value="">All Supervisors</option>
                {safeSupervisors.map((supervisor) => (
                  <option key={supervisor.name} value={supervisor.name}>
                    {supervisor.name} (D{supervisor.district})
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5 pointer-events-none" />
            </div>

            {/* Category Filter */}
            <div className="relative">
              <select
                value={filters.category}
                onChange={(e) => handleFilterChange("category", e.target.value)}
                className="appearance-none pl-4 pr-10 py-3 border border-gray-300 rounded-lg bg-white text-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none cursor-pointer min-w-[180px]"
                disabled={isLoading}
              >
                <option value="">All Categories</option>
                {safeCategories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5 pointer-events-none" />
            </div>

            {/* Search Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed font-medium whitespace-nowrap"
            >
              {isLoading ? "Searching..." : "Search"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
