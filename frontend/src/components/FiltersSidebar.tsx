// components/FiltersSidebar.tsx
"use client";

import { useMemo } from "react";
import { SearchFilters } from "@/components/SearchBar";
import { Supervisor } from "@/types/legislation";

type Props = {
  supervisors: Supervisor[];
  categories: string[];
  filters: SearchFilters;
  onFilterChange: (filters: SearchFilters) => void;
};

export default function FiltersSidebar({
  supervisors,
  categories,
  filters,
  onFilterChange,
}: Props) {
  const sortedSupervisors = useMemo(
    () => [...supervisors].sort((a, b) => a.district - b.district),
    [supervisors]
  );

  return (
    <aside className="hidden md:block w-72 shrink-0 border-r bg-white">
      <div className="p-4 border-b">
        <h2 className="text-sm font-semibold text-gray-700">Filters</h2>
      </div>

      <div className="p-4 space-y-6">
        {/* Supervisor */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-2">
            Supervisor
          </label>
          <select
            value={filters.supervisor}
            onChange={(e) =>
              onFilterChange({ ...filters, supervisor: e.target.value })
            }
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Supervisors</option>
            {sortedSupervisors.map((s) => (
              <option key={s.name} value={s.name}>
                {s.name} (D{s.district})
              </option>
            ))}
          </select>
        </div>

        {/* Category */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-2">
            Category
          </label>
          <select
            value={filters.category}
            onChange={(e) =>
              onFilterChange({ ...filters, category: e.target.value })
            }
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>
    </aside>
  );
}
