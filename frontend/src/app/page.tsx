// app/page.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import SearchBar, { type SearchFilters } from "@/components/SearchBar";
import FiltersSidebar from "@/components/FiltersSidebar";
import SearchResultsContainer from "@/components/SearchResultsContainer";
// import { fetchLegislation } from "@/lib/api";
import type { Legislation, Supervisor } from "@/types/legislation";
import LegislationCard from "@/components/LegislationCard";


export default function Page() {
  // Raw dataset and reference lists
  const [allLegislation, setAllLegislation] = useState<Legislation[]>([]);
  const [supervisors, setSupervisors] = useState<Supervisor[]>([]);
  const [categories, setCategories] = useState<string[]>([]);

  // View state
  const [filteredLegislation, setFilteredLegislation] = useState<Legislation[]>([]);
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<SearchFilters>({ supervisor: "", category: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Derive categories from data
  const derivedCategories = useMemo(() => {
    const s = new Set<string>();
    for (const l of allLegislation) if (l?.category) s.add(l.category);
    return Array.from(s).sort();
  }, [allLegislation]);

  // Client-side filter
  function applyFilters(list: Legislation[], q: string, f: SearchFilters): Legislation[] {
    const qNorm = q.trim().toLowerCase();
    return list.filter((item) => {
      const matchesQuery =
        !qNorm ||
        item.title?.toLowerCase().includes(qNorm) ||
        item.legislation_number?.toLowerCase().includes(qNorm) ||
        item.description?.toLowerCase().includes(qNorm);

      const matchesSupervisor =
        !f.supervisor ||
        (item.votes && Object.prototype.hasOwnProperty.call(item.votes, f.supervisor)) ||
        (Array.isArray(item.sponsors) && item.sponsors.some((s) => s.name === f.supervisor));

      const matchesCategory = !f.category || item.category === f.category;

      return matchesQuery && matchesSupervisor && matchesCategory;
    });
  }

  // Initial load (backend or mock)
  useEffect(() => {
    (async () => {
      try {
        setIsLoading(true);
        setError(null);
          // const data = await fetchLegislation();
          const data = {
              legislation: [],
              supervisors: []
          };
        const legislation = data?.legislation ?? [];
        const sups = data?.supervisors ?? [];

        setAllLegislation(legislation);
        setSupervisors(sups);
        setFilteredLegislation(applyFilters(legislation, "", { supervisor: "", category: "" }));
        setHasSearched(true);
      } catch (e) {
        console.error(e);
        setError("Failed to load legislation data.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  // Keep categories synced
  useEffect(() => {
    setCategories(derivedCategories);
  }, [derivedCategories]);

  // Sidebar filter changes
  function handleFilterChange(next: SearchFilters) {
    setFilters(next);
    setFilteredLegislation(applyFilters(allLegislation, query, next));
  }

  // Search submit (may hit backend; still filtered client-side)
  async function handleSearch(nextQuery: string, nextFilters: SearchFilters) {
    try {
      setIsLoading(true);
      setError(null);
      setQuery(nextQuery);
      setFilters(nextFilters);

          const data = {
              legislation: [],
              supervisors: []
          };
        //const data = await fetchLegislation(nextQuery);
      const legislation = data?.legislation ?? [];
      const sups = data?.supervisors ?? [];

      setAllLegislation(legislation);
      setSupervisors(sups);
      setFilteredLegislation(applyFilters(legislation, nextQuery, nextFilters));
      setHasSearched(true);
    } catch (e) {
      console.error(e);
      setError("Failed to search legislation.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Top search bar */}
      <div className="border-b bg-white">
        <div className="container mx-auto px-4 py-6">
          <SearchBar
            onSearch={handleSearch}
            isLoading={isLoading}
            supervisors={supervisors}
            categories={categories}
          />
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="container mx-auto px-4 mt-6">
          <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
            {error}
          </div>
        </div>
      )}

      {/* Content area */}
      <div className="container mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* Sidebar */}
          <FiltersSidebar
            supervisors={supervisors}
            categories={categories}
            filters={filters}
            onFilterChange={handleFilterChange}
          />

          {/* One container, many cards inside */}
          <div className="flex-1">
            <SearchResultsContainer 
            isLoading={isLoading} 
            error={error}
            count={filteredLegislation.length}   // ✅ add this

            >
              {hasSearched && filteredLegislation.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-600 text-lg">No legislation found matching your search.</p>
                  <p className="text-gray-500 mt-2">Try a different search term or adjust filters.</p>
                </div>
              ) : (
                <>
                  <div className="mb-6">
                    <h2 className="text-2xl font-bold text-gray-900">
                      {filteredLegislation.length}{" "}
                      {filteredLegislation.length === 1 ? "Result" : "Results"}
                    </h2>
                  </div>
                  <div className="space-y-6">
                    {filteredLegislation.map((leg) => (
                      <LegislationCard
                        key={leg.id}
                        legislation={leg}
                        supervisors={supervisors}
                      />
                    ))}
                  </div>
                </>
              )}
            </SearchResultsContainer>
          </div>
        </div>
      </div>
    </main>
  );
}
